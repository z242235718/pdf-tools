# Web PDF 工具箱可执行开发计划

版本：v0.1  
日期：2026-06-13  
来源需求：`pdf_toolbox_development_document.md`  
目标读者：Claude Code、Codex、Cursor Agent 等代码执行代理，以及接手开发的人类工程师

## 1. 执行目标

按需求文档实现一个基于 Web 的 PDF 工具箱。开发顺序采用“先完成基础任务闭环，再逐步接入 PDF 工具能力”的方式。

首期 MVP 必须完成：

- 文件上传。
- PDF 转 PNG。
- 图片转 PDF。
- PDF 按页拆分。
- 删除 PDF 指定页。
- 任务创建、任务状态轮询、任务结果下载。
- 简单历史任务。
- 输出文件统一追加时间戳，避免重名。

后续版本完成：

- PDF 加水印。
- PDF 转 Word。
- PDF 版权保护与可溯源。
- 管理后台。
- 生产化部署。

## 2. 给代码代理的执行规则

代码代理执行本计划时必须遵守：

- 每次只执行一个阶段，阶段完成后运行该阶段验收命令。
- 不要跳过测试、格式化、类型检查或接口自测。
- 不要把后续阶段能力提前混进 MVP，除非该能力是当前阶段的公共基础。
- 所有输出文件名必须追加时间戳，格式为 `yyyyMMdd_HHmmss`。
- 所有 PDF 页码输入均按用户视角从 1 开始，内部转换为 0 基索引时必须集中处理。
- 所有文件路径必须使用服务端生成的安全路径，不允许信任用户传入路径。
- 所有耗时处理必须走任务系统，不允许在 HTTP 请求中同步执行完整转换。
- 每个 PDF 功能必须作为独立 service，方便后续替换实现或拆分 Worker。
- 如果当前仓库还没有代码，先按本计划创建项目结构。
- 如果已有代码，先阅读现有结构，保持既有风格，只补齐缺失模块。

## 3. 推荐技术栈

后端：

- Python 3.11 或 3.12。
- FastAPI。
- Uvicorn。
- SQLAlchemy 2.x。
- Alembic。
- SQLite，开发环境使用。
- PostgreSQL，生产环境使用。
- FastAPI BackgroundTasks，开发/MVP 阶段使用。
- Celery + Redis，生产化阶段替换。

PDF 与图片处理：

- PyMuPDF：PDF 渲染 PNG、读取页面信息、水印预览。
- pypdf：PDF 拆分、删除页、元数据、权限加密、页面叠加。
- img2pdf：图片转 PDF，优先用于 JPEG/JPG 无损封装。
- Pillow：图片格式规范化、EXIF 方向处理、透明背景处理、缩放裁切。
- pdf2docx：PDF 转 Word。
- qrcode：版权保护二维码。
- cryptography：签名、哈希或版权 payload。

前端：

- React + TypeScript + Vite，或 Vue 3 + TypeScript + Vite。
- 若无既有偏好，优先 React + TypeScript + Vite。

## 4. 目标目录结构

如果仓库为空，建议创建如下结构：

```text
pdf-tools/
  backend/
    app/
      __init__.py
      main.py
      config.py
      database.py
      api/
        __init__.py
        files.py
        tasks.py
        previews.py
        trace.py
      models/
        __init__.py
        user.py
        file.py
        task.py
        download_log.py
        copyright_fingerprint.py
      schemas/
        __init__.py
        file.py
        task.py
        preview.py
        trace.py
      services/
        __init__.py
        file_service.py
        task_service.py
        cleanup_service.py
        naming_service.py
      pdf_engines/
        __init__.py
        page_ranges.py
        pdf_info.py
        pdf_to_png.py
        images_to_pdf.py
        split_pdf.py
        remove_pages.py
        watermark.py
        pdf_to_word.py
        protect_pdf.py
      workers/
        __init__.py
        task_runner.py
      storage/
        __init__.py
        local_storage.py
      security/
        __init__.py
        file_validation.py
      tests/
        unit/
        integration/
    alembic/
    pyproject.toml
    README.md
  frontend/
    src/
      api/
      components/
      pages/
      routes/
      types/
    package.json
  storage/
    uploads/
    outputs/
    tmp/
  samples/
  pdf_toolbox_development_document.md
  pdf_toolbox_executable_development_plan.md
```

