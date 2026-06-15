# Web PDF 工具箱需求与开发文档

版本：v0.1  
日期：2026-06-06  
技术方向：Python Web 应用

## 1. 项目目标

建设一个基于 Web 界面的 PDF 工具箱，面向个人用户、企业内勤、法务、行政、教育和内容分发场景，提供常用 PDF 转换、拆分、水印、版权追踪能力。

首期目标不是做一个完整的在线办公套件，而是做一个稳定、易用、可部署、可扩展的 PDF 处理平台。用户上传文件后选择工具和参数，系统异步处理任务，处理完成后提供下载，并在服务端保留必要的任务状态、审计日志和可溯源信息。

## 2. 功能范围

### 2.1 PDF 转 Word

用户上传 PDF 文件，系统输出 `.docx` 文件。

核心需求：

- 支持单个 PDF 上传。
- 支持输出 `.docx`。
- 默认输出文件名为 `原文件名_word_时间戳.docx`。
- 显示处理进度和失败原因。
- 对扫描版 PDF 提示需要 OCR，首期可作为增强功能。
- 保留尽可能多的文本、图片、表格和页面布局。

重要边界：

- PDF 本质上更接近固定版式文件，很多 PDF 不包含真实的段落、标题、表格结构。转换为 Word 时只能做版面重建，不能承诺 100% 保真。
- 首期建议使用 `pdf2docx` 实现基础转换；对高保真要求较高的企业版，可预留商业转换引擎或 Microsoft Word/LibreOffice 服务化适配层。
- 扫描版 PDF 如果没有 OCR 文本层，直接转 Word 只能得到图片型 Word。后续可接入 OCR 生成可编辑文本。

验收标准：

- 文本型 PDF 可成功转换为 `.docx`。
- 普通合同、报告、简历类 PDF 的主要文本和图片可读。
- 失败时返回明确错误，不产生空文件或损坏文件。

### 2.2 PDF 转 PNG

用户上传 PDF，系统按页渲染为 PNG 图片，输出 ZIP 包或单页预览下载。

核心需求：

- 支持选择页码范围，例如全部、1-3、5、8-10。
- 支持 DPI 参数，建议默认 150 DPI，可选 72、150、200、300。
- 支持输出文件命名规则，例如 `原文件名_page_001_时间戳.png`。
- 多页 PDF 默认打包为 `.zip` 下载，ZIP 默认命名为 `原文件名_png_时间戳.zip`。
- 支持透明背景开关作为增强项。

技术建议：

- 使用 PyMuPDF 渲染页面。PyMuPDF 官方文档提供了通过 `Page.get_pixmap()` 将每一页生成 PNG 的做法。
- 大文件或高 DPI 任务必须异步处理，避免阻塞 Web 请求。

验收标准：

- 每页图片尺寸与 DPI 参数一致。
- 页码顺序正确。
- 中文、图片、矢量图形渲染正常。

### 2.3 图片转换成 PDF

用户上传一张或多张图片，系统合成为一个 PDF 或分别转换为多个 PDF。

核心需求：

- 支持 JPG、JPEG、PNG、WEBP、BMP、TIFF。
- 支持多图合并成一个 PDF。
- 支持图片顺序调整。
- 支持页面尺寸参数：按图片原始尺寸、A4、Letter、自定义宽高。
- 支持方向：自动、纵向、横向。
- 支持边距、适配方式：等比适配、填充裁切、原始尺寸。
- 支持输出文件名设置，最终文件名必须自动追加时间戳，例如 `自定义文件名_时间戳.pdf`。

技术建议：

- 引入 `img2pdf` 作为图片转 PDF 的优先实现路径；对 JPEG/JPG 输入应采用无损嵌入，直接将图片数据封装为 PDF，避免不必要的重编码和质量损失。
- 使用 Pillow 作为补充处理层，用于读取 EXIF、处理透明背景、WEBP/BMP/TIFF 等格式转换、页面适配、裁切、缩放和必要的预处理。
- 当用户选择按图片原始尺寸、等比适配且输入为 JPEG/JPG 时，应优先走 `img2pdf` 无损路径；当需要透明背景合成、填充裁切、统一页面尺寸或非 JPEG 格式规范化时，可先用 Pillow 生成中间图像再封装。

