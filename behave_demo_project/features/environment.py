import os
import time

from playwright.sync_api import sync_playwright


def _format_srt_timestamp(total_seconds):
    """Convert elapsed seconds to SRT timestamp format."""
    millis = int(round(total_seconds * 1000))
    hours, remainder = divmod(millis, 3600 * 1000)
    minutes, remainder = divmod(remainder, 60 * 1000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def _write_srt_file(srt_path, subtitles):
    with open(srt_path, "w", encoding="utf-8") as handle:
        for index, item in enumerate(subtitles, start=1):
            handle.write(f"{index}\n")
            handle.write(
                f"{_format_srt_timestamp(item['start'])} --> "
                f"{_format_srt_timestamp(item['end'])}\n"
            )
            handle.write(f"{item['text']}\n\n")


def before_all(context):
    context._playwright_manager = sync_playwright()
    context.playwright = context._playwright_manager.start()
    context.browser = context.playwright.chromium.launch(headless=False)

def before_scenario(context, scenario):
    video_dir = "videos"
    os.makedirs(video_dir, exist_ok=True)

    context.context = context.browser.new_context(
        record_video_dir=video_dir,
        record_video_size={"width": 1280, "height": 720},
    )
    context.page = context.context.new_page()
    context.video_start_time = time.perf_counter()
    context.subtitles = []
    context.current_step_start = None


def before_step(context, step):
    # Record each step's relative start time from scenario video start.
    context.current_step_start = time.perf_counter() - context.video_start_time


def after_step(context, step):
    if context.current_step_start is None:
        return

    end_offset = time.perf_counter() - context.video_start_time
    context.subtitles.append(
        {
            "start": max(context.current_step_start, 0.0),
            "end": max(end_offset, context.current_step_start),
            "text": step.name,
        }
    )

def after_scenario(context, scenario):
    recorded_videos = []
    if hasattr(context, "context") and context.context:
        for page in context.context.pages:
            if page.video:
                recorded_videos.append(page.video)
        context.context.close()

    subtitle_paths = []
    for video in recorded_videos:
        try:
            video_path = video.path()
            srt_path = os.path.splitext(video_path)[0] + ".srt"
            _write_srt_file(srt_path, getattr(context, "subtitles", []))
            subtitle_paths.append(srt_path)
        except OSError:
            pass

    # 可选：只保留失败视频
    """
    if scenario.status == "passed":
        for video in recorded_videos:
            try:
                os.remove(video.path())
            except OSError:
                pass
        for subtitle_path in subtitle_paths:
            try:
                os.remove(subtitle_path)
            except OSError:
                pass
    """

def after_all(context):
    if hasattr(context, "browser") and context.browser:
        context.browser.close()
    if hasattr(context, "playwright") and context.playwright:
        context.playwright.stop()