## 5. 环境初始化

### 5.1 后端初始化

目标：

- 创建 FastAPI 后端工程。
- 配置依赖、环境变量、基础启动命令。
- 提供健康检查接口。

建议命令：

```powershell
cd E:\Work\Coding\pdf-tools
mkdir backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy alembic pydantic-settings python-multipart
pip install pymupdf pypdf img2pdf pillow pdf2docx qrcode cryptography
pip install pytest pytest-asyncio httpx ruff mypy
```

建议创建文件：

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/pyproject.toml`

实现要求：

- `GET /health` 返回 `{ "status": "ok" }`。
- 配置项使用 `pydantic-settings`。
- 配置项至少包含：
  - `APP_ENV`
  - `DATABASE_URL`
  - `STORAGE_ROOT`
  - `UPLOAD_RETENTION_HOURS`
  - `OUTPUT_RETENTION_HOURS`
  - `MAX_UPLOAD_MB`
  - `MAX_PDF_PAGES`
  - `MAX_CONCURRENT_TASKS_PER_USER`

验收命令：

```powershell
cd E:\Work\Coding\pdf-tools\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

浏览器或 HTTP 客户端访问：

```text
GET http://127.0.0.1:8000/health
```

完成标准：

- 服务可启动。
- `/health` 返回 200。
- `ruff check .` 无错误。

### 5.2 前端初始化

目标：

- 创建前端工程。
- 先完成空壳页面和 API 客户端。

建议命令：

```powershell
cd E:\Work\Coding\pdf-tools
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install lucide-react
```

建议创建页面：

- `HomePage`
- `PdfToPngPage`
- `ImagesToPdfPage`
- `SplitPdfPage`
- `RemovePdfPagesPage`
- `TaskDetailPage`
- `HistoryPage`

完成标准：

- `npm run dev` 可启动。
- 首页可访问。
- 页面路由可切换。

## 6. 阶段 M1：基础框架与数据模型

### 6.1 数据库模型

目标：

- 建立用户、文件、任务、下载日志、版权指纹模型。
- MVP 阶段可以先使用单用户模式，但表结构预留用户字段。

必须实现的表：

`users`：

- `id`
- `email`
- `phone`
- `display_name`
- `role`
- `created_at`

`files`：

- `id`
- `owner_id`
- `original_name`
- `mime_type`
- `size_bytes`
- `sha256`
- `storage_key`
- `kind`
- `expires_at`
- `created_at`

`tasks`：

- `id`
- `user_id`
- `tool_type`
- `status`
- `input_file_ids`
- `output_file_ids`
- `params`
- `progress`
- `error_code`
- `error_message`
- `created_at`
- `started_at`
- `finished_at`

`download_logs`：

- `id`
- `user_id`
- `file_id`
- `task_id`
- `ip`
- `user_agent`
- `created_at`

`copyright_fingerprints`：

- `id`
- `fingerprint_id`
- `user_id`
- `source_file_id`
- `output_file_id`
- `task_id`
- `visible_text`
- `metadata_payload`
- `verify_url`
- `created_at`

枚举要求：

```text
tool_type:
  pdf_to_word
  pdf_to_png
  images_to_pdf
  split_pdf
  remove_pdf_pages
  watermark_pdf
  protect_pdf

task_status:
  pending
  running
  succeeded
  failed
  expired

file_kind:
  upload
  output
  temp

role:
  user
  admin
```

完成标准：

- Alembic migration 可生成并执行。
- SQLite 数据库可创建全部表。
- 模型字段与需求文档一致。

### 6.2 本地存储服务

目标：

- 统一处理上传、输出、临时文件路径。

建议文件：

- `backend/app/storage/local_storage.py`
- `backend/app/services/file_service.py`

实现要求：

- 使用 UUID 作为服务端存储 key。
- 存储根目录默认为项目根目录下 `storage`。
- 自动创建：
  - `storage/uploads`
  - `storage/outputs`
  - `storage/tmp`
- 不允许直接使用用户文件名作为真实路径。
- 记录原始文件名仅用于展示和输出命名。

完成标准：

- 上传文件可以保存到 `storage/uploads/{uuid}`。
- 输出文件可以保存到 `storage/outputs/{uuid}`。
- 临时目录可以按任务 ID 创建和清理。

## 7. 阶段 M2：通用工具与任务闭环

### 7.1 文件校验