验收标准：

- 多图合成后页面顺序与用户排序一致。
- JPEG/JPG 在无需缩放、裁切或透明合成时可无损嵌入 PDF，不发生重编码。
- PNG 透明背景可按设置转换为白底或保留兼容处理。
- 大图不被异常拉伸或旋转。

### 2.4 PDF 按页拆分

用户上传一个 PDF，系统按页拆分为一页一个 PDF，最终输出 ZIP 包。

核心需求：

- 每页输出一个独立 PDF。
- 支持页码范围选择。
- 支持命名规则，例如 `原文件名_page_001_时间戳.pdf`。
- 输出 ZIP 默认命名为 `原文件名_split_时间戳.zip`。
- 支持保留元数据，增强项可支持保留书签片段。
- 支持加密 PDF，用户输入密码后处理。

技术建议：

- 使用 `pypdf` 读取原 PDF，并为每一页创建新的 `PdfWriter` 输出。
- 对损坏 PDF、加密 PDF、超大页数 PDF 做异常捕获和任务失败状态记录。

验收标准：

- 输出 ZIP 中的 PDF 数量与处理页数一致。
- 每个 PDF 只有一页。
- 原文件旋转角度和页面尺寸保持正确。

### 2.5 删除 PDF 指定页

用户上传一个 PDF，输入需要删除的页码或页码范围，系统输出删除指定页面后的新 PDF。

核心需求：

- 支持删除单页、多页和页码范围，例如 `3`、`1,3,5`、`2-4`、`1,3-5,8`。
- 支持按保留页逻辑预览删除结果，例如展示删除后剩余页数和页码映射。
- 删除页后输出单个 PDF，默认命名为 `原文件名_removed_pages_时间戳.pdf`。
- 至少保留 1 页，禁止删除全部页面。
- 支持加密 PDF，用户输入密码后处理。
- 支持保留原 PDF 元数据；增强项可支持保留仍然有效的书签片段。

技术建议：

- 使用 `pypdf` 读取原 PDF，解析用户指定的删除页集合，将未删除页面按原顺序写入新的 `PdfWriter`。
- 页码解析与 PDF 转 PNG、PDF 拆分、水印页码范围共用同一套页码范围解析器，避免不同功能对 `1,3-5` 等表达式理解不一致。
- 对删除全部页面、页码越界、重复页码、加密 PDF 密码错误等情况返回明确错误信息。

验收标准：

- 输出 PDF 页数等于原页数减去删除页数。
- 未删除页面的顺序、旋转角度和页面尺寸保持正确。
- 删除页不存在于输出文件中。
- 删除全部页面时任务失败，并返回用户可理解的错误。

### 2.6 给 PDF 添加水印

用户上传 PDF，选择文字水印或图片水印，调节参数后输出新 PDF。

文字水印参数：

- 水印文本。
- 字体，默认内置中文字体或系统可用字体。
- 字号。
- 颜色。
- 透明度。
- 旋转角度。
- 位置：居中、左上、右上、左下、右下、自定义坐标。
- 平铺模式：单个、全页平铺、密集形。
- 密集形文字水印用于隐式版权指纹或防泄露追踪，默认采用极小字号、低透明度和高密度重复排布，肉眼正常阅读时不可见或近乎不可见，放大数倍后可辨认。
- 层级：覆盖在内容上方、置于内容下方。
- 页码范围。

图片水印参数：

- 水印图片上传。
- 宽度、高度或缩放比例。
- 透明度。
- 旋转角度。
- 位置。
- 平铺模式：单个、自定义铺满个数、全页铺满。
- 自定义铺满个数模式只在页面中间竖向排列，用户设置数量后系统按页面高度等距分布。
- 层级。
- 页码范围。

输出命名：

