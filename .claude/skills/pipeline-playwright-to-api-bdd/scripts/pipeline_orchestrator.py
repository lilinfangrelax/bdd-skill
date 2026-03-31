"""
pipeline_orchestrator.py
总控向导：将 Playwright 录制 → trace 解析 → BDD 确认 → API 步骤 → bdd_project 接入
的多步流程收敛为单入口分步执行，支持中断/续跑。

用法:
  python pipeline_orchestrator.py start --recording-script <path> [选项]
  python pipeline_orchestrator.py continue --run-dir <path>
  python pipeline_orchestrator.py resume-from <stage> --run-dir <path>
  python pipeline_orchestrator.py status --run-dir <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ── 阶段定义（有序） ────────────────────────────────────────────

STAGES = [
    "validate_recording_script",
    "record_or_use_trace",
    "trace_to_bdd_confirm",
    "human_confirm_required",
    "confirmed_md_to_api_steps",
    "api_steps_to_bdd_project",
    "done",
]

# ── 路径常量 ──────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent
# .claude/skills/pipeline-playwright-to-api-bdd → skills → .claude → 项目根
_PROJECT_ROOT = _SKILL_DIR.parent.parent.parent

# 依赖脚本（相对项目根）
PARSE_TRACE_SCRIPT = "demo/trace_click_api/parse_trace.py"
TRACE_TO_BDD_SCRIPT = ".claude/skills/trace-to-bdd/scripts/trace_to_bdd.py"
MD_TO_API_STEPS_SCRIPT = ".claude/skills/md-to-api-steps/scripts/md_to_api_steps.py"
API_STEPS_TO_BDD_SCRIPT = ".claude/skills/api-steps-to-bdd-project/scripts/api_steps_to_bdd_project.py"

# 录制脚本最大执行时间
RECORDING_TIMEOUT_SEC = 300


# ── 状态管理 ──────────────────────────────────────────────────


class PipelineState:
    """pipeline_state.json 的读写封装。"""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.state_file = run_dir / "pipeline_state.json"
        self.data: dict[str, Any] = {}

    def init(self, params: dict[str, Any]) -> None:
        self.data = {
            "version": 1,
            "run_id": self.run_dir.name,
            "run_dir": str(self.run_dir),
            "current_stage": STAGES[0],
            "completed_stages": [],
            "params": params,
            "artifacts": {},
            "error": None,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self.save()

    def load(self) -> None:
        self.data = json.loads(self.state_file.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.data["updated_at"] = datetime.now().isoformat()
        self.state_file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @property
    def current_stage(self) -> str:
        return self.data["current_stage"]

    @current_stage.setter
    def current_stage(self, stage: str) -> None:
        self.data["current_stage"] = stage
        self.save()

    def mark_completed(self, stage: str) -> None:
        if stage not in self.data["completed_stages"]:
            self.data["completed_stages"].append(stage)
        idx = STAGES.index(stage)
        if idx + 1 < len(STAGES):
            self.data["current_stage"] = STAGES[idx + 1]
        self.data["error"] = None
        self.save()

    def mark_error(self, stage: str, error: str, suggestion: str = "") -> None:
        self.data["current_stage"] = stage
        self.data["error"] = {
            "stage": stage,
            "message": error,
            "suggestion": suggestion,
        }
        self.save()

    def set_artifact(self, key: str, value: str) -> None:
        self.data["artifacts"][key] = value
        self.save()

    def get_artifact(self, key: str) -> Optional[str]:
        return self.data.get("artifacts", {}).get(key)

    def get_param(self, key: str) -> Any:
        return self.data.get("params", {}).get(key)

    def reset_to_stage(self, stage: str) -> None:
        """回退到指定阶段，清除之后的完成记录。"""
        idx = STAGES.index(stage)
        self.data["current_stage"] = stage
        self.data["completed_stages"] = [
            s for s in self.data["completed_stages"] if STAGES.index(s) < idx
        ]
        self.data["error"] = None
        self.save()


# ── 工具函数 ──────────────────────────────────────────────────


def _python_exe() -> str:
    return sys.executable


def _render_cli_command(script_path: Path, args: list[str]) -> str:
    """渲染可直接复制的命令，避免相对路径导致命令不可用。"""
    parts = [f'"{_python_exe()}"', f'"{script_path}"']
    parts.extend(f'"{a}"' if " " in a else a for a in args)
    return " ".join(parts)


def _run_script(
    script_rel: str,
    args: list[str],
    project_root: Path,
    *,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """在项目根目录下执行 Python 脚本。"""
    script_path = project_root / script_rel
    if not script_path.exists():
        raise FileNotFoundError(f"脚本不存在: {script_path}")
    cmd = [_python_exe(), str(script_path)] + args
    print(f"  执行: {' '.join(cmd[:6])}{'...' if len(cmd) > 6 else ''}")
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.stdout:
        for line in result.stdout.strip().splitlines()[:20]:
            print(f"    {line}")
    if result.stderr:
        for line in result.stderr.strip().splitlines()[:10]:
            print(f"    [stderr] {line}")
    return result


def _quick_validate_trace(trace_zip: Path) -> tuple[bool, str]:
    """快速验证 trace.zip 是否包含有效请求响应。"""
    try:
        with zipfile.ZipFile(trace_zip) as zf:
            names = zf.namelist()
            has_trace = any(n.endswith("trace.trace") for n in names)
            has_network = any(n.endswith("trace.network") for n in names)
            if not has_trace:
                return False, "trace.zip 中缺少 trace.trace"
            if not has_network:
                return False, "trace.zip 中缺少 trace.network"

            network_entry = next(n for n in names if n.endswith("trace.network"))
            network_bytes = zf.read(network_entry)
            valid_count = 0
            for line in network_bytes.decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    snap = obj.get("snapshot", {})
                    resp = snap.get("response", {})
                    status = resp.get("status")
                    if isinstance(status, int) and status > 0:
                        valid_count += 1
                except json.JSONDecodeError:
                    continue

            if valid_count == 0:
                return False, "trace 中未找到有效请求响应（全部 pending 或无请求）"
            return True, f"trace 包含 {valid_count} 个有效请求响应"
    except zipfile.BadZipFile:
        return False, "文件不是有效的 zip 格式"
    except Exception as e:
        return False, f"验证 trace.zip 时出错: {e}"


def _count_checked_items(md_path: Path) -> int:
    """统计 Markdown 中 [x] 勾选项数量。"""
    if not md_path.exists():
        return 0
    text = md_path.read_text(encoding="utf-8")
    return len(re.findall(r"^\s*-\s*\[x\]", text, re.MULTILINE))


def _sha256_file(path: Path) -> str:
    """计算文件内容哈希，用于判断人工确认文件是否被修改。"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_run_dir(state: PipelineState, project_root: Path) -> Path:
    run_dir = Path(state.data["run_dir"])
    if not run_dir.is_absolute():
        run_dir = project_root / run_dir
    return run_dir