目标：

- 校验上传文件类型、大小、哈希。

建议文件：

- `backend/app/security/file_validation.py`

实现要求：

- 不只依赖扩展名。
- PDF 至少校验文件头或使用 PDF 库尝试读取。
- 图片使用 Pillow 尝试打开并校验格式。
- 计算 SHA-256。
- 上传大小超过限制时返回 `FILE_TOO_LARGE`。
- 类型不支持时返回 `INVALID_FILE_TYPE`。

完成标准：

- 非 PDF/图片文件无法作为对应任务输入。
- 文件哈希正确写入数据库。

### 7.2 输出命名服务

目标：

- 所有输出文件统一追加时间戳。

建议文件：

- `backend/app/services/naming_service.py`

实现函数：

```python
def build_output_filename(
    original_name: str,
    suffix: str,
    extension: str,
    timestamp: datetime,
    extra: str | None = None,
) -> str:
    ...
```

规则：

- 去掉原始扩展名。
- 清理路径分隔符、控制字符、非法字符。
- 限制基础文件名长度。
- 时间戳格式：`yyyyMMdd_HHmmss`。
- 输出格式：
  - 无 extra：`原文件名_功能后缀_时间戳.扩展名`
  - 有 extra：`原文件名_功能后缀_extra_时间戳.扩展名`

必须覆盖示例：

- `contract.pdf` + `word` + `docx` -> `contract_word_20260613_153045.docx`
- `contract.pdf` + `page_001` + `png` -> `contract_page_001_20260613_153045.png`
- `contract.pdf` + `split` + `zip` -> `contract_split_20260613_153045.zip`
- `contract.pdf` + `removed_pages` + `pdf` -> `contract_removed_pages_20260613_153045.pdf`
- `contract.pdf` + `protected` + `pdf` + `AB12-CD34` -> `contract_protected_AB12-CD34_20260613_153045.pdf`

完成标准：

- 单元测试覆盖中文名、空格、非法字符、重复任务、长文件名。

### 7.3 页码范围解析

目标：

- 所有需要页码输入的功能共用一套解析器。

建议文件：

- `backend/app/pdf_engines/page_ranges.py`

输入格式：

- `all`
- `1`
- `1-5`
- `1,3,5`
- `1-3,8,10-12`

实现要求：

- 用户输入页码从 1 开始。
- 输出内部页码列表建议使用 0 基索引。
- 不允许 0、负数、超过总页数。
- 自动去重并按升序处理。
- 空字符串、非法字符、倒序范围返回 `PAGE_RANGE_INVALID`。

额外函数：

```python
def parse_page_range(value: str, total_pages: int) -> list[int]:
    ...

def compute_remaining_pages(delete_pages: list[int], total_pages: int) -> list[int]:
    ...
```

完成标准：

- 单元测试覆盖合法输入、非法输入、越界、重复、删除全部页面。

### 7.4 任务系统

目标：

- 跑通“创建任务 -> 后台处理 -> 查询状态 -> 下载结果”。

建议文件：

- `backend/app/services/task_service.py`
- `backend/app/workers/task_runner.py`
- `backend/app/api/tasks.py`

实现要求：

- `POST /api/tasks` 创建任务。
- 创建后状态为 `pending`。
- 使用 BackgroundTasks 在后台执行。
- 执行开始后状态为 `running`。
- 成功后状态为 `succeeded`，进度 100。
- 失败后状态为 `failed`，写入 `error_code` 和 `error_message`。
- 每个任务的 `params` 必须保存原始参数快照。

任务调度映射：

```text
pdf_to_png -> pdf_engines.pdf_to_png.run
images_to_pdf -> pdf_engines.images_to_pdf.run
split_pdf -> pdf_engines.split_pdf.run
remove_pdf_pages -> pdf_engines.remove_pages.run
watermark_pdf -> pdf_engines.watermark.run
pdf_to_word -> pdf_engines.pdf_to_word.run
protect_pdf -> pdf_engines.protect_pdf.run
```

完成标准：

- 可以创建一个 mock 任务，并在后台生成一个测试输出文件。
- 查询接口能看到状态变化。
- 下载接口能下载输出文件。

## 8. 阶段 M3：文件 API 与前端通用流程

### 8.1 文件上传 API

接口：

```text
POST /api/files
```

请求：

- `multipart/form-data`
- 字段：`file`