- 添加水印后输出单个 PDF，默认命名为 `原文件名_watermarked_时间戳.pdf`。

预览需求：

- 前端至少提供第一页预览。
- 参数调整后可生成低清预览图。
- 预览与最终输出要尽量一致。

技术建议：

- 使用 PyMuPDF 直接在页面上插入文字或图片，适合实现位置、透明度、旋转、前景/背景控制。
- 或使用 ReportLab 生成水印 PDF，再用 pypdf 的 `merge_page` 叠加。该方案适合复杂文字排版，但坐标和透明度控制要做好封装。

验收标准：

- 水印在指定页出现。
- 透明度、位置、旋转与参数一致。
- 原 PDF 页数、尺寸、可读性不受破坏。

### 2.7 PDF 版权保护，可溯源

该功能的核心不是“绝对防复制”，而是“分发后能追踪来源、提高传播成本、为追责提供证据”。需求文档和产品文案必须避免承诺不可破解。

核心能力：

- 为每次下载生成唯一版权指纹 ID。
- 将指纹与用户、任务、文件、时间、IP、下载记录关联。
- 在 PDF 中嵌入可见水印，例如用户名、手机号后四位、订单号、时间、指纹短码。
- 在 PDF 中嵌入隐式信息，例如 PDF 元数据、自定义 XMP 元数据、不可见小字号文本、页面角落微缩码。
- 可选添加二维码水印，二维码内容指向溯源验证地址。
- 可选设置 PDF 打开密码、权限限制，如禁止复制、禁止修改、限制打印。
- 提供溯源查询页面：输入指纹 ID 或上传疑似泄露 PDF，解析并展示来源记录。
- 输出文件默认命名为 `原文件名_protected_指纹ID_时间戳.pdf`。

版权保护策略：

- 基础版：可见水印 + 元数据 + 下载日志。
- 标准版：基础版 + 每次下载唯一水印 + 二维码验证链接。
- 增强版：标准版 + 多点隐式指纹 + PDF 权限加密 + 泄露文件解析。

重要边界：

- PDF 权限限制依赖阅读器遵守，不能作为强 DRM。
- 可见水印可能被裁剪、遮挡或重制。
- 隐式元数据可能被某些工具清除。
- 真正的“可溯源”应采用多层指纹组合，并保存服务端审计日志。

验收标准：

- 每次生成的受保护 PDF 都有唯一追踪 ID。
- 下载记录可在后台查询。
- 从生成文件中至少能解析出一种指纹信息。
- 同一原文件分发给不同用户时，输出文件可区分来源。

## 3. 用户角色

### 3.1 普通用户

- 上传文件。
- 选择工具。
- 配置参数。
- 查看任务状态。
- 下载结果文件。
- 查看自己的历史任务。

### 3.2 管理员

- 查看全部任务。
- 查看系统处理失败日志。
- 配置文件大小、保留周期、并发限制。
- 查看版权溯源记录。
- 禁用异常用户或清理违规文件。

### 3.3 API 调用方，二期

- 通过 API 上传文件和创建任务。
- 通过 Webhook 获取任务完成通知。
- 下载处理结果。

## 4. 非功能需求

### 4.1 性能

- 普通 20 页 PDF 转 PNG 在 150 DPI 下应在 30 秒内完成，具体取决于服务器配置。
- 文件上传大小首期建议限制为 100 MB，可配置。
- 单任务最大页数首期建议限制为 500 页，可配置。
- 同一用户并发任务数默认限制为 2。

### 4.2 稳定性

- 所有耗时任务异步执行。
- 任务状态必须可追踪：等待中、处理中、成功、失败、已过期。
- 任务失败必须保存错误码和用户可理解的错误信息。
- 文件处理过程使用临时目录隔离，任务结束后统一归档或清理。

### 4.3 安全

