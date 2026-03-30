# BDD Steps 确认

勾选需要纳入自动化的接口，取消勾选不需要的。

## Step 1：打开页面

- [x] `GET` http://127.0.0.1:8765/api/tasks → ✅ 200

## Step 2：新增任务

- [x] `POST` http://127.0.0.1:8765/api/tasks/create → ✅ 201

## Step 3：编辑任务

- [x] `GET` http://127.0.0.1:8765/api/tasks → ✅ 200
- [x] `POST` http://127.0.0.1:8765/api/tasks/update → ✅ 200

## Step 4：假删除任务

- [x] `GET` http://127.0.0.1:8765/api/tasks → ✅ 200
- [x] `POST` http://127.0.0.1:8765/api/tasks/delete → ✅ 200

## Step 5：永久删除任务

- [x] `GET` http://127.0.0.1:8765/api/tasks → ✅ 200
- [x] `POST` http://127.0.0.1:8765/api/tasks/purge → ⚠️ err