响应：

```json
{
  "file_id": "uuid",
  "original_name": "contract.pdf",
  "size_bytes": 123456,
  "mime_type": "application/pdf"
}
```

实现要求：

- 保存上传文件。
- 写入 `files` 表。
- 返回文件 ID。
- 设置默认过期时间。

### 8.2 任务查询 API

接口：

```text
GET /api/tasks/{task_id}
```

响应：

```json
{
  "task_id": "uuid",
  "status": "succeeded",
  "progress": 100,
  "error_code": null,
  "error_message": null,
  "output_files": [
    {
      "file_id": "uuid",
      "download_url": "/api/files/uuid/download",
      "filename": "contract_removed_pages_20260613_153045.pdf"
    }
  ]
}
```

### 8.3 文件下载 API

接口：

```text
GET /api/files/{file_id}/download
```

实现要求：

- 校验文件存在。
- 校验权限，MVP 可用单用户临时逻辑。
- 写入下载日志。
- 返回文件流。

### 8.4 前端通用组件

必须实现：

- 文件上传组件。
- 参数表单容器。
- 任务创建客户端。
- 任务轮询 hook。
- 下载结果组件。
- 错误提示组件。

前端通用流程：

1. 用户进入工具页面。
2. 上传文件。
3. 前端展示文件名、大小、页数或图片数量。
4. 用户配置参数。
5. 点击开始处理。
6. 创建任务。
7. 轮询任务状态。
8. 成功后展示下载按钮。
9. 失败后展示用户可读错误。

完成标准：

- 前端可以上传文件。
- 前端可以创建 mock 任务。
- 前端可以轮询并展示任务状态。

## 9. 阶段 M4：PDF 转 PNG

目标：

- 用户上传 PDF，按页渲染为 PNG。
- 多页输出 ZIP。

建议文件：

- `backend/app/pdf_engines/pdf_to_png.py`
- `backend/app/api/tasks.py`
- `frontend/src/pages/PdfToPngPage.tsx`

参数：

```json
{
  "page_range": "all",
  "dpi": 150,
  "transparent_background": false
}
```

实现流程：

1. 校验 PDF。
2. 如果 PDF 加密，尝试用用户密码打开。
3. 获取总页数。
4. 解析页码范围。
5. 使用 PyMuPDF 打开文档。
6. 对每一页按 DPI 渲染为 pixmap。
7. 使用统一命名规则保存 PNG：
   - `原文件名_page_001_时间戳.png`
8. 如果输出多张图片，打包 ZIP：
   - `原文件名_png_时间戳.zip`
9. 写入输出文件记录。
10. 更新任务状态。

验收测试：

- 上传 1 页 PDF，输出 1 张 PNG。
- 上传 10 页 PDF，选择 `1-3,5`，输出 4 张 PNG。
- DPI 150 与 DPI 300 输出图片尺寸不同。
- 中文、图片、矢量内容渲染正常。
- 多页任务下载 ZIP。

完成标准：

- 后端集成测试通过。
- 前端页面可上传、配置 DPI、配置页码范围、下载结果。

## 10. 阶段 M5：图片转 PDF

目标：

- 一张或多张图片合成为 PDF。
- JPEG/JPG 在无需处理时优先走 img2pdf 无损封装。

建议文件：

- `backend/app/pdf_engines/images_to_pdf.py`
- `frontend/src/pages/ImagesToPdfPage.tsx`

参数：

```json
{
  "merge_mode": "single_pdf",
  "page_size": "original",
  "orientation": "auto",
  "margin": 0,
  "fit_mode": "contain",
  "output_name": null
}
```

实现流程：

1. 校验图片格式和像素大小。
2. 统一 EXIF 方向。
3. 按用户排序读取图片。
4. 判断是否满足 img2pdf 无损封装条件：
   - 输入为 JPEG/JPG。
   - 无需重采样。
   - 无需裁切。
   - 无需透明背景合成。
   - 页面尺寸按图片原始尺寸。
5. 满足条件时使用 img2pdf 直接生成 PDF。
6. 不满足条件时使用 Pillow 做格式转换、透明背景处理、页面适配、缩放或裁切。
7. 输出文件命名：
   - `原文件名_images_时间戳.pdf`
   - 如果用户自定义名称：`用户自定义名称_时间戳.pdf`
8. 写入输出记录。