- 校验文件类型，不只依赖扩展名。
- 限制上传大小、页数、图片像素总量。
- 禁止路径穿越，所有文件使用服务端生成的 UUID 路径。
- 上传文件与输出文件设置自动过期清理。
- 不在日志中记录完整敏感文件内容。
- 私有部署场景可提供本地存储；公网 SaaS 场景建议接对象存储并使用短期签名 URL。

### 4.4 隐私

- 默认文件保留 24 小时，可配置。
- 用户可手动删除任务和文件。
- 版权保护日志保留周期单独配置，例如 180 天或按企业要求。
- 后台访问文件需要管理员权限并记录审计日志。

### 4.5 可扩展性

- 每个 PDF 功能作为独立 service。
- 文件存储、任务队列、转换引擎通过接口抽象。
- 后续可扩展：PDF 合并、压缩、OCR、PDF 转 Excel、页面旋转、提取图片、电子签章。

## 5. 推荐技术栈

### 5.1 后端

- Python 3.11 或 3.12。
- FastAPI：提供 Web API、自动 OpenAPI 文档、文件上传接口。
- Uvicorn/Gunicorn：运行服务。
- Celery + Redis：生产环境异步任务队列。
- FastAPI BackgroundTasks：仅适合开发环境或非常轻量任务，生产环境不建议依赖它处理长任务。
- SQLAlchemy + Alembic：数据库访问和迁移。
- PostgreSQL：生产数据库。
- SQLite：本地开发可选。

### 5.2 PDF 和图片处理库

- PyMuPDF：PDF 渲染 PNG、读取页面尺寸、插入文字/图片水印、基础 PDF 操作。
- pypdf：PDF 拆分、合并、元数据、加密权限、页面叠加。
- pdf2docx：PDF 转 DOCX 基础实现。
- img2pdf：图片转 PDF 的优先实现，支持 JPEG/JPG 无损嵌入。
- Pillow：图片格式处理、EXIF 方向修正、透明背景处理、缩放裁切和非 JPEG 图片预处理。
- qrcode：生成溯源二维码。
- cryptography：配合 PDF 加密或生成签名、哈希。

### 5.3 前端

可选方案：

- 简单版：Jinja2 模板 + HTMX + Alpine.js。
- 工程化版：Vue 3 或 React + TypeScript。

建议首期使用工程化版前端，因为水印参数、预览、任务状态轮询、历史记录都需要较强交互。

推荐页面：

- 首页工具面板。
- PDF 转 Word 页面。
- PDF 转 PNG 页面。
- 图片转 PDF 页面。
- PDF 拆分页面。
- PDF 删除页页面。
- PDF 加水印页面。
- 版权保护页面。
- 任务详情页。
- 历史任务页。
- 管理后台。

### 5.4 存储

本地开发：

- `storage/uploads`
- `storage/outputs`
- `storage/tmp`

生产环境：

- 原始文件和结果文件存对象存储，例如 S3、MinIO、阿里云 OSS。
- 数据库存任务、用户、文件、指纹、日志。
- 临时处理文件放本地磁盘，任务结束后清理。

## 6. 系统架构

推荐采用分层架构：

```text
Browser
  |
  | HTTP / WebSocket / Polling
  v
FastAPI Web API
  |
  | create task
  v
Database <---- Worker 状态回写
  |
  v
Redis Queue
  |
  v
Celery Worker
  |
  | PDF/Image processing
  v
File Storage
```

模块划分：

- `api`：路由、请求校验、鉴权。
- `services`：业务服务，例如转换、拆分、水印、版权保护。
- `workers`：异步任务入口。
- `models`：数据库模型。
- `schemas`：Pydantic 请求和响应模型。
- `storage`：本地或对象存储适配。
- `pdf_engines`：对 PyMuPDF、pypdf、pdf2docx 的封装。
- `security`：鉴权、权限、文件校验。
- `cleanup`：过期文件清理。

## 7. 数据模型设计

### 7.1 users

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 用户 ID |
| email | string | 邮箱 |
| phone | string | 手机号，可选 |
| display_name | string | 昵称 |
| role | enum | user/admin |
| created_at | datetime | 创建时间 |