def _find_trace_zip(script_path: Path, project_root: Path) -> Optional[Path]:
    """在录制脚本附近搜索最近修改的 trace*.zip。"""
    search_dirs = [
        script_path.parent.parent / "traces",  # 录制脚本/../traces/
        script_path.parent,
        project_root,
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        candidates = sorted(
            d.glob("*trace*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
    return None


# ── 各阶段实现 ──────────────────────────────────────────────────


def stage_validate_recording_script(state: PipelineState, project_root: Path) -> bool:
    """执行录制脚本并验证 trace.zip 可用（硬闸门）。"""
    if state.get_param("trace_zip_input"):
        print("  跳过：用户已提供 trace.zip，无需验证录制脚本")
        state.mark_completed("validate_recording_script")
        return True

    recording_script = state.get_param("recording_script")
    script_path = project_root / recording_script
    if not script_path.exists():
        state.mark_error(
            "validate_recording_script",
            f"录制脚本不存在: {script_path}",
            "请检查 --recording-script 参数路径是否正确",
        )
        return False

    print(f"  录制脚本: {script_path}")
    print("  正在执行录制（请确保目标应用已启动）...")

    try:
        result = subprocess.run(
            [_python_exe(), str(script_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=RECORDING_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        state.mark_error(
            "validate_recording_script",
            f"录制脚本执行超时（{RECORDING_TIMEOUT_SEC}s）",
            "请检查脚本是否卡在等待状态，或增加超时时间",
        )
        return False

    if result.returncode != 0:
        stderr_brief = result.stderr[:500] if result.stderr else "(无)"
        suggestion = "请检查目标应用是否已启动、脚本路径是否正确"
        if "ERR_CONNECTION_REFUSED" in stderr_brief or "ECONNREFUSED" in stderr_brief:
            suggestion = (
                "检测到连接被拒绝，请先启动目标服务（例如："
                ".\\.venv\\Scripts\\python demo/trace_click_api/server.py）"
            )
        state.mark_error(
            "validate_recording_script",
            f"录制脚本退出码 {result.returncode}\nstderr: {stderr_brief}",
            suggestion,
        )
        return False

    # 查找 trace.zip
    trace_output = state.get_param("trace_output")
    if trace_output:
        trace_path = Path(trace_output)
        if not trace_path.is_absolute():
            trace_path = project_root / trace_path
    else:
        trace_path = _find_trace_zip(script_path, project_root)

    if not trace_path or not trace_path.exists():
        state.mark_error(
            "validate_recording_script",
            "录制脚本执行成功但未找到 trace.zip",
            "请检查脚本中 tracing.stop(path=...) 的输出路径，或使用 --trace-output 指定",
        )
        return False

    valid, msg = _quick_validate_trace(trace_path)
    if not valid:
        state.mark_error(
            "validate_recording_script",
            msg,
            "参考 playwright-trace-recorder skill 改进 tracing 收尾等待策略",
        )
        return False

    print(f"  ✅ 验证通过：{msg}")
    state.set_artifact("trace_zip_source", str(trace_path))
    state.mark_completed("validate_recording_script")
    return True


def stage_record_or_use_trace(state: PipelineState, project_root: Path) -> bool:
    """将有效 trace.zip 复制到 run 目录统一管理。"""
    run_dir = _resolve_run_dir(state, project_root)
    dest = run_dir / "trace.zip"

    trace_zip_input = state.get_param("trace_zip_input")
    if trace_zip_input:
        src = Path(trace_zip_input)
        if not src.is_absolute():
            src = project_root / src
        if not src.exists():
            state.mark_error(
                "record_or_use_trace",
                f"指定的 trace.zip 不存在: {src}",
                "请检查 --trace-zip 参数路径",
            )
            return False
        valid, msg = _quick_validate_trace(src)
        if not valid:
            state.mark_error("record_or_use_trace", msg, "请提供有效的 trace.zip")
            return False
        shutil.copy2(str(src), str(dest))
        print(f"  ✅ 已复制用户提供的 trace.zip → {dest}")
    else:
        src_str = state.get_artifact("trace_zip_source")
        if not src_str:
            state.mark_error(
                "record_or_use_trace",
                "未找到 trace.zip（验证阶段可能未完成）",
                "请先完成 validate_recording_script 阶段",
            )
            return False
        src = Path(src_str)
        if not src.exists():
            state.mark_error(
                "record_or_use_trace",
                f"trace.zip 源文件已不存在: {src}",
                "请重新执行 validate_recording_script 阶段",
            )
            return False
        shutil.copy2(str(src), str(dest))
        print(f"  ✅ 已复制 trace.zip → {dest}")

    state.set_artifact("trace_zip", str(dest))
    state.mark_completed("record_or_use_trace")
    return True


def stage_trace_to_bdd_confirm(state: PipelineState, project_root: Path) -> bool:
    """解析 trace.zip → JSON → 与录制脚本合并生成 bdd_confirmed.md。"""
    run_dir = _resolve_run_dir(state, project_root)
    trace_zip = run_dir / "trace.zip"
    trace_json = run_dir / "trace_parsed.json"
    bdd_md = run_dir / "bdd_confirmed.md"

    # 子步骤 1: parse_trace.py → trace_parsed.json
    print("  [1/2] 解析 trace.zip → trace_parsed.json")
    try:
        result = _run_script(
            PARSE_TRACE_SCRIPT,
            ["--zip", str(trace_zip), "--json-out", str(trace_json)],
            project_root,
        )
    except FileNotFoundError as e:
        state.mark_error("trace_to_bdd_confirm", str(e), "")
        return False

    if result.returncode != 0:
        state.mark_error(
            "trace_to_bdd_confirm",
            f"parse_trace.py 失败（退出码 {result.returncode}）\n{result.stderr[:500]}",
            "请检查 trace.zip 是否完整",
        )
        return False
    if not trace_json.exists():
        state.mark_error("trace_to_bdd_confirm", "parse_trace.py 未生成 trace_parsed.json", "")
        return False
    state.set_artifact("trace_parsed_json", str(trace_json))

    # 子步骤 2: trace_to_bdd.py → bdd_confirmed.md
    recording_script = state.get_param("recording_script")
    if not recording_script:
        state.mark_error(
            "trace_to_bdd_confirm",
            "缺少录制脚本路径",
            "请在 start 时提供 --recording-script",
        )
        return False
    recording_path = project_root / recording_script

    print("  [2/2] 录制脚本 + trace JSON → bdd_confirmed.md")
    try:
        result = _run_script(
            TRACE_TO_BDD_SCRIPT,
            [str(recording_path), str(trace_json), str(bdd_md)],
            project_root,
        )
    except FileNotFoundError as e:
        state.mark_error("trace_to_bdd_confirm", str(e), "")
        return False

    if result.returncode != 0:
        state.mark_error(
            "trace_to_bdd_confirm",
            f"trace_to_bdd.py 失败（退出码 {result.returncode}）\n{result.stderr[:500]}",
            "请检查录制脚本的 # 注释格式是否符合规范",
        )
        return False
    if not bdd_md.exists():
        state.mark_error("trace_to_bdd_confirm", "trace_to_bdd.py 未生成 bdd_confirmed.md", "")
        return False

    checked = _count_checked_items(bdd_md)
    print(f"  ✅ 已生成 bdd_confirmed.md（{checked} 个接口默认勾选）")
    state.set_artifact("bdd_confirmed_md", str(bdd_md))
    state.set_artifact("bdd_confirmed_md_initial_sha256", _sha256_file(bdd_md))
    state.mark_completed("trace_to_bdd_confirm")
    return True


def stage_human_confirm_required(state: PipelineState, project_root: Path) -> bool:
    """校验人工勾选结果：至少有一个 [x] 才放行。"""
    bdd_md_str = state.get_artifact("bdd_confirmed_md")
    if not bdd_md_str:
        state.mark_error(
            "human_confirm_required",
            "bdd_confirmed.md 路径缺失",
            "请先完成 trace_to_bdd_confirm 阶段",
        )
        return False

    md_path = Path(bdd_md_str)
    if not md_path.exists():
        state.mark_error(
            "human_confirm_required",
            f"bdd_confirmed.md 不存在: {md_path}",
            "文件可能被删除，请从 trace_to_bdd_confirm 阶段重新开始",
        )
        return False

    initial_hash = state.get_artifact("bdd_confirmed_md_initial_sha256")
    if initial_hash:
        current_hash = _sha256_file(md_path)
        if current_hash == initial_hash:
            state.mark_error(
                "human_confirm_required",
                "检测到 bdd_confirmed.md 尚未人工修改",
                f"请先手工编辑并保存 {md_path}（例如取消不需要的勾选），再执行 continue",
            )
            return False

    checked = _count_checked_items(md_path)
    if checked == 0:
        state.mark_error(
            "human_confirm_required",
            "bdd_confirmed.md 中没有 [x] 勾选的接口",
            f"请编辑 {md_path}，至少勾选一个接口后重新 continue",
        )
        return False

    print(f"  ✅ 检测到 {checked} 个勾选接口，校验通过")
    state.mark_completed("human_confirm_required")
    return True


def stage_confirmed_md_to_api_steps(state: PipelineState, project_root: Path) -> bool:
    """勾选后的 bdd_confirmed.md + trace.zip → api_steps.md。"""
    run_dir = _resolve_run_dir(state, project_root)
    bdd_md = run_dir / "bdd_confirmed.md"
    trace_zip = run_dir / "trace.zip"
    api_steps = run_dir / "api_steps.md"

    try:
        result = _run_script(
            MD_TO_API_STEPS_SCRIPT,
            [str(bdd_md), str(trace_zip), str(api_steps)],
            project_root,
        )
    except FileNotFoundError as e:
        state.mark_error("confirmed_md_to_api_steps", str(e), "")
        return False

    if result.returncode != 0:
        state.mark_error(
            "confirmed_md_to_api_steps",
            f"md_to_api_steps.py 失败（退出码 {result.returncode}）\n{result.stderr[:500]}",
            "请检查 bdd_confirmed.md 格式与 trace.zip 完整性",
        )
        return False
    if not api_steps.exists():
        state.mark_error("confirmed_md_to_api_steps", "未生成 api_steps.md", "")
        return False

    print(f"  ✅ 已生成 {api_steps}")
    state.set_artifact("api_steps_md", str(api_steps))
    state.mark_completed("confirmed_md_to_api_steps")
    return True


def stage_api_steps_to_bdd_project(state: PipelineState, project_root: Path) -> bool:
    """api_steps.md → bdd_project fixture / feature / generated steps。"""
    run_dir = _resolve_run_dir(state, project_root)
    api_steps = run_dir / "api_steps.md"
    bdd_root = state.get_param("bdd_project_root") or "bdd_project"
    bdd_root_path = project_root / bdd_root
    scenario_name = state.get_param("scenario_name") or "用户完整操作任务（API）"

    script_args = [
        str(api_steps),
        str(bdd_root_path),
        "--scenario-name",
        scenario_name,
    ]

    try:
        result = _run_script(API_STEPS_TO_BDD_SCRIPT, script_args, project_root)
    except FileNotFoundError as e:
        state.mark_error("api_steps_to_bdd_project", str(e), "")
        return False

    if result.returncode != 0:
        state.mark_error(
            "api_steps_to_bdd_project",
            f"api_steps_to_bdd_project.py 失败（退出码 {result.returncode}）\n{result.stderr[:500]}",
            "请检查 api_steps.md 格式与 bdd_project 目录结构",
        )
        return False

    output_lines = []
    for line in (result.stdout or "").splitlines():
        if any(kw in line for kw in ("fixture", "feature", "steps", "已写入", "已更新")):
            output_lines.append(line.strip())

    state.set_artifact("bdd_project_output", "\n".join(output_lines))
    print("  ✅ bdd_project 产物已写入")
    for line in output_lines:
        print(f"    {line}")

    state.mark_completed("api_steps_to_bdd_project")
    return True


def stage_done(state: PipelineState, project_root: Path) -> bool:
    """输出最终产物路径与后续接入提示。"""
    run_dir = state.data["run_dir"]
    print("\n" + "=" * 60)
    print("  🎉 流水线执行完成！")
    print("=" * 60)
    print(f"\n  产物目录: {run_dir}")
    artifacts = state.data.get("artifacts", {})
    if artifacts:
        print("\n  中间产物:")
        for key, val in artifacts.items():
            if val and key != "bdd_project_output":
                print(f"    {key}: {val}")
    bdd_output = artifacts.get("bdd_project_output", "")
    if bdd_output:
        print("\n  bdd_project 输出:")
        for line in bdd_output.splitlines():
            print(f"    {line}")
    print("\n  后续步骤:")
    print("    1. 在 bdd_project/tests/test_api.py 中引入 generated_api_steps 模块")
    print("    2. 为新 Scenario 增加 @scenario(...) 装饰器")
    print("    3. 执行 pytest 验证测试是否通过")
    print()

    state.mark_completed("done")
    return True


# ── 阶段调度表 ─────────────────────────────────────────────────

STAGE_HANDLERS = {
    "validate_recording_script": stage_validate_recording_script,
    "record_or_use_trace": stage_record_or_use_trace,
    "trace_to_bdd_confirm": stage_trace_to_bdd_confirm,
    "human_confirm_required": stage_human_confirm_required,
    "confirmed_md_to_api_steps": stage_confirmed_md_to_api_steps,
    "api_steps_to_bdd_project": stage_api_steps_to_bdd_project,
    "done": stage_done,
}


# ── 流水线执行引擎 ─────────────────────────────────────────────


def run_pipeline(
    state: PipelineState,
    project_root: Path,
    *,
    stop_before_human: bool = True,
) -> bool:
    """
    从当前阶段开始顺序执行。
    stop_before_human=True 时，到达 human_confirm_required 阶段前暂停（首次 start 用）。
    """
    current = state.current_stage
    if current not in STAGES:
        print(f"  ❌ 未知阶段: {current}")
        return False
    start_idx = STAGES.index(current)

    for i in range(start_idx, len(STAGES)):
        stage = STAGES[i]

        # 在 start 模式下到达人工确认阶段前暂停
        if stop_before_human and stage == "human_confirm_required":
            bdd_md = state.get_artifact("bdd_confirmed_md")
            continue_cmd = _render_cli_command(
                _SCRIPT_DIR / "pipeline_orchestrator.py",
                ["continue", "--run-dir", str(state.run_dir)],
            )
            print("\n" + "=" * 60)
            print("  ⏸️  流水线暂停：请人工审阅并勾选接口")
            print("=" * 60)
            print(f"\n  请编辑以下文件，勾选需要纳入自动化的接口（取消不需要的）：")
            print(f"  📄 {bdd_md}")
            print("  ⚠️  注意：必须保存一次人工修改（文件内容变化）后才能继续")
            print(f"\n  完成编辑后，执行以下命令继续：")
            print(f"  {continue_cmd}")
            print()
            return True

        print(f"\n{'─' * 60}")
        print(f"  阶段 [{i + 1}/{len(STAGES)}]: {stage}")
        print(f"{'─' * 60}")

        handler = STAGE_HANDLERS[stage]
        success = handler(state, project_root)

        if not success:
            err = state.data.get("error") or {}
            retry_cmd = _render_cli_command(
                _SCRIPT_DIR / "pipeline_orchestrator.py",
                ["resume-from", stage, "--run-dir", str(state.run_dir)],
            )
            print(f"\n  ❌ 阶段 {stage} 失败")
            print(f"  原因: {err.get('message', '未知')}")
            if err.get("suggestion"):
                print(f"  建议: {err['suggestion']}")
            print(f"\n  修复后可使用以下命令重试：")
            print(f"  {retry_cmd}")
            return False

    return True


# ── CLI 子命令 ──────────────────────────────────────────────────


def cmd_start(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_root = project_root / args.runs_root
    run_dir = runs_root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    state = PipelineState(run_dir)
    params = {
        "recording_script": args.recording_script,
        "trace_zip_input": args.trace_zip,
        "trace_output": args.trace_output,
        "bdd_project_root": args.bdd_project,
        "scenario_name": args.scenario_name,
    }
    state.init(params)

    print(f"🚀 流水线启动")
    print(f"  运行目录: {run_dir}")
    print(f"  状态文件: {state.state_file}")

    success = run_pipeline(state, project_root, stop_before_human=True)
    return 0 if success else 1


def cmd_continue(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = project_root / run_dir

    state = PipelineState(run_dir)
    state.load()

    current = state.current_stage
    print(f"▶️  继续流水线（当前阶段: {current}）")

    success = run_pipeline(state, project_root, stop_before_human=False)
    return 0 if success else 1


def cmd_resume_from(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = project_root / run_dir

    stage = args.stage
    if stage not in STAGES:
        print(f"❌ 未知阶段: {stage}")
        print(f"  可用阶段: {', '.join(STAGES)}")
        return 1

    state = PipelineState(run_dir)
    state.load()
    state.reset_to_stage(stage)

    print(f"🔄 从阶段 {stage} 重新开始")

    # 从 human_confirm_required 或之后恢复时不暂停
    stop = STAGES.index(stage) < STAGES.index("human_confirm_required")
    success = run_pipeline(state, project_root, stop_before_human=stop)
    return 0 if success else 1


def cmd_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = project_root / run_dir

    state = PipelineState(run_dir)
    state.load()
    d = state.data

    print("📋 流水线状态")
    print(f"  运行 ID:   {d['run_id']}")
    print(f"  当前阶段:  {d['current_stage']}")
    print(f"  已完成:    {', '.join(d['completed_stages']) or '（无）'}")
    print(f"  启动时间:  {d['started_at']}")
    print(f"  更新时间:  {d['updated_at']}")

    if d.get("error"):
        err = d["error"]
        print(f"\n  ❌ 错误（阶段 {err['stage']}）:")
        print(f"    {err['message']}")
        if err.get("suggestion"):
            print(f"    建议: {err['suggestion']}")

    artifacts = d.get("artifacts", {})
    if artifacts:
        print("\n  产物:")
        for k, v in artifacts.items():
            if v:
                print(f"    {k}: {v}")

    return 0


# ── 入口 ──────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BDD 流水线总控向导",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"可用阶段: {', '.join(STAGES)}",
    )
    parser.add_argument(
        "--project-root",
        default=str(_PROJECT_ROOT),
        help="项目根目录（默认自动检测）",
    )

    sub = parser.add_subparsers(dest="command")

    # start
    sp_start = sub.add_parser("start", help="启动新流水线")
    sp_start.add_argument(
        "--recording-script",
        default="demo/trace_click_api/recordings/task.py",
        help="录制脚本路径（相对项目根）",
    )
    sp_start.add_argument(
        "--trace-zip",
        default=None,
        help="直接使用已有 trace.zip（跳过录制验证）",
    )
    sp_start.add_argument(
        "--trace-output",
        default=None,
        help="录制脚本产出 trace.zip 的路径（自动检测时可省略）",
    )
    sp_start.add_argument(
        "--bdd-project",
        default="bdd_project",
        help="bdd_project 根目录（相对项目根）",
    )
    sp_start.add_argument(
        "--scenario-name",
        default="用户完整操作任务（API）",
        help="Scenario 名称",
    )
    sp_start.add_argument(
        "--runs-root",
        default="runs",
        help="runs 根目录（相对项目根）",
    )

    # continue
    sp_cont = sub.add_parser("continue", help="继续已暂停的流水线（人工勾选后）")
    sp_cont.add_argument("--run-dir", required=True, help="运行目录路径")

    # resume-from
    sp_resume = sub.add_parser("resume-from", help="从指定阶段重新开始")
    sp_resume.add_argument("stage", choices=STAGES, help="阶段名")
    sp_resume.add_argument("--run-dir", required=True, help="运行目录路径")

    # status
    sp_status = sub.add_parser("status", help="查看流水线状态")
    sp_status.add_argument("--run-dir", required=True, help="运行目录路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "start": cmd_start,
        "continue": cmd_continue,
        "resume-from": cmd_resume_from,
        "status": cmd_status,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