验收测试：

- 单张 JPG 转 PDF。
- 多张 JPG 合并 PDF，顺序正确。
- PNG 透明背景按设置处理。
- WEBP/BMP/TIFF 可转换。
- 自定义输出文件名仍自动追加时间戳。

完成标准：

- 后端集成测试通过。
- 前端页面可上传多图、调整顺序、生成 PDF。

## 11. 阶段 M6：PDF 按页拆分

目标：

- 用户上传 PDF，按页拆分为一页一个 PDF，输出 ZIP。

建议文件：

- `backend/app/pdf_engines/split_pdf.py`
- `frontend/src/pages/SplitPdfPage.tsx`

参数：

```json
{
  "page_range": "all"
}
```

实现流程：

1. 使用 pypdf 读取 PDF。
2. 处理加密 PDF。
3. 解析页码范围。
4. 循环每一页，创建新的 writer。
5. 添加当前页。
6. 使用统一命名规则写出单页 PDF：
   - `原文件名_page_001_时间戳.pdf`
7. 打包 ZIP：
   - `原文件名_split_时间戳.zip`
8. 写入输出记录。

验收测试：

- 10 页 PDF 拆分后 ZIP 内有 10 个 PDF。
- 每个 PDF 只有 1 页。
- 选择 `2-4` 时只输出 3 个 PDF。
- 原页面尺寸和旋转角度保持正确。

完成标准：

- 后端集成测试通过。
- 前端页面可上传 PDF、输入页码范围、下载 ZIP。

## 12. 阶段 M7：删除 PDF 指定页

目标：

- 用户上传 PDF，输入删除页码或范围，输出删除指定页后的 PDF。

建议文件：

- `backend/app/pdf_engines/remove_pages.py`
- `frontend/src/pages/RemovePdfPagesPage.tsx`

参数：

```json
{
  "delete_pages": "2,4-6"
}
```

实现流程：

1. 使用 pypdf 读取 PDF。
2. 处理加密 PDF。
3. 获取总页数。
4. 解析删除页码集合。
5. 校验删除后至少保留 1 页。
6. 计算保留页集合。
7. 按原顺序将保留页面写入新的 writer。
8. 输出文件命名：
   - `原文件名_removed_pages_时间戳.pdf`
9. 写入输出记录。

验收测试：

- 删除 10 页 PDF 中的第 2、4-6 页，输出 PDF 剩余 6 页。
- 输出页面顺序正确。
- 删除页不存在于输出文件。
- 删除全部页面时任务失败。
- 页码越界时返回 `PAGE_RANGE_INVALID`。

完成标准：

- 后端集成测试通过。
- 前端页面可上传 PDF、输入删除页、下载结果。

## 13. 阶段 M8：历史任务与 MVP 收口

目标：

- MVP 首期可完整使用。

必须实现：

- 历史任务列表。
- 任务详情页。
- 下载结果。
- 删除任务和文件，MVP 可软删除或直接标记过期。
- 错误信息统一展示。

历史任务接口建议：

```text
GET /api/tasks
DELETE /api/tasks/{task_id}
```

MVP 验收清单：

- 文件上传可用。
- PDF 转 PNG 可用。
- 图片转 PDF 可用。
- PDF 按页拆分可用。
- 删除 PDF 指定页可用。
- 所有输出文件名带时间戳。
- 任务失败有明确错误码和错误信息。
- 前端可完成上传、处理、下载闭环。
- 单元测试和集成测试通过。

## 14. 阶段 M9：PDF 加水印

目标：

- 支持文字水印和图片水印。

建议文件：

- `backend/app/pdf_engines/watermark.py`
- `backend/app/api/previews.py`
- `frontend/src/pages/WatermarkPdfPage.tsx`

文字水印参数：

```json
{
  "watermark_type": "text",
  "text": "内部资料",
  "font_size": 32,
  "color": "#888888",
  "opacity": 0.25,
  "rotation": -30,
  "position": "center",
  "tile_mode": "full",
  "layer": "foreground",
  "page_range": "all"
}
```

图片水印参数：

```json
{
  "watermark_type": "image",
  "watermark_file_id": "uuid",
  "scale": 0.5,
  "opacity": 0.25,
  "rotation": -30,
  "position": "center",
  "tile_mode": "single",
  "layer": "foreground",
  "page_range": "all"
}
```

实现要求：