### 7.2 files

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 文件 ID |
| owner_id | UUID | 用户 ID |
| original_name | string | 原始文件名 |
| mime_type | string | MIME 类型 |
| size_bytes | int | 文件大小 |
| sha256 | string | 文件哈希 |
| storage_key | string | 存储路径 |
| kind | enum | upload/output/temp |
| expires_at | datetime | 过期时间 |
| created_at | datetime | 创建时间 |

### 7.3 tasks

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 任务 ID |
| user_id | UUID | 用户 ID |
| tool_type | enum | pdf_to_word/pdf_to_png/images_to_pdf/split_pdf/remove_pdf_pages/watermark_pdf/protect_pdf |
| status | enum | pending/running/succeeded/failed/expired |
| input_file_ids | json | 输入文件 ID 列表 |
| output_file_ids | json | 输出文件 ID 列表 |
| params | json | 参数快照 |
| progress | int | 0-100 |
| error_code | string | 错误码 |
| error_message | string | 用户可见错误 |
| created_at | datetime | 创建时间 |
| started_at | datetime | 开始时间 |
| finished_at | datetime | 结束时间 |

### 7.4 copyright_fingerprints

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 记录 ID |
| fingerprint_id | string | 对外展示的短码 |
| user_id | UUID | 接收方用户 |
| source_file_id | UUID | 原文件 |
| output_file_id | UUID | 受保护输出文件 |
| task_id | UUID | 任务 |
| visible_text | string | 可见水印内容 |
| metadata_payload | json | 嵌入元数据 |
| verify_url | string | 验证链接 |
| created_at | datetime | 创建时间 |

### 7.5 download_logs

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 日志 ID |
| user_id | UUID | 用户 ID |
| file_id | UUID | 下载文件 |
| task_id | UUID | 任务 |
| ip | string | IP 地址 |
| user_agent | string | 浏览器信息 |
| created_at | datetime | 下载时间 |

## 8. API 设计

### 8.1 文件上传

`POST /api/files`

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

### 8.2 创建任务

`POST /api/tasks`

请求：

```json
{
  "tool_type": "watermark_pdf",
  "input_file_ids": ["uuid"],
  "params": {
    "watermark_type": "text",
    "text": "内部资料",
    "opacity": 0.25,
    "rotation": -30,
    "position": "center",
    "tile": true,
    "page_range": "all"
  }
}
```

响应：

```json
{
  "task_id": "uuid",
  "status": "pending"
}
```

### 8.3 查询任务状态

`GET /api/tasks/{task_id}`

响应：

```json
{
  "task_id": "uuid",
  "status": "succeeded",
  "progress": 100,
  "output_files": [
    {
      "file_id": "uuid",
      "download_url": "/api/files/uuid/download",
      "filename": "contract_watermarked_20260613_153045.pdf"
    }
  ]
}
```

### 8.4 下载文件

`GET /api/files/{file_id}/download`

要求：

- 校验用户是否有权限下载。
- 写入下载日志。
- 私有存储场景返回文件流。
- 对象存储场景返回短期签名地址。

### 8.5 水印预览

`POST /api/tools/watermark/preview`

请求：

```json
{
  "file_id": "uuid",
  "page": 1,
  "params": {
    "watermark_type": "text",
    "text": "内部资料",
    "opacity": 0.25,
    "rotation": -30,
    "position": "center"
  }
}
```

响应：

```json
{
  "preview_image_url": "/api/previews/uuid.png"
}
```

### 8.6 溯源查询

`GET /api/copyright/fingerprints/{fingerprint_id}`

响应：

```json
{
  "fingerprint_id": "AB12-CD34",
  "source_file": "training.pdf",
  "recipient": "user@example.com",
  "created_at": "2026-06-06T10:00:00Z",
  "task_id": "uuid"
}
```

## 9. 前端交互设计

### 9.1 通用流程

