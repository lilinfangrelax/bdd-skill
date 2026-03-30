# API 自动化步骤

## 新增任务

**POST** `http://127.0.0.1:8765/api/tasks/create`

**Request**

```json
{
  "name": "新增任务xxx",
  "start_time": "2025-01-01",
  "end_time": "2026-03-03",
  "priority": "高",
  "description": "任务描述",
  "tags": []
}
```

**Response**

```json
{
  "ok": true,
  "task": {
    "id": "f83e6b16-7e53-4e3f-be86-d20e9abd5671",
    "name": "新增任务xxx",
    "start_time": "2025-01-01",
    "end_time": "2026-03-03",
    "priority": "高",
    "description": "任务描述",
    "tags": [],
    "deleted": false
  }
}
```

> 💾 提取 `response` 中的 `id` → 存入 `ctx.task_id`

---

## 编辑任务

**POST** `http://127.0.0.1:8765/api/tasks/update`

**Request**

```json
{
  "id": "{{ctx.task_id}}",
  "name": "新增任务xxx-修改任务",
  "start_time": "2025-01-01",
  "end_time": "2026-03-03",
  "priority": "高",
  "description": "任务描述",
  "tags": []
}
```

**Response**

```json
{
  "ok": true,
  "task": {
    "id": "f83e6b16-7e53-4e3f-be86-d20e9abd5671",
    "name": "新增任务xxx-修改任务",
    "start_time": "2025-01-01",
    "end_time": "2026-03-03",
    "priority": "高",
    "description": "任务描述",
    "tags": [],
    "deleted": false
  }
}
```

> 🔗 `id` 引用 来自「新增任务」→ `ctx.task_id`

---

## 假删除任务

**POST** `http://127.0.0.1:8765/api/tasks/delete`

**Request**

```json
{
  "id": "{{ctx.task_id}}"
}
```

**Response**

```json
{
  "ok": true,
  "message": "已假删除",
  "task": {
    "id": "f83e6b16-7e53-4e3f-be86-d20e9abd5671",
    "name": "新增任务xxx-修改任务",
    "start_time": "2025-01-01",
    "end_time": "2026-03-03",
    "priority": "高",
    "description": "任务描述",
    "tags": [],
    "deleted": true
  }
}
```

> 🔗 `id` 引用 来自「新增任务」→ `ctx.task_id`

---

## 永久删除任务

**POST** `http://127.0.0.1:8765/api/tasks/purge`

**Request**

```json
{
  "id": "{{ctx.task_id}}"
}
```

**Response**

```json
  // status: err  // 录制时请求中断，建议重新录制确认响应结构
```

> 🔗 `id` 引用 来自「新增任务」→ `ctx.task_id`

---