- 至少支持第一页低清预览。
- 支持页码范围。
- 支持单个、全页平铺、密集形文字水印。
- 支持单个、自定义铺满个数、全页铺满图片水印。
- 输出命名：`原文件名_watermarked_时间戳.pdf`。

验收测试：

- 水印出现在指定页。
- 透明度、位置、旋转正确。
- 原 PDF 页数、尺寸、可读性不被破坏。
- 预览与最终输出尽量一致。

## 15. 阶段 M10：PDF 转 Word

目标：

- 使用 pdf2docx 实现基础转换。

建议文件：

- `backend/app/pdf_engines/pdf_to_word.py`
- `frontend/src/pages/PdfToWordPage.tsx`

参数：

```json
{
  "password": null
}
```

实现要求：

- 输出 `.docx`。
- 输出命名：`原文件名_word_时间戳.docx`。
- 对扫描版 PDF 给出需要 OCR 的提示。
- 失败时不产生空文件或损坏文件。
- 产品文案必须说明“尽力还原”，不承诺 100% 保真。

验收测试：

- 文本型 PDF 可转换为 docx。
- 合同、报告、简历类 PDF 主要文本和图片可读。
- 扫描版 PDF 有明确提示。

## 16. 阶段 M11：版权保护与可溯源

目标：

- 为 PDF 分发生成可追踪指纹。

建议文件：

- `backend/app/pdf_engines/protect_pdf.py`
- `backend/app/api/trace.py`
- `frontend/src/pages/ProtectPdfPage.tsx`
- `frontend/src/pages/TraceQueryPage.tsx`

参数：

```json
{
  "visible_text": "授权给：张三",
  "add_qrcode": true,
  "set_permissions": false,
  "page_range": "all"
}
```

实现流程：

1. 创建任务时生成 `fingerprint_id`。
2. 生成服务端签名 payload。
3. 将 payload 写入 `copyright_fingerprints`。
4. 将短码或用户信息写入可见水印。
5. 将完整或签名后的 payload 写入 PDF 元数据。
6. 可选生成二维码并加入页面角落。
7. 可选设置 PDF 权限加密。
8. 输出命名：`原文件名_protected_指纹ID_时间戳.pdf`。

验收测试：

- 每次生成的受保护 PDF 都有唯一追踪 ID。
- 下载记录可查询。
- 从生成文件中至少能解析出一种指纹信息。
- 同一原文件分发给不同用户时，输出文件可区分来源。

## 17. 阶段 M12：清理、权限和管理后台

目标：

- 完成基本运维能力。

必须实现：

- 过期文件清理。
- 用户任务列表。
- 管理员任务列表。
- 管理员查看失败日志。
- 文件大小、保留周期、并发限制配置。
- 后台访问文件记录审计日志。

清理规则：

- 上传文件默认保留 24 小时。
- 输出文件默认保留 24 小时。
- 版权指纹记录默认保留 180 天，可配置。
- 审计日志默认保留 180 天，可配置。

完成标准：

- 清理任务可手动触发。
- 过期文件不会再被下载。
- 管理员可以查看所有任务。

## 18. 阶段 M13：生产化

目标：

- 从本地 MVP 过渡到可部署版本。

必须完成：

- SQLite 切 PostgreSQL。
- BackgroundTasks 切 Celery + Redis。
- API 服务和 Worker 分开部署。
- 增加 Dockerfile。
- 增加 docker-compose。
- 增加任务超时。
- 增加 Worker 内存和并发限制。
- 增加对象存储适配，可选 S3/MinIO。

生产架构：

```text
Nginx
  |
FastAPI API 服务，多实例
  |
PostgreSQL + Redis
  |
Celery Worker，多实例
  |
Object Storage
```

完成标准：

- `docker compose up` 可启动完整服务。
- API 与 Worker 分离。
- 大文件任务不会阻塞 API。
- 任务超时后状态变为 `failed`，错误码为 `TASK_TIMEOUT`。

## 19. 测试计划

### 19.1 单元测试

必须覆盖：

- 页码范围解析。
- 删除页集合与保留页集合计算。
- 文件类型识别。
- 输出文件命名。
- 水印坐标计算。
- 文字水印单个、全页平铺、密集形坐标和透明度参数计算。
- 图片水印单个、自定义铺满个数、全页铺满坐标计算。
- DPI 到矩阵/尺寸换算。
- 指纹 ID 生成和签名校验。