1. 用户进入某个工具页面。
2. 拖拽或点击上传文件。
3. 前端显示文件名、大小、页数或图片数量。
4. 用户调整参数。
5. 点击开始处理。
6. 前端创建任务并轮询任务状态。
7. 成功后显示下载按钮。
8. 用户可进入历史任务再次下载或删除。

### 9.2 水印页面布局

建议布局：

- 左侧：文件上传和水印参数。
- 中间：PDF 页面预览。
- 右侧：页面范围、输出设置、开始处理按钮。

参数控件建议：

- 水印类型使用 Tab：文字、图片。
- 透明度使用滑块。
- 旋转角度使用滑块和数字输入。
- 位置使用九宫格按钮。
- 平铺使用开关。
- 页码范围使用输入框，并提供示例提示。

### 9.3 任务状态

状态文案：

- `pending`：排队中。
- `running`：处理中。
- `succeeded`：处理完成。
- `failed`：处理失败。
- `expired`：文件已过期。

失败提示示例：

- 文件受密码保护，请输入密码后重试。
- 文件格式无法识别，请确认上传的是有效 PDF。
- 文件页数过多，请减少页码范围或联系管理员。
- PDF 转 Word 未能识别可编辑文本，可能是扫描版 PDF。

## 10. 参数规范

### 10.1 页码范围

输入格式：

- `all`
- `1`
- `1-5`
- `1,3,5`
- `1-3,8,10-12`

校验规则：

- 页码从 1 开始。
- 不允许 0 或负数。
- 不允许超过总页数。
- 自动去重并按升序处理。

### 10.2 DPI

可选值：

- 72：低清预览。
- 150：默认，适合普通查看。
- 200：较清晰。
- 300：打印质量，处理慢且文件大。

### 10.3 水印透明度

范围：

- 0.05 到 1.0。
- 默认 0.25。

### 10.4 输出文件命名规则

默认规则：

- 所有输出文件名必须在扩展名前追加时间戳，避免同一原文件、同一参数重复处理时文件名冲突。
- 时间戳格式建议使用 `yyyyMMdd_HHmmss`，例如 `20260613_153045`。
- 时间戳应以任务创建时间或任务完成时间为准，同一任务内的多个输出文件必须使用同一个时间戳。
- 文件名格式建议为 `原文件名_功能后缀_时间戳.扩展名`。
- 用户自定义输出文件名时，系统仍必须自动追加时间戳，格式为 `用户自定义名称_时间戳.扩展名`。
- 多文件输出时，ZIP 文件名和 ZIP 内文件名都应包含同一个时间戳。
- 原文件名需要去除扩展名并做安全清洗，避免路径分隔符、控制字符、过长文件名和操作系统不兼容字符。

示例：

- PDF 转 Word：`contract_word_20260613_153045.docx`。
- PDF 转 PNG 单页：`contract_page_001_20260613_153045.png`。
- PDF 转 PNG ZIP：`contract_png_20260613_153045.zip`。
- PDF 拆分页：`contract_page_001_20260613_153045.pdf`。
- PDF 拆分 ZIP：`contract_split_20260613_153045.zip`。
- 删除指定页：`contract_removed_pages_20260613_153045.pdf`。
- 添加水印：`contract_watermarked_20260613_153045.pdf`。
- 版权保护：`contract_protected_AB12-CD34_20260613_153045.pdf`。

### 10.5 文件过期

默认：

- 上传文件：24 小时。
- 输出文件：24 小时。
- 版权指纹记录：180 天，可配置。
- 审计日志：180 天，可配置。

## 11. 实现方案

### 11.1 PDF 转 PNG

流程：

1. 校验 PDF。
2. 如果加密，尝试用用户密码打开。
3. 解析页码范围。
4. 使用 PyMuPDF 打开文档。
5. 对每一页按 DPI 渲染为 pixmap。
6. 保存 PNG 到任务输出目录。
7. 多文件打 ZIP。
8. 写入任务输出文件记录。

### 11.2 图片转 PDF

流程：

