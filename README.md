# PDF Tools · Web 版 PDF 工具箱

> 一个完全离线、本地优先的 PDF 工具箱：覆盖日常 80% 的 PDF 处理需求（转 Word / 转图片 / 拆分 / 删页 / 水印 / 版权保护与溯源），既可作为本地 Web 应用开发与二次定制，也能打包成单 EXE 给最终用户开箱即用。

---

## 目录

- [功能一览](#功能一览)
- [在线演示 / 桌面版](#在线演示--桌面版)
- [快速开始](#快速开始)
  - [一键启动（开发模式）](#一键启动开发模式)
  - [传统方式（分别启动）](#传统方式分别启动)
- [桌面 EXE 版](#桌面-exe-版)
- [技术栈](#技术栈)
- [兼容性](#兼容性)
- [项目结构](#项目结构)
- [关键配置](#关键配置)
- [开发与测试](#开发与测试)
- [重新打包 EXE](#重新打包-exe)
- [数据与隐私](#数据与隐私)
- [路线图](#路线图)
- [许可](#许可)

---

## 功能一览

| 序号 | 功能 | 说明 |
| --- | --- | --- |
| 1 | **PDF → Word** | 基于 `pdf2docx` 还原段落、表格、图片；保留原始版式。 |
| 2 | **PDF → PNG** | 支持指定页码 / 页码区间、DPI（72–300）；多页时打包为 ZIP。 |
| 3 | **图片 → PDF** | 拖拽多张图片（JPG / PNG / WebP），按文件名排序合并为单 PDF。 |
| 4 | **PDF 拆分** | 按页码区间拆分，逐区间生成独立 PDF 并打包 ZIP。 |
| 5 | **删除页** | 通过页码区间从原 PDF 中移除指定页面并输出新文件。 |
| 6 | **PDF 水印** | 文字水印 / 图片水印，支持旋转、透明度、等距分布；时间戳可选。 |
| 7 | **PDF 版权保护与溯源** | 可见文字标识 + 验签指纹（写入 PDF 元数据）+ QR 码溯源页 + 可选 PDF 加密 / 权限锁。 |

每一个工具都遵循统一的**「上传 → 提交任务 → 后台异步执行 → 历史下载」**闭环，所有任务持久化到本地 SQLite，可在「历史」页面搜索、查看、重下。

进阶：

- **历史与任务详情**：分页、关键字搜索、单条清空与批量清空、字体大小可调（设置页）。
- **设置页**：域名（用于生成 QR 验签链接）、密码长度、QR 是否可见、上传/产物保留时长等。
- **溯源查询**：通过指纹 ID 反查历史授权记录（`/trace-query`）。

---

## 桌面 EXE 版

> 最终用户可直接使用预打包的 EXE，**无需安装 Python / Node**。

| 系统 | 启动 EXE |
| --- | --- |
| 64 位 Windows 10 / 11 | `RELEASE/pdf-tools-x64/pdf-tools-x64.exe` |
| 32 位 Windows 7 / 8 / 10 | `RELEASE/pdf-tools-x86/pdf-tools-x86.exe` |

使用方式：拷贝整个 `pdf-tools-x64\`（或 `pdf-tools-x86\`）目录到任意位置 → 双击 EXE → 自动开浏览器访问 `http://127.0.0.1:8000`。关闭控制台窗口即停服。

更详细说明见 [RELEASE/README-用户使用说明.md](RELEASE/README-用户使用说明.md)。

---

## 快速开始

### 环境要求

| 组件 | 版本 |
| --- | --- |
| Node.js | ≥ 20 |
| Python | 3.11 – 3.14（推荐 3.12，32 位打包需 3.11.9 embeddable） |
| OS | Windows 10/11、macOS、Linux（开发模式可跨平台；EXE 仅 Windows） |

### 一键启动（开发模式）

在仓库**根目录**执行：

```bash
# 首次运行：安装前后端依赖
npm install
cd frontend && npm install && cd ..

# 初始化数据库
cd backend && .venv\Scripts\python.exe -m alembic upgrade head && cd ..

# 同时启动后端 (:8001) + 前端 (:5173)
npm run dev
```

启动后：

- 🖥️ 前端界面：[http://localhost:5173](http://localhost:5173)
- ⚙️ 后端 API：[http://127.0.0.1:8001](http://127.0.0.1:8001)（通过 Vite 代理转发）
- 🩺 健康检查：[http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)

按 `Ctrl + C` 同时终止两个服务。也可单独启动：

```bash
npm run dev:backend   # 仅后端
npm run dev:frontend  # 仅前端
```

### 传统方式（分别启动）

<details>
<summary>PowerShell（Windows）</summary>

```powershell
# 后端
cd E:\Coding\pdf-tools\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8001

# 前端（注意：PowerShell 直接执行 npm 可能被策略拦截，请用 npm.cmd）
cd E:\Coding\pdf-tools\frontend
npm.cmd run dev
```

PowerShell 上推荐 `npm.cmd`；Linux/macOS 直接 `npm` 即可。

</details>

---

## 技术栈

### 后端（`backend/`）

| 类别 | 选型 |
| --- | --- |
| Web 框架 | FastAPI 0.115 + Uvicorn |
| ORM / 迁移 | SQLAlchemy 2.0 + Alembic |
| PDF 解析 / 生成 | PyMuPDF (`fitz`) ≥ 1.24、`pypdf` ≥ 4.3、`pdf2docx` ≥ 0.5.8 |
| 图片 / 文档 | Pillow ≥ 10.4、`img2pdf` ≥ 0.5.1、`qrcode` ≥ 7.4 |
| 安全 / 加密 | `cryptography` ≥ 43（`protect` 额外依赖组） |
| 配置 | pydantic-settings |

### 前端（`frontend/`）

| 类别 | 选型 |
| --- | --- |
| 框架 | React 19 + React Router 7 |
| 语言 | TypeScript 6 |
| 构建 | Vite 8（`base: './'`，子路径友好） |
| HTTP | Axios |
| 图标 | lucide-react |

### 桌面打包

PyInstaller onedir 模式，分别构建 x64 / x86 启动器；前端 `dist` 通过环境变量 `PDF_TOOLS_FRONTEND_DIST` 挂载到同一 FastAPI 进程，无跨域。

---

## 兼容性

### 运行平台

| 模式 | Windows | macOS | Linux |
| --- | --- | --- | --- |
| 开发模式（前后端分离） | ✅ 10 / 11 | ✅ | ✅ |
| 桌面 EXE（x64） | ✅ 10 / 11（实测） | ❌ | ❌ |
| 桌面 EXE（x86） | ✅ 7 / 8 / 10 / 11 | ❌ | ❌ |

64 位 EXE **不能在** Windows 7 32-bit / 不支持 SSE4.2 的老机器上运行 —— 这种环境下请使用 x86 版本。

### Python 与依赖

- `requires-python = ">=3.11,<3.15"`。
- 32 位 EXE 的关键依赖锁定：`SQLAlchemy` 2.0.x + 强制 `--no-deps` 跳过 `greenlet`（cp311-win32 无 wheel，运行时通过纯同步 API 规避）；`pypdf` 锁 4.3.x；`pillow` 锁 10.4.x。
- 若 `cryptography` 安装失败，建议改用 Python 3.12 创建虚拟环境。

### 浏览器

前端使用现代 ES2020+ 特性，需 Chrome / Edge / Firefox 最近 2 个大版本。

---

## 项目结构

```
pdf-tools/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由：files / tasks / previews / trace / settings
│   │   ├── models/          # SQLAlchemy 模型：Task / File / Setting / CopyrightFingerprint / User / DownloadLog
│   │   ├── pdf_engines/     # 7 个工具的具体实现
│   │   ├── services/        # 业务逻辑层（任务、文件、命名）
│   │   ├── schemas/         # Pydantic 数据契约
│   │   ├── security/        # 文件校验
│   │   ├── workers/         # 后台任务执行器
│   │   ├── storage/         # 本地存储抽象
│   │   └── main.py          # create_app() 工厂（同时支持 dev / 单 EXE 模式）
│   ├── alembic/             # 数据库迁移
│   ├── pdf-tools-x64.spec   # PyInstaller x64 打包脚本
│   ├── pdf-tools-x86.spec   # PyInstaller x86 打包脚本
│   └── run.py               # 单 EXE 入口（启动 uvicorn + 自动开浏览器）
├── frontend/                # React + Vite
│   ├── src/
│   │   ├── pages/           # 7 个工具页 + 历史 / 设置 / 溯源 / 任务详情
│   │   ├── components/      # 通用组件（Layout 等）
│   │   └── api/             # Axios 封装
│   └── vite.config.ts       # base: './'，dev 时代理 /api → 8001
├── RELEASE/                 # 已打包的桌面 EXE（pdf-tools-x64 / pdf-tools-x86）
├── samples/                 # 示例文件
├── storage/                 # 运行时 uploads / outputs / tmp
├── package.json             # concurrently 一键启动
└── README.md
```

---

## 关键配置

后端通过环境变量或 `.env` 覆盖（[pydantic-settings](backend/app/config.py)）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_ENV` | `development` | 运行环境标识 |
| `DATABASE_URL` | `sqlite:///./pdf_tools.db` | 数据库连接串 |
| `STORAGE_ROOT` | `../storage` | 上传 / 产物 / 临时目录 |
| `UPLOAD_RETENTION_HOURS` | `24` | 上传文件保留时长（小时） |
| `OUTPUT_RETENTION_HOURS` | `24` | 产物文件保留时长（小时） |
| `MAX_UPLOAD_MB` | `100` | 单文件最大体积（MB） |
| `MAX_PDF_PAGES` | `500` | 单 PDF 最大页数 |
| `MAX_CONCURRENT_TASKS_PER_USER` | `2` | 单用户最大并发任务数 |
| `FINGERPRINT_SECRET` | `dev-fingerprint-secret-do-not-use-in-prod` | 版权指纹 HMAC 签名密钥（**生产务必替换**） |
| `PDF_TOOLS_PORT` | `8000`（EXE） | 单 EXE 启动端口，冲突时自动降级 |
| `PDF_TOOLS_STORAGE_ROOT` | `<exe_dir>/storage` | 单 EXE 的存储目录覆盖 |
| `PDF_TOOLS_FRONTEND_DIST` | （dev 无） | 单 EXE 模式下指向 `frontend/dist` |

`frontend/vite.config.ts` 中 dev server 默认代理 `/api → 127.0.0.1:8001`。

---

## 开发与测试

```bash
# 后端：代码检查、类型检查、单元/集成测试
cd backend
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check

# 前端：lint + 类型构建
cd frontend
npm.cmd run lint
npm.cmd run build
```

测试缓存统一放到根目录 `.cache/`，避免污染工作区。

---

## 重新打包 EXE

详见 [RELEASE/README-打包说明.md](RELEASE/README-打包说明.md)。简要流程：

```powershell
# 64 位（推荐）
cd backend
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean pdf-tools-x64.spec
# 产物：backend\dist\pdf-tools-x64\

# 32 位（需要 Python 3.11.9 embeddable + 特殊依赖锁，参考打包说明）
```

冒烟测试：

```bash
./pdf-tools-x64.exe &
sleep 5
curl http://127.0.0.1:8000/health
curl -X POST -F "file=@samples/test_doc.pdf" http://127.0.0.1:8000/api/files
curl -X POST -H "Content-Type: application/json" \
  -d '{"tool_type":"pdf_to_png","input_file_ids":[1],"params":{"page_range":"all","dpi":150}}' \
  http://127.0.0.1:8000/api/tasks
```

---

## 数据与隐私

- **完全本地**：所有 PDF 与图片处理都在本机完成，**不上传任何文件到服务器**。
- **不写注册表 / 服务 / 计划任务**：卸载 = 删除整个 `pdf-tools-x64` 目录。
- **存储位置（EXE 版）**：`<exe_dir>/storage/{uploads,outputs,tmp}` 与 `<exe_dir>/pdf_tools.db`。
- **默认清理策略**：上传与产物 24 小时后由后台任务自动清理（可在 `.env` 调整）。
- **版权指纹 HMAC 密钥**：开发默认值为占位符，**生产部署务必替换为高熵随机串**。

---

## 路线图

- [ ] 多用户鉴权（当前 `user` 模型已就绪，路由层未启用）
- [ ] 下载审计日志（`DownloadLog` 模型已存在）
- [ ] 任务失败重试与指数退避
- [ ] macOS / Linux 桌面包
- [ ] 前端 i18n

---

## 许可

本仓库源码遵循仓库根目录 `LICENSE`（如未提供，按默认保留所有权利；EXE 内包含 PyMuPDF 等 GPL / AGPL 兼容组件，商业分发请自行评估许可）。