建议命令：

```powershell
cd E:\Work\Coding\pdf-tools\backend
pytest app/tests/unit
```

### 19.2 集成测试

必须覆盖：

- 上传 PDF 后转 PNG。
- 上传多图后合成 PDF。
- 上传 JPEG/JPG 后通过 img2pdf 生成 PDF，验证无损嵌入路径不触发重编码。
- 拆分 10 页 PDF，得到 10 个单页 PDF。
- 删除 10 页 PDF 中的第 2、4-6 页，输出 PDF 剩余 6 页且顺序正确。
- 尝试删除全部页面时任务失败并返回明确错误。
- 添加文字水印后输出文件可打开。
- 添加图片水印后透明度正确。
- 版权保护文件可查询指纹。

建议命令：

```powershell
cd E:\Work\Coding\pdf-tools\backend
pytest app/tests/integration
```

### 19.3 样例文件

应准备：

- 普通文本 PDF。
- 含中文字体 PDF。
- 含图片 PDF。
- 扫描版 PDF。
- 横向页面 PDF。
- 混合页面尺寸 PDF。
- 加密 PDF。
- 大页数 PDF。
- 透明 PNG。
- 超大分辨率图片。

## 20. 错误码

后端必须使用统一错误码：

| 错误码 | 含义 |
| --- | --- |
| INVALID_FILE_TYPE | 文件类型不支持 |
| FILE_TOO_LARGE | 文件过大 |
| PDF_ENCRYPTED | PDF 已加密，需要密码 |
| PDF_PASSWORD_INVALID | PDF 密码错误 |
| PAGE_RANGE_INVALID | 页码范围非法 |
| PAGE_LIMIT_EXCEEDED | 页数超出限制 |
| IMAGE_TOO_LARGE | 图片像素过大 |
| CONVERSION_FAILED | 转换失败 |
| REMOVE_PAGES_FAILED | 删除页面失败 |
| WATERMARK_FAILED | 添加水印失败 |
| STORAGE_FAILED | 文件存储失败 |
| TASK_TIMEOUT | 任务超时 |
| PERMISSION_DENIED | 无权限访问 |

错误处理要求：

- API 返回用户可理解的 `error_message`。
- 日志记录技术细节。
- 不在日志中记录完整敏感文件内容。
- 失败任务不得留下半成品作为可下载结果。

## 21. 每个阶段的通用完成定义

一个阶段只有满足以下条件才算完成：

- 代码已实现。
- 数据模型或接口文档已更新。
- 单元测试已添加或更新。
- 集成测试已添加或更新，若阶段涉及 API。
- 前端页面已接入，若阶段涉及用户操作。
- 输出文件命名符合时间戳规则。
- 错误码和错误文案符合统一规范。
- 本地运行验证通过。
- 没有引入无关重构。

## 22. 建议给代码代理的阶段执行提示词

可以把下面模板交给 Claude Code 或 Codex：

```text
请阅读 pdf_toolbox_development_document.md 和 pdf_toolbox_executable_development_plan.md。
只执行阶段 M{编号}：{阶段名称}。

要求：
1. 先检查现有代码结构，不要覆盖用户已有改动。
2. 按计划创建或修改文件。
3. 保持每个 PDF 功能为独立 service。
4. 输出文件名必须追加 yyyyMMdd_HHmmss 时间戳。
5. 添加必要单元测试和集成测试。
6. 运行本阶段验收命令。
7. 最后汇报修改文件、测试结果和未完成风险。
```

## 23. 外部文档参考

实现时优先查阅官方文档：

- FastAPI BackgroundTasks：<https://fastapi.tiangolo.com/tutorial/background-tasks/>
- FastAPI 文件上传：<https://fastapi.tiangolo.com/tutorial/request-files/>
- SQLAlchemy ORM：<https://docs.sqlalchemy.org/>
- Alembic：<https://alembic.sqlalchemy.org/>
- PyMuPDF Page.get_pixmap：<https://pymupdf.readthedocs.io/en/latest/recipes-images.html>
- pypdf PdfWriter：<https://pypdf.readthedocs.io/>
- img2pdf：<https://pypi.org/project/img2pdf/>
- Pillow 图片格式：<https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html>
- pdf2docx：<https://pypi.org/project/pdf2docx/>