1. 校验图片格式和像素大小。
2. 统一 EXIF 方向。
3. 按用户排序读取图片。
4. 判断是否满足 `img2pdf` 无损封装条件，例如输入为 JPEG/JPG、无需重采样、无需裁切、无需透明背景合成。
5. 满足条件时使用 `img2pdf` 直接生成 PDF 页面，保留 JPEG 原始编码数据。
6. 不满足条件时使用 Pillow 完成格式转换、透明背景处理、页面适配、缩放或裁切，再封装为 PDF。
7. 保存为单个 PDF 或多个 PDF。
8. 写入输出记录。

### 11.3 PDF 拆分

流程：

1. 使用 pypdf 读取 PDF。
2. 解析页码范围。
3. 循环每一页，创建新的 writer。
4. 添加当前页。
5. 写出单页 PDF。
6. 打包 ZIP。

### 11.4 PDF 删除页

流程：

1. 使用 pypdf 读取 PDF。
2. 解析用户输入的删除页码或页码范围。
3. 校验页码范围，确保页码存在且删除后至少保留 1 页。
4. 计算需要保留的页码集合。
5. 按原顺序将保留页面写入新的 writer。
6. 写出新的 PDF。
7. 写入输出记录。

### 11.5 PDF 加水印

流程：

1. 读取 PDF。
2. 读取参数并校验。
3. 如果是文字水印，计算文本框和坐标。
4. 如果文字水印为全页平铺或密集形，按页面尺寸、字号、旋转角度和间距生成重复坐标；密集形使用极小字号和低透明度，并限制最小可读放大倍率。
5. 如果是图片水印，处理图片尺寸、透明通道和位置。
6. 如果图片水印为自定义铺满个数，按用户设置的数量在页面中间竖向等距排列；如果为全页铺满，按页面宽高生成网格坐标。
7. 根据页码范围逐页插入水印。
8. 保存新 PDF。
9. 生成预览图或输出文件。

### 11.6 版权保护

流程：

1. 创建任务时生成 `fingerprint_id`。
2. 生成服务端签名 payload，例如：

```json
{
  "fingerprint_id": "AB12-CD34",
  "user_id": "uuid",
  "source_file_sha256": "hash",
  "issued_at": "2026-06-06T10:00:00Z"
}
```

3. 将 payload 写入版权指纹表。
4. 将短码或用户信息写入可见水印。
5. 将完整或签名后的 payload 写入 PDF 元数据。
6. 可选生成二维码并加入页面角落。
7. 可选设置 PDF 权限加密。
8. 输出受保护 PDF。

建议指纹组合：

- 可见文字：`授权给：张三 / ID: AB12-CD34 / 2026-06-06`
- 二维码：`https://example.com/verify/AB12-CD34`
- 元数据：`/Subject`, `/Keywords`, 自定义 XMP。
- 隐式文本：页面边缘小字号、低透明度、白色近似背景文本。

## 12. 错误码设计

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

## 13. 测试计划

### 13.1 单元测试

- 页码范围解析。
- 删除页集合与保留页集合计算。
- 文件类型识别。
- 水印坐标计算。
- 文字水印单个、全页平铺、密集形坐标和透明度参数计算。
- 图片水印单个、自定义铺满个数、全页铺满坐标计算。
- DPI 到矩阵/尺寸换算。
- 指纹 ID 生成和签名校验。

### 13.2 集成测试

- 上传 PDF 后转 PNG。
- 上传多图后合成 PDF。
- 上传 JPEG/JPG 后通过 `img2pdf` 生成 PDF，验证无损嵌入路径不触发重编码。
- 拆分 10 页 PDF，得到 10 个单页 PDF。
- 删除 10 页 PDF 中的第 2、4-6 页，输出 PDF 剩余 6 页且顺序正确。
- 尝试删除全部页面时任务失败并返回明确错误。
- 添加文字水印后输出文件可打开，单个、全页平铺、密集形三种模式均符合预期。
- 添加图片水印后透明度正确，单个、自定义铺满个数、全页铺满三种模式均符合预期。
- 版权保护文件可查询指纹。

### 13.3 样例文件测试集

