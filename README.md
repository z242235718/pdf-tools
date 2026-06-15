# Web PDF Tools

这是 Web PDF 工具箱的开发工作区。当前环境已经初始化：

- 后端：FastAPI + SQLAlchemy + PDF 处理依赖。
- 前端：React + TypeScript + Vite。
- 本地存储：`storage/uploads`、`storage/outputs`、`storage/tmp`。
- 执行计划：`pdf_toolbox_executable_development_plan.md`。

## Quick Start（一键启动）

在项目**根目录**执行一条命令即可同时启动前后端：

```bash
# 首次运行前安装依赖（已完成则跳过）
npm install

# 初始化数据库（首次或拉取更新后执行）
cd backend && .venv\Scripts\python.exe -m alembic upgrade head && cd ..

# 一键启动前后端
npm run dev
```

启动后：
- 🖥️ 前端：http://localhost:5173
- ⚙️  后端 API：http://127.0.0.1:8001（通过 Vite 代理转发）
- 🩺 健康检查：http://localhost:5173/health

按 `Ctrl+C` 同时终止两个服务。

也可以单独启动任一端：

```bash
npm run dev:backend   # 仅后端
npm run dev:frontend  # 仅前端
```

---

### 传统方式（分别启动）

## Backend

```powershell
cd E:\Work\Coding\pdf-tools\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

健康检查：

```text
http://127.0.0.1:8000/health
```

检查命令：

```powershell
cd E:\Work\Coding\pdf-tools\backend
$env:RUFF_CACHE_DIR="..\.cache\ruff"
$env:PYTEST_ADDOPTS="-o cache_dir=../.cache/pytest"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

## Frontend

PowerShell 上直接执行 `npm` 可能被执行策略拦截，请使用 `npm.cmd`。

```powershell
cd E:\Work\Coding\pdf-tools\frontend
npm.cmd run dev
```

构建和检查：

```powershell
cd E:\Work\Coding\pdf-tools\frontend
npm.cmd run lint
npm.cmd run build
```

## Notes

- 当前机器 Python 是 3.14.5。MVP 依赖已经安装通过。
- `cryptography` 已放到后端可选依赖组 `protect`，用于后续版权保护阶段。若安装失败，建议使用 Python 3.12 创建虚拟环境。
- Vite 脚本已使用 `--configLoader native`，避免在 `node_modules/.vite-temp` 写临时文件时触发权限问题。
- TypeScript、Ruff、Pytest、Vite 缓存统一放在根目录 `.cache`。