应准备以下测试文件：

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

## 14. 部署方案

### 14.1 开发环境

```text
FastAPI + SQLite + local storage + single worker
```

适合本地开发、功能验证。

### 14.2 生产环境

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

建议：

- API 服务和 Worker 分开部署。
- Worker 可按 CPU 密集型任务水平扩容。
- 设置任务超时和最大内存。
- 使用容器化部署，限制容器 CPU、内存和临时磁盘。

## 15. 开发里程碑

### M1：基础框架，1 周

- FastAPI 项目结构。
- 文件上传下载。
- 任务模型。
- 本地存储。
- 简单前端页面。

### M2：核心转换，1 到 2 周

- PDF 转 PNG。
- 图片转 PDF。
- PDF 按页拆分。
- PDF 删除指定页。
- 任务状态和 ZIP 输出。

### M3：水印能力，1 到 2 周

- 文字水印。
- 图片水印。
- 参数调节。
- 首页或首屏预览。

### M4：PDF 转 Word，1 周

- 接入 pdf2docx。
- 增加失败提示和扫描版识别提示。
- 输出质量测试。

### M5：版权保护，2 周

- 指纹 ID。
- 可见水印。
- 元数据写入。
- 二维码。
- 下载日志。
- 溯源查询页面。

### M6：管理后台和生产化，1 到 2 周

- 管理员任务列表。
- 配置项。
- 过期清理。
- 权限控制。
- 部署脚本。
- 压力测试。

## 16. 首期 MVP 建议

为了尽快上线验证，建议首期只做以下能力：

- 文件上传。
- PDF 转 PNG。
- 图片转 PDF。
- PDF 按页拆分。
- PDF 删除指定页。
- 文字水印。
- 图片水印。
- 任务状态轮询。
- 输出文件下载。
- 简单历史任务。

PDF 转 Word 和版权保护建议作为 MVP 后半段或标准版能力实现，因为它们的产品预期管理更复杂，尤其是 PDF 转 Word 的还原质量和版权保护的法律表述。

## 17. 关键风险与应对

| 风险 | 说明 | 应对 |
| --- | --- | --- |
| PDF 转 Word 效果不稳定 | PDF 不一定包含语义结构 | 明确“尽力还原”，提供 OCR/商业引擎扩展 |
| 大文件导致服务阻塞 | PDF 渲染和图片处理消耗 CPU/内存 | 异步任务、限流、超时、Worker 隔离 |
| 水印被移除 | 可见水印可被编辑或裁剪 | 多层指纹、服务端日志、二维码、隐式信息 |
| 加密权限不可靠 | 部分阅读器或工具可绕过权限 | 产品文案避免承诺 DRM |
| 用户隐私风险 | 上传文件可能含敏感信息 | 自动过期、权限控制、审计日志、私有部署 |
| 字体问题 | 中文水印可能缺字 | 内置开源中文字体，字体配置化 |

## 18. 参考资料

- FastAPI 文件上传文档：<https://fastapi.tiangolo.com/tutorial/request-files/>
- FastAPI 后台任务文档：<https://fastapi.tiangolo.com/tutorial/background-tasks/>
- PyMuPDF 图片与页面渲染文档：<https://pymupdf.readthedocs.io/en/latest/recipes-images.html>
- PyMuPDF Page API，包含页面渲染和插入图片等能力：<https://pymupdf.readthedocs.io/en/latest/page.html>
- pypdf 合并和页面写入文档：<https://pypdf.readthedocs.io/en/latest/user/merging-pdfs.html>
- pypdf 加密文档：<https://pypdf.readthedocs.io/en/3.15.3/user/encryption-decryption.html>
- pypdf 水印文档：<https://pypdf.readthedocs.io/en/3.17.2/user/add-watermark.html>
- Pillow PDF 保存能力文档：<https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html>
- img2pdf PyPI 项目说明：<https://pypi.org/project/img2pdf/>
- pdf2docx PyPI 项目说明：<https://pypi.org/pypi/pdf2docx/>
