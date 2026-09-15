# enterprise-doc-assistant 完整源码清单

本文件由项目文件机械生成，每节标题均为对应文件名，代码内容未省略。API Key 已脱敏。

## .env

~~~~text
# Zhipu OpenAI-compatible API
ZHIPU_API_KEY=your_zhipu_api_key_here
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=glm-4.7-flash
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=60
LLM_MAX_RETRIES=2

# Local embedding model. The first run downloads the model, later runs are local.
EMBEDDING_MODEL_NAME=BAAI/bge-small-zh
EMBEDDING_DEVICE=cpu
EMBEDDING_LOCAL_ONLY=false
EMBEDDING_CACHE_DIR=./data/models

# Local ChromaDB
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION=enterprise_knowledge

# Retrieval and chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=100
RETRIEVAL_TOP_K=4

# Conversation memory
MAX_HISTORY_MESSAGES=12
MAX_CONTEXT_CHARS=14000

# Runtime directories
UPLOAD_DIR=./data/uploads
REPORT_DIR=./data/reports
EVAL_OUTPUT_DIR=./data/evaluations

# Gradio
GRADIO_SERVER_NAME=127.0.0.1
GRADIO_SERVER_PORT=7860
GRADIO_SHARE=false
~~~~

## requirements.txt

~~~~text
python-dotenv>=1.0.1,<2.0.0
openai>=1.40.0,<2.0.0
chromadb>=1.5.9,<2.0.0
sentence-transformers>=3.0.1,<6.0.0
torch>=2.2.0
PyPDF2>=3.0.1,<4.0.0
python-docx>=1.1.2,<2.0.0
gradio>=4.44.1,<6.0.0
pandas>=2.2.2,<3.0.0
openpyxl>=3.1.5,<4.0.0
numpy>=1.26.0,<3.0.0
pytest>=8.3.0,<9.0.0
~~~~

## .gitignore

~~~~text
# Environment
.env
.venv/
venv/
env/

# Python
__pycache__/
*.py[cod]
*.pyd
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
.coverage
htmlcov/

# Runtime data
data/
outputs/
*.log

# IDE and OS
.idea/
.vscode/
.DS_Store
Thumbs.db

# Model caches that may be placed in the project
models/
~~~~

## README.md

~~~~text
# enterprise-doc-assistant

企业文档智能助手：基于智谱 GLM-4.7-Flash、Function Calling、本地 BGE 向量模型和 ChromaDB 的私有知识库问答系统。项目同时提供 Gradio Web 界面与 CLI 命令行工具，并包含离线检索评测与 Excel 结果导出。

## 核心能力

- 文档解析：支持 PDF、DOCX、Markdown、TXT。
- 文本处理：统一清洗、滑动窗口分块、重叠上下文。
- 本地检索：`BAAI/bge-small-zh` 在本地生成向量，不使用外部嵌入 API。
- 本地持久化：ChromaDB `PersistentClient`，无需启动独立数据库服务。
- Agent 工具：完整实现 `knowledge_retrieve`、`doc_summary`、`export_report` 三个 Function Calling 工具。
- 多轮记忆：按消息数量和上下文字符数自动裁剪早期对话。
- 离线评测：读取 CSV 问答集，计算 `Hit@K`、`MRR`，导出 XLSX 表格。
- 双入口：Gradio Web 界面和 CLI 命令行。

## 技术架构

```text
                    +----------------------+
                    | Gradio Web / CLI     |
                    +----------+-----------+
                               |
                    +----------v-----------+
                    | DocumentAgent        |
                    | GLM-4.7-Flash        |
                    | Function Calling     |
                    +----+------+------+---+
                         |      |      |
          knowledge_retrieve |  doc_summary |  export_report
                         |      |      |
              +----------v--+ +-v------+ +-v----------------+
              | ChromaDB    | | LLM    | | Markdown report  |
              | local store | | summary| | local file       |
              +------+------+ +--------+ +------------------+
                     |
              +------v------------------+
              | BAAI/bge-small-zh       |
              | sentence-transformers   |
              | local inference         |
              +-------------------------+
                     ^
                     |
        +------------+------------+
        | PDF / DOCX / MD / TXT   |
        | parse + clean + chunk   |
        +-------------------------+
```

## 项目结构

```text
enterprise-doc-assistant/
├── .env
├── .gitignore
├── requirements.txt
├── README.md
├── docs/
│   ├── system_design.md
│   └── user_manual.md
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── llm_client.py
│   ├── document_parser.py
│   ├── vector_store.py
│   ├── agent_tools.py
│   ├── conversation_mem.py
│   ├── evaluator.py
│   ├── cli_main.py
│   └── web_gradio.py
├── test_dataset/
│   └── test_qa.csv
└── tests/
    ├── test_core.py
    └── test_web_smoke.py
```

## Windows 本地运行

### 1. 安装 Python

建议使用 64 位 Python 3.10、3.11 或 3.12。安装时勾选 `Add Python to PATH`。

```powershell
python --version
```

### 2. 进入项目目录

```powershell
cd C:\path\to\enterprise-doc-assistant
```

### 3. 创建并激活虚拟环境

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 4. 安装依赖

```powershell
pip install -r requirements.txt
```

首次安装 `torch` 和 `sentence-transformers` 下载量较大，建议预留充足磁盘空间和稳定网络。

### 5. 配置智谱 API

打开项目根目录的 `.env`，将下面一行替换成真实 Key：

```dotenv
ZHIPU_API_KEY=your_real_zhipu_api_key
```

默认使用智谱 OpenAI 兼容接口：

```dotenv
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=glm-4.7-flash
```

### 6. 首次加载本地嵌入模型

默认配置首次运行会自动下载 `BAAI/bge-small-zh` 到 `data/models`：

```dotenv
EMBEDDING_MODEL_NAME=BAAI/bge-small-zh
EMBEDDING_LOCAL_ONLY=false
EMBEDDING_CACHE_DIR=./data/models
```

确认本地缓存已经完整后，可改为离线模式：

```dotenv
EMBEDDING_LOCAL_ONLY=true
```

嵌入推理始终在本机执行，不会调用外部向量 API。

### 7. 建立知识库

```powershell
python -m src.cli_main ingest "D:\company_docs"
```

单文件示例：

```powershell
python -m src.cli_main ingest "D:\company_docs\employee_handbook.pdf"
```

### 8. 启动 CLI

```powershell
python -m src.cli_main chat
```

单次提问：

```powershell
python -m src.cli_main ask "员工入职后多久可以申请年假？"
```

### 9. 启动 Gradio Web

```powershell
python -m src.web_gradio
```

浏览器访问：

```text
http://127.0.0.1:7860
```

也可以直接运行：

```powershell
python src\web_gradio.py
```

## CLI 命令

```powershell
python -m src.cli_main --help
python -m src.cli_main config
python -m src.cli_main ingest <文件或目录> [--reset] [--no-recursive]
python -m src.cli_main documents
python -m src.cli_main ask "问题"
python -m src.cli_main chat
python -m src.cli_main delete <doc_id>
python -m src.cli_main evaluate --dataset test_dataset/test_qa.csv --top-k 5
```

## 离线评测

评测不调用大模型，只调用本地 BGE 检索，因此不会消耗智谱 Token。

```powershell
python -m src.cli_main evaluate --dataset test_dataset/test_qa.csv --top-k 5
```

默认输出：

```text
data/evaluations/retrieval_eval_YYYYMMDD_HHMMSS.xlsx
```

也可以指定输出：

```powershell
python -m src.cli_main evaluate --dataset test_dataset/test_qa.csv --top-k 3 --output data/evaluations/demo.xlsx
```

CSV 格式：

```csv
question,expected_source,expected_answer
员工入职后多久可以申请年假？,employee_handbook.md,员工通过试用期后可按规定申请年假。
```

必要列：

- `question`：测试问题。
- `expected_source`：期望命中的来源文件。多个来源使用 `|` 或 `;` 分隔。
- `expected_answer`：可选，便于人工核对。

## 运行数据目录

项目运行后自动创建：

```text
data/
├── chroma/       # ChromaDB 本地持久化目录
├── evaluations/  # 评测 XLSX
├── models/       # 本地嵌入模型缓存
├── reports/      # Markdown 报告
└── uploads/      # Web 上传文件副本
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

Web 依赖完整时，`test_web_smoke.py` 会执行 Gradio 组件检查；依赖不完整时会自动跳过。

## 常见问题

### 1. `ZHIPU_API_KEY` 未配置

确认 `.env` 位于项目根目录，Key 不包含引号和多余空格。

### 2. 本地嵌入模型加载失败

确认首次运行设置为 `EMBEDDING_LOCAL_ONLY=false`，并检查 `data/models` 是否有写入权限。模型缓存不完整时，改为离线模式会直接失败。

### 3. 扫描版 PDF 无文本

当前解析链使用 PyPDF2 提取文本，扫描图片型 PDF 需要先使用 OCR 工具生成可检索 PDF。

### 4. ChromaDB 维度不匹配

如果切换了嵌入模型，旧集合与新向量维度可能不一致。执行：

```powershell
python -m src.cli_main ingest <文档路径> --reset
```

### 5. Gradio 端口占用

修改 `.env`：

```dotenv
GRADIO_SERVER_PORT=7861
```

### 6. 企业网络无法访问模型仓库

在一台可联网机器预先下载 `BAAI/bge-small-zh`，将模型目录复制到本机，然后把 `EMBEDDING_MODEL_NAME` 改为本地绝对路径。

## 安全与边界

- API Key 只在后端读取，Web 页面仅显示是否配置。
- 上传文件会复制到 `data/uploads`，原始路径不会直接作为报告写入路径。
- 报告名称经过字符过滤，且限制在 `data/reports` 目录。
- 本系统用于企业文档辅助检索，不替代正式审批、法务或安全判断。
- 回答质量取决于知识库文档完整程度、分块参数和检索 Top-K。
~~~~

## docs/system_design.md

~~~~text
# 系统设计说明

## 1. 设计目标

`enterprise-doc-assistant` 面向企业内部文档问答场景，目标是在不引入独立向量数据库服务的前提下，完成文档解析、本地向量化、私有知识检索、多轮问答、文档摘要和报告导出。

核心约束如下：

- 对话模型固定为智谱 `glm-4.7-flash`，通过 OpenAI 兼容接口调用。
- Agent 使用完整 Function Calling，不退化为纯文本拼接。
- 嵌入模型为本地 `BAAI/bge-small-zh`。
- 向量数据库为本地持久化 ChromaDB。
- 支持 PDF、DOCX、MD、TXT。
- 同时提供 Gradio Web 和 CLI。
- 评测阶段可脱离大模型独立运行。

## 2. 总体架构

```text
Interaction Layer
  ├── Gradio Web
  └── CLI

Application Layer
  ├── DocumentAgent
  ├── ConversationMemory
  └── RetrievalEvaluator

Tool Layer
  ├── knowledge_retrieve
  ├── doc_summary
  └── export_report

Data and Model Layer
  ├── DocumentParser
  ├── LocalBGEEmbedder
  ├── ChromaVectorStore
  └── ZhipuLLMClient
```

## 3. 模块职责

### 3.1 `config.py`

集中读取 `.env`，解析类型、校验分块参数、解析相对路径、创建运行目录，并提供脱敏配置摘要。

关键设置：

- 智谱接口：Key、Base URL、模型名、超时、重试次数。
- 嵌入模型：模型名、设备、缓存目录、离线模式。
- ChromaDB：持久化目录、集合名。
- 文本处理：分块大小、重叠字符数、检索 Top-K。
- 会话记忆：消息上限、上下文字符上限。
- Web：监听地址、端口、共享开关。

### 3.2 `document_parser.py`

负责文件识别、解析、清洗和分块。

支持格式：

- PDF：PyPDF2 `PdfReader` 逐页提取文本，并写入页码标记。
- DOCX：python-docx 读取段落、表格、页眉和页脚。
- MD/TXT：按 UTF-8、GB18030、UTF-16 顺序尝试解码。

文本清洗：

- Unicode NFKC 规范化。
- 统一换行符。
- 移除控制字符。
- 压缩连续空白和空行。

分块策略：

- 使用字符滑动窗口。
- 默认 `chunk_size=500`、`chunk_overlap=100`。
- 优先在段落、句号、换行等自然边界截断。
- 每个分块记录 `chunk_index`、`start_char`、`end_char`。

### 3.3 `vector_store.py`

包含两个组件：

1. `LocalBGEEmbedder`
2. `ChromaVectorStore`

`LocalBGEEmbedder` 通过 sentence-transformers 在 CPU 或指定设备运行 `BAAI/bge-small-zh`。模型加载采用懒加载和线程锁，避免 Web 并发下重复加载。首次运行允许下载模型缓存，后续可设置 `EMBEDDING_LOCAL_ONLY=true` 完全离线。

`ChromaVectorStore` 使用 `chromadb.PersistentClient`。每个分块保存：

- 向量。
- 原文。
- `doc_id`。
- 来源路径。
- 文件名。
- 扩展名。
- 分块序号。
- 起止字符位置。
- 文件修改时间。

检索使用 cosine 距离，返回 `score = 1 - distance`，并支持按来源文件名或路径片段过滤。

### 3.4 `llm_client.py`

封装智谱 OpenAI 兼容接口。

主要职责：

- 创建 OpenAI 客户端，Base URL 指向智谱。
- 禁止使用非本项目指定模型配置。
- 统一处理鉴权错误、限流、超时、连接失败和 API 状态错误。
- 将响应标准化为：

```json
{
  "role": "assistant",
  "content": "文本",
  "tool_calls": [],
  "finish_reason": "stop"
}
```

`tool_calls` 保留工具名称、参数 JSON 字符串和调用 ID，供 Agent 执行。

### 3.5 `conversation_mem.py`

保存最近若干轮完整问答，不保存中间工具调用消息。

裁剪策略：

- 消息数量超过 `MAX_HISTORY_MESSAGES` 时删除最旧消息。
- 历史必须以 user 消息开始，避免留下孤立的 assistant 回复。
- 构建上下文时从最新消息向前累计，直到 `MAX_CONTEXT_CHARS`。
- 系统提示和当前用户问题始终保留。

中间工具消息保留在单轮 Agent 工作上下文中，不跨轮持久化，避免 tool 消息与 assistant tool_call 被裁剪后结构不合法。

### 3.6 `agent_tools.py`

包含业务工具、索引服务和 Agent 主循环。

#### `knowledge_retrieve`

输入：

- `query`：检索问题。
- `top_k`：可选，1 至 10。
- `source_filter`：可选来源过滤。

输出：

- 带排名、来源、分块号和相似度的文本片段。
- 结构化来源列表。

#### `doc_summary`

输入：

- `doc_id` 或 `source`。
- `max_chars`。

执行流程：

1. 从 ChromaDB 读取指定文档全部分块。
2. 按分块顺序拼接并限制字符数。
3. 调用 GLM-4.7-Flash 生成结构化摘要。
4. 返回摘要和来源。

#### `export_report`

输入：

- `question`
- `answer`
- `sources`
- `report_name`

输出：

- `data/reports` 下的 Markdown 文件。

安全措施：

- 文件名过滤非法字符。
- 禁止 `..` 和路径穿越。
- 最终路径必须位于配置的报告目录。

#### Agent 循环

```text
用户问题
  -> 组装系统提示 + 会话历史 + 当前问题
  -> 调用 GLM-4.7-Flash，传入三个工具 schema
  -> 模型返回 tool_calls
  -> 本地解析参数
  -> 执行工具
  -> 将 tool 结果追加到工作消息
  -> 再次调用模型
  -> 无 tool_calls 时输出最终回答
  -> 最终回答写入会话记忆
```

单轮最多执行 6 个工具轮次。工具异常会转换为结构化错误结果返回模型，便于模型修正参数或向用户说明。

### 3.7 `evaluator.py`

离线评测只执行本地检索，不调用 GLM。

对每个问题计算：

- 首次正确来源排名。
- `Hit@K`：Top-K 中是否出现期望来源。
- `MRR`：所有有效问题倒数排名的平均值。

输出两个工作表：

- `评测指标`：数据集、K、样本数、命中数、错误数、Hit@K、MRR。
- `问题明细`：逐题检索来源、命中情况和错误。

Excel 使用 Arial 字体、表头填充、冻结首行、自动筛选和自动列宽。

### 3.8 `cli_main.py`

提供子命令：

- `ingest`
- `documents`
- `delete`
- `ask`
- `chat`
- `evaluate`
- `config`

CLI 与 Web 共用 Agent、索引器、向量库和评测器。

### 3.9 `web_gradio.py`

Web 页面分为文档管理和知识问答两个工作区。

文档管理：

- 多文件上传。
- 分块大小和重叠参数。
- 可选清空后重建。
- 索引进度和失败明细。
- 知识库文档表。

知识问答：

- 多轮对话。
- 引用来源显示。
- 报告路径显示。
- 清空会话。
- API 与知识库连接检查。

## 4. 数据流

### 4.1 索引流

```text
文件
  -> 类型检查
  -> 解析
  -> 文本清洗
  -> 滑动窗口分块
  -> 本地 BGE 向量化
  -> ChromaDB upsert
```

### 4.2 问答流

```text
用户问题
  -> 会话记忆裁剪
  -> GLM-4.7-Flash 判断工具
  -> knowledge_retrieve / doc_summary / export_report
  -> Agent 根据工具结果生成回答
  -> 展示引用来源
  -> 写入多轮记忆
```

### 4.3 评测流

```text
CSV
  -> 逐题本地向量检索
  -> 来源匹配
  -> Hit@K 和 MRR
  -> XLSX
```

## 5. 异常处理

- 文件不存在、不可访问、编码错误：`DocumentParseError`。
- PDF 加密或扫描版无文本：返回可理解的解析提示。
- 嵌入模型加载失败：提示缓存目录、网络和离线配置。
- ChromaDB 初始化或写入失败：`VectorStoreError`。
- 智谱 Key 缺失：`LLMConfigurationError`。
- 智谱网络超时：`LLMNetworkError`。
- API 鉴权、限流、状态码错误：`LLMAPIError`。
- 工具参数 JSON 错误：作为 tool 结果返回模型。
- 单个文件索引失败：不影响同批次其他文件。
- Web 请求异常：显示错误消息，不让页面进程退出。

## 6. 并发与持久化

- 嵌入模型加载使用 `RLock`。
- 会话记忆读写使用 `RLock`。
- 报告写入使用 `RLock`。
- ChromaDB 使用本地持久化客户端。
- Gradio 默认并发限制为 4。

## 7. 可扩展点

- 将 PDF 解析替换为 OCR 管线。
- 增加 Excel、PPTX、HTML 解析器。
- 增加关键词检索与向量检索混合排序。
- 增加 Reranker。
- 增加文档权限元数据和用户级过滤。
- 增加 PostgreSQL 或对象存储保存评测历史。
- 将同步 LLM 客户端封装为异步调用。
~~~~

## docs/user_manual.md

~~~~text
# 用户手册

## 1. 环境准备

建议环境：

- Windows 10 或 Windows 11。
- Python 3.10 至 3.12。
- 可用网络，用于安装依赖、首次下载本地嵌入模型和调用智谱 API。
- 至少 4 GB 可用内存，模型和依赖建议预留 5 GB 以上磁盘空间。

## 2. 安装

在 PowerShell 中执行：

```powershell
cd C:\path\to\enterprise-doc-assistant
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. 配置 `.env`

最少需要修改：

```dotenv
ZHIPU_API_KEY=your_real_zhipu_api_key
```

常用参数：

| 参数 | 说明 | 默认值 |
|---|---|---|
| `ZHIPU_MODEL` | 对话模型 | `glm-4.7-flash` |
| `EMBEDDING_MODEL_NAME` | 本地嵌入模型 | `BAAI/bge-small-zh` |
| `EMBEDDING_LOCAL_ONLY` | 是否仅使用本地模型缓存 | `false` |
| `CHROMA_PERSIST_DIR` | ChromaDB 数据目录 | `./data/chroma` |
| `CHUNK_SIZE` | 分块字符数 | `500` |
| `CHUNK_OVERLAP` | 分块重叠字符数 | `100` |
| `RETRIEVAL_TOP_K` | 默认检索条数 | `4` |
| `MAX_HISTORY_MESSAGES` | 记忆最大消息数 | `12` |
| `MAX_CONTEXT_CHARS` | 上下文最大字符数 | `14000` |
| `GRADIO_SERVER_PORT` | Web 端口 | `7860` |

首次运行建议保持：

```dotenv
EMBEDDING_LOCAL_ONLY=false
```

模型缓存完整后改为：

```dotenv
EMBEDDING_LOCAL_ONLY=true
```

## 4. 索引文档

### 4.1 CLI 索引

索引目录：

```powershell
python -m src.cli_main ingest "D:\company_docs"
```

索引单个文件：

```powershell
python -m src.cli_main ingest "D:\company_docs\handbook.pdf"
```

清空知识库后重建：

```powershell
python -m src.cli_main ingest "D:\company_docs" --reset
```

不递归子目录：

```powershell
python -m src.cli_main ingest "D:\company_docs" --no-recursive
```

### 4.2 Web 索引

1. 启动 Web。
2. 在左侧“文档”选择多个 PDF、DOCX、MD 或 TXT。
3. 如需调整，展开“分块参数”。
4. 点击“建立索引”。
5. 查看索引状态和文档列表。

上传文件会复制到 `data/uploads`。原始文件可以继续保留在原位置。

## 5. 启动 Web

```powershell
python -m src.web_gradio
```

打开：

```text
http://127.0.0.1:7860
```

页面功能：

- 文档管理：上传、索引、刷新、清空知识库。
- 知识问答：多轮对话、引用来源、报告路径。
- 状态检查：模型配置、知识库分块数、智谱连接状态。
- 会话控制：清空最近对话记忆。

## 6. CLI 问答

单次问题：

```powershell
python -m src.cli_main ask "报销申请需要提交哪些材料？"
```

显示工具调用：

```powershell
python -m src.cli_main ask "报销申请需要提交哪些材料？" --show-tools
```

多轮对话：

```powershell
python -m src.cli_main chat
```

对话内命令：

- `/clear`：清空会话记忆。
- `/exit`：退出。

## 7. 文档摘要

直接提问即可触发 Agent 的 `doc_summary`：

```text
请总结 employee_handbook.md 的核心内容。
```

如果存在同名文件，建议先用 `knowledge_retrieve` 的返回来源确认 `doc_id`，再明确指定文档。

## 8. 导出报告

示例问题：

```text
请回答“员工入职后多久可以申请年假？”，并把结论、依据和来源导出为 Markdown 报告。
```

Agent 会调用 `export_report`，报告写入：

```text
data/reports/
```

Web 回答底部会显示报告路径。

## 9. 查看和管理知识库

列出文档：

```powershell
python -m src.cli_main documents
```

输出包含文件名、分块数和 `doc_id`。

删除一个文档：

```powershell
python -m src.cli_main delete <doc_id>
```

查看脱敏配置：

```powershell
python -m src.cli_main config
```

## 10. 离线评测

准备 CSV：

```csv
question,expected_source,expected_answer
员工入职后多久可以申请年假？,employee_handbook.md,员工通过试用期后可按规定申请年假。
报销申请需要提交哪些材料？,expense_policy.md,需要提交发票、费用明细和审批记录。
```

运行：

```powershell
python -m src.cli_main evaluate --dataset test_dataset/test_qa.csv --top-k 5
```

指定输出：

```powershell
python -m src.cli_main evaluate --dataset test_dataset/test_qa.csv --top-k 3 --output data/evaluations/custom.xlsx
```

说明：

- 必须先将与 `expected_source` 对应的文档索引到知识库。
- `expected_source` 可写完整路径、文件名或能唯一识别的路径片段。
- 多个可接受来源使用 `|` 或 `;` 分隔。
- 评测不会调用大模型，不会消耗智谱 Token。

## 11. 运行测试

```powershell
python -m unittest discover -s tests -v
```

使用 pytest：

```powershell
pytest -q
```

## 12. 数据目录说明

| 目录 | 用途 |
|---|---|
| `data/chroma` | ChromaDB 本地持久化 |
| `data/models` | 本地嵌入模型缓存 |
| `data/uploads` | Web 上传副本 |
| `data/reports` | Markdown 报告 |
| `data/evaluations` | 评测 XLSX |

删除 `data/chroma` 会丢失已建索引。删除 `data/models` 后，下一次首次运行可能需要重新下载模型。

## 13. 常见错误

### 未配置 API Key

表现：

```text
未配置 ZHIPU_API_KEY
```

处理：检查项目根目录 `.env`，确保 Key 已替换且变量名正确。

### 无法连接智谱 API

检查：

- 网络和代理。
- `ZHIPU_BASE_URL` 是否为 `https://open.bigmodel.cn/api/paas/v4`。
- 企业防火墙是否允许 HTTPS 出站。

### 嵌入模型加载失败

检查：

- `data/models` 是否存在且可写。
- 首次运行是否允许联网。
- `EMBEDDING_LOCAL_ONLY=false` 是否符合当前阶段。
- 模型名是否仍为 `BAAI/bge-small-zh`。

### PDF 提取不到文本

PyPDF2 只能提取文本层。扫描图片 PDF 需先执行 OCR。

### 检索没有结果

检查：

- 是否已经执行索引。
- 运行 `python -m src.cli_main documents`。
- 问题是否过于模糊。
- 尝试调大 `RETRIEVAL_TOP_K` 或减小 `CHUNK_SIZE`。

### 切换嵌入模型后报维度错误

清空旧集合后重建：

```powershell
python -m src.cli_main ingest "D:\company_docs" --reset
```

### Gradio 无法访问

确认进程仍在运行，并检查端口：

```powershell
Get-NetTCPConnection -LocalPort 7860
```

端口占用时修改 `.env` 中的 `GRADIO_SERVER_PORT`。

## 14. 使用建议

- 制度类文档建议按章节保存，避免一个文件包含大量无关内容。
- 长文档可先使用 400 至 700 字符分块，重叠设置为分块大小的 15% 至 25%。
- 重要问题建议明确写出文档名、部门或流程。
- 评测集应覆盖真实业务问题，并保持来源文件可追溯。
- 生产环境建议增加文档权限、审计日志、脱敏和用户身份校验。
~~~~

## src/__init__.py

~~~~text
"""Enterprise document assistant package."""

__version__ = "1.0.0"
~~~~

## src/config.py

~~~~text
"""Centralized runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is a declared dependency
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _resolve_path(value: str | None, default: str) -> Path:
    raw = value.strip() if value and value.strip() else default
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    project_root: Path
    zhipu_api_key: str
    zhipu_base_url: str
    zhipu_model: str
    llm_temperature: float
    llm_timeout: float
    llm_max_retries: int

    embedding_model_name: str
    embedding_device: str
    embedding_local_only: bool
    embedding_cache_dir: Path

    chroma_persist_dir: Path
    chroma_collection: str

    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int

    max_history_messages: int
    max_context_chars: int

    upload_dir: Path
    report_dir: Path
    eval_output_dir: Path

    gradio_server_name: str
    gradio_server_port: int
    gradio_share: bool

    @classmethod
    def from_env(cls) -> "Settings":
        _load_environment()

        chunk_size = max(100, _as_int(os.getenv("CHUNK_SIZE"), 500))
        chunk_overlap = max(0, _as_int(os.getenv("CHUNK_OVERLAP"), 100))
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size // 5)

        return cls(
            project_root=PROJECT_ROOT,
            zhipu_api_key=os.getenv("ZHIPU_API_KEY", "").strip(),
            zhipu_base_url=os.getenv(
                "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
            ).strip(),
            zhipu_model=os.getenv("ZHIPU_MODEL", "glm-4.7-flash").strip(),
            llm_temperature=max(
                0.0, min(1.0, _as_float(os.getenv("LLM_TEMPERATURE"), 0.2))
            ),
            llm_timeout=max(5.0, _as_float(os.getenv("LLM_TIMEOUT"), 60.0)),
            llm_max_retries=max(0, _as_int(os.getenv("LLM_MAX_RETRIES"), 2)),
            embedding_model_name=os.getenv(
                "EMBEDDING_MODEL_NAME", "BAAI/bge-small-zh"
            ).strip(),
            embedding_device=os.getenv("EMBEDDING_DEVICE", "cpu").strip() or "cpu",
            embedding_local_only=_as_bool(
                os.getenv("EMBEDDING_LOCAL_ONLY"), default=False
            ),
            embedding_cache_dir=_resolve_path(
                os.getenv("EMBEDDING_CACHE_DIR"), "./data/models"
            ),
            chroma_persist_dir=_resolve_path(
                os.getenv("CHROMA_PERSIST_DIR"), "./data/chroma"
            ),
            chroma_collection=os.getenv(
                "CHROMA_COLLECTION", "enterprise_knowledge"
            ).strip()
            or "enterprise_knowledge",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            retrieval_top_k=max(1, _as_int(os.getenv("RETRIEVAL_TOP_K"), 4)),
            max_history_messages=max(
                2, _as_int(os.getenv("MAX_HISTORY_MESSAGES"), 12)
            ),
            max_context_chars=max(
                2000, _as_int(os.getenv("MAX_CONTEXT_CHARS"), 14000)
            ),
            upload_dir=_resolve_path(os.getenv("UPLOAD_DIR"), "./data/uploads"),
            report_dir=_resolve_path(os.getenv("REPORT_DIR"), "./data/reports"),
            eval_output_dir=_resolve_path(
                os.getenv("EVAL_OUTPUT_DIR"), "./data/evaluations"
            ),
            gradio_server_name=os.getenv(
                "GRADIO_SERVER_NAME", "127.0.0.1"
            ).strip()
            or "127.0.0.1",
            gradio_server_port=max(
                1, _as_int(os.getenv("GRADIO_SERVER_PORT"), 7860)
            ),
            gradio_share=_as_bool(os.getenv("GRADIO_SHARE"), default=False),
        )

    def ensure_directories(self) -> None:
        """Create all runtime directories."""

        for path in (
            self.embedding_cache_dir,
            self.chroma_persist_dir,
            self.upload_dir,
            self.report_dir,
            self.eval_output_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def safe_summary(self) -> dict[str, Any]:
        """Return non-secret settings for UI status display."""

        key_configured = bool(
            self.zhipu_api_key
            and self.zhipu_api_key != "your_zhipu_api_key_here"
        )
        return {
            "model": self.zhipu_model,
            "api_key_configured": key_configured,
            "embedding_model": self.embedding_model_name,
            "embedding_local_only": self.embedding_local_only,
            "chroma_collection": self.chroma_collection,
            "chroma_dir": str(self.chroma_persist_dir),
            "retrieval_top_k": self.retrieval_top_k,
        }


def get_settings() -> Settings:
    """Create settings and ensure runtime directories exist."""

    settings = Settings.from_env()
    settings.ensure_directories()
    return settings
~~~~

## src/llm_client.py

~~~~text
"""Zhipu GLM-4.7-Flash client using the OpenAI-compatible API."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from .config import Settings


logger = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    """Base error for LLM operations."""


class LLMConfigurationError(LLMClientError):
    """Raised when required LLM configuration is missing."""


class LLMNetworkError(LLMClientError):
    """Raised for network and timeout errors."""


class LLMAPIError(LLMClientError):
    """Raised for API-side errors."""


class ZhipuLLMClient:
    """Small wrapper around the Zhipu OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.zhipu_model
        self._client: Any | None = None

        if self.model.lower() != "glm-4.7-flash":
            raise LLMConfigurationError(
                "本项目固定使用智谱 GLM-4.7-Flash，"
                "请将 ZHIPU_MODEL 设置为 glm-4.7-flash。"
            )

    def _get_client(self) -> Any:
        key = self.settings.zhipu_api_key.strip()
        if not key or key == "your_zhipu_api_key_here":
            raise LLMConfigurationError(
                "未配置 ZHIPU_API_KEY，请先复制 .env 并填写智谱 API Key。"
            )

        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise LLMConfigurationError(
                    "缺少 openai 依赖，请执行 "
                    "pip install -r requirements.txt。"
                ) from exc
            self._client = OpenAI(
                api_key=key,
                base_url=self.settings.zhipu_base_url,
                timeout=self.settings.llm_timeout,
                max_retries=self.settings.llm_max_retries,
            )
        return self._client

    def chat_completion(
        self,
        messages: Iterable[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Call GLM-4.7-Flash and normalize the assistant message."""

        message_list = list(messages)
        if not message_list:
            raise LLMClientError("messages 不能为空。")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": message_list,
            "temperature": (
                self.settings.llm_temperature
                if temperature is None
                else max(0.0, min(1.0, float(temperature)))
            ),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        try:
            from openai import (
                APIConnectionError,
                APIError,
                APIStatusError,
                APITimeoutError,
                AuthenticationError,
                RateLimitError,
            )
        except ImportError as exc:
            raise LLMConfigurationError(
                "缺少 openai 依赖，请执行 pip install -r requirements.txt。"
            ) from exc

        try:
            response = self._get_client().chat.completions.create(**kwargs)
        except AuthenticationError as exc:
            raise LLMAPIError(
                "智谱 API 鉴权失败，请检查 ZHIPU_API_KEY 是否正确。"
            ) from exc
        except RateLimitError as exc:
            raise LLMAPIError(
                "智谱 API 请求频率或额度受限，请稍后重试。"
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise LLMNetworkError(
                "无法连接智谱 API，请检查网络、代理或 base URL。"
            ) from exc
        except APIStatusError as exc:
            detail = getattr(exc, "message", str(exc))
            raise LLMAPIError(
                f"智谱 API 返回异常状态码 {exc.status_code}: {detail}"
            ) from exc
        except APIError as exc:
            raise LLMAPIError(f"智谱 API 调用失败: {exc}") from exc
        except Exception as exc:
            logger.exception("Unexpected LLM error")
            raise LLMClientError(f"大模型调用发生未预期错误: {exc}") from exc

        if not response.choices:
            raise LLMAPIError("智谱 API 未返回任何候选结果。")

        choice = response.choices[0]
        message = choice.message
        tool_calls: list[dict[str, Any]] = []
        for tool_call in getattr(message, "tool_calls", None) or []:
            function = tool_call.function
            tool_calls.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": function.name,
                        "arguments": function.arguments or "{}",
                    },
                }
            )

        return {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason,
        }

    def summarize(
        self,
        content: str,
        *,
        instruction: str = "请用中文生成结构化摘要。",
        max_chars: int = 12000,
    ) -> str:
        """Generate a summary without exposing tools to the model."""

        trimmed = content[: max(500, max_chars)]
        messages = [
            {
                "role": "system",
                "content": (
                    "你是严谨的企业文档摘要助手。只依据用户提供的原文进行概括，"
                    "不得补充原文不存在的事实。输出包含：核心结论、关键事项、"
                    "风险或待办；没有对应内容时明确写“未提及”。"
                ),
            },
            {
                "role": "user",
                "content": f"{instruction}\n\n文档内容如下：\n\n{trimmed}",
            },
        ]
        response = self.chat_completion(messages, temperature=0.1)
        return response.get("content", "").strip() or "文档未生成有效摘要。"

    def health_check(self) -> tuple[bool, str]:
        """Perform a minimal API call for status display."""

        try:
            response = self.chat_completion(
                [
                    {
                        "role": "user",
                        "content": "只回复 OK。",
                    }
                ],
                temperature=0.0,
            )
            return True, response.get("content", "").strip() or "连接成功"
        except LLMClientError as exc:
            return False, str(exc)
~~~~

## src/document_parser.py

~~~~text
"""Document parsing, cleaning, and overlapping chunking."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


class DocumentParseError(RuntimeError):
    """Raised when a document cannot be read or parsed."""


@dataclass(frozen=True)
class Chunk:
    """A text chunk and its source position."""

    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self, document: "ParsedDocument") -> dict[str, Any]:
        metadata = {
            "doc_id": document.doc_id,
            "source": document.path,
            "filename": document.filename,
            "extension": document.extension,
            "title": document.title,
            "chunk_index": self.index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "modified_at": document.modified_at,
            "file_size": document.file_size,
        }
        metadata.update(self.metadata)
        return metadata


@dataclass(frozen=True)
class ParsedDocument:
    """A parsed document and all generated chunks."""

    doc_id: str
    path: str
    filename: str
    extension: str
    title: str
    text: str
    chunks: list[Chunk]
    modified_at: str
    file_size: int


class DocumentParser:
    """Parse supported file types and split them into overlapping chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        if chunk_size < 100:
            raise ValueError("chunk_size 不能小于 100。")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size。")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def is_supported(path: str | Path) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def parse_file(self, path: str | Path) -> ParsedDocument:
        """Parse a file and return cleaned text with overlapping chunks."""

        file_path = Path(path).expanduser()
        try:
            file_path = file_path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise DocumentParseError(f"文件不存在: {file_path}") from exc
        except OSError as exc:
            raise DocumentParseError(f"文件路径不可访问: {file_path}") from exc

        if not file_path.is_file():
            raise DocumentParseError(f"不是有效文件: {file_path}")

        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentParseError(
                f"不支持的文件类型 {extension or '<无扩展名>'}，"
                f"仅支持 {', '.join(sorted(SUPPORTED_EXTENSIONS))}。"
            )

        try:
            stat = file_path.stat()
        except OSError as exc:
            raise DocumentParseError(f"无法读取文件属性: {file_path}") from exc

        if extension == ".pdf":
            raw_text = self._read_pdf(file_path)
        elif extension == ".docx":
            raw_text = self._read_docx(file_path)
        else:
            raw_text = self._read_text(file_path)

        cleaned = clean_text(raw_text)
        if not cleaned:
            raise DocumentParseError(
                f"文件未提取到文本，可能是扫描版 PDF 或空文件: {file_path.name}"
            )

        chunks = chunk_text(
            cleaned,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        doc_id = self._build_doc_id(file_path, stat.st_size, stat.st_mtime)
        modified_at = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat()
        title = file_path.stem

        return ParsedDocument(
            doc_id=doc_id,
            path=str(file_path),
            filename=file_path.name,
            extension=extension,
            title=title,
            text=cleaned,
            chunks=chunks,
            modified_at=modified_at,
            file_size=stat.st_size,
        )

    def parse_paths(self, paths: Iterable[str | Path]) -> list[ParsedDocument]:
        """Parse files while preserving per-file errors for the caller."""

        documents: list[ParsedDocument] = []
        for item in paths:
            try:
                documents.append(self.parse_file(item))
            except DocumentParseError:
                logger.exception("Failed to parse document: %s", item)
        return documents

    @staticmethod
    def collect_files(path: str | Path, *, recursive: bool = True) -> list[Path]:
        """Collect supported files from a file or directory."""

        target = Path(path).expanduser()
        try:
            target = target.resolve(strict=True)
        except FileNotFoundError as exc:
            raise DocumentParseError(f"路径不存在: {target}") from exc
        except OSError as exc:
            raise DocumentParseError(f"路径不可访问: {target}") from exc

        if target.is_file():
            if not DocumentParser.is_supported(target):
                raise DocumentParseError(f"不支持的文件类型: {target}")
            return [target]

        if not target.is_dir():
            raise DocumentParseError(f"既不是文件也不是目录: {target}")

        iterator = target.rglob("*") if recursive else target.glob("*")
        files = sorted(
            item.resolve()
            for item in iterator
            if item.is_file() and DocumentParser.is_supported(item)
        )
        return files

    @staticmethod
    def _read_pdf(path: Path) -> str:
        try:
            from PyPDF2 import PdfReader
        except ImportError as exc:
            raise DocumentParseError(
                "缺少 PyPDF2，请执行 pip install -r requirements.txt。"
            ) from exc

        try:
            with path.open("rb") as file_obj:
                reader = PdfReader(file_obj)
                if reader.is_encrypted:
                    try:
                        if reader.decrypt("") == 0:
                            raise DocumentParseError(
                                f"PDF 已加密，无法读取: {path.name}"
                            )
                    except Exception as exc:
                        raise DocumentParseError(
                            f"PDF 已加密或密码错误: {path.name}"
                        ) from exc

                page_texts: list[str] = []
                for page_number, page in enumerate(reader.pages, start=1):
                    try:
                        text = page.extract_text() or ""
                    except Exception as exc:
                        logger.warning(
                            "PDF 第 %s 页提取失败 (%s): %s",
                            page_number,
                            path.name,
                            exc,
                        )
                        text = ""
                    if text.strip():
                        page_texts.append(f"[第 {page_number} 页]\n{text}")
        except DocumentParseError:
            raise
        except Exception as exc:
            raise DocumentParseError(f"PDF 读取失败 {path.name}: {exc}") from exc

        return "\n\n".join(page_texts)

    @staticmethod
    def _read_docx(path: Path) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise DocumentParseError(
                "缺少 python-docx，请执行 pip install -r requirements.txt。"
            ) from exc

        try:
            document = Document(str(path))
            sections: list[str] = []

            for paragraph in document.paragraphs:
                text = paragraph.text.strip()
                if text:
                    sections.append(text)

            for table in document.tables:
                for row in table.rows:
                    values = [cell.text.strip() for cell in row.cells]
                    row_text = " | ".join(value for value in values if value)
                    if row_text:
                        sections.append(row_text)

            for section in document.sections:
                for paragraph in section.header.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        sections.append(text)
                for paragraph in section.footer.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        sections.append(text)

        except Exception as exc:
            raise DocumentParseError(f"DOCX 读取失败 {path.name}: {exc}") from exc

        return "\n\n".join(sections)

    @staticmethod
    def _read_text(path: Path) -> str:
        encodings = ("utf-8-sig", "utf-8", "gb18030", "utf-16")
        last_error: Exception | None = None

        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
            except OSError as exc:
                raise DocumentParseError(
                    f"文本文件读取失败 {path.name}: {exc}"
                ) from exc

        raise DocumentParseError(
            f"无法识别文本编码 {path.name}: {last_error}"
        )

    @staticmethod
    def _build_doc_id(path: Path, file_size: int, modified_time: float) -> str:
        raw = f"{path}|{file_size}|{modified_time:.6f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters."""

    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = (
        normalized.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u00a0", " ")
    )
    normalized = "".join(
        char
        for char in normalized
        if char in {"\n", "\t"} or unicodedata.category(char)[0] != "C"
    )
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """Split text with a sliding character window and natural boundaries."""

    if chunk_size < 100:
        raise ValueError("chunk_size 不能小于 100。")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size。")

    cleaned = clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [Chunk(text=cleaned, index=0, start_char=0, end_char=len(cleaned))]

    boundaries = ("\n\n", "。", "！", "？", ". ", "! ", "? ", "\n", "；", ";")
    chunks: list[Chunk] = []
    start = 0
    index = 0
    text_length = len(cleaned)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        end = target_end

        if target_end < text_length:
            search_start = start + int(chunk_size * 0.55)
            best_boundary = -1
            for marker in boundaries:
                position = cleaned.rfind(marker, search_start, target_end)
                if position > best_boundary:
                    best_boundary = position + len(marker)
            if best_boundary > start:
                end = best_boundary

        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    text=piece,
                    index=index,
                    start_char=start,
                    end_char=end,
                )
            )
            index += 1

        if end >= text_length:
            break

        next_start = end - chunk_overlap
        if next_start <= start:
            next_start = start + max(1, chunk_size - chunk_overlap)
        start = next_start

    return chunks


def merge_pdf_files(
    input_paths: Iterable[str | Path],
    output_path: str | Path,
) -> Path:
    """Merge PDFs with PyPDF2 and write atomically to the target path."""

    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError as exc:
        raise DocumentParseError(
            "缺少 PyPDF2，请执行 pip install -r requirements.txt。"
        ) from exc

    sources = [Path(path).expanduser().resolve() for path in input_paths]
    if not sources:
        raise DocumentParseError("至少需要一个 PDF 输入文件。")

    target = Path(output_path).expanduser().resolve()
    if target.suffix.lower() != ".pdf":
        target = target.with_suffix(".pdf")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_target = target.with_suffix(target.suffix + ".tmp")

    writer = PdfWriter()
    try:
        for source in sources:
            if not source.is_file():
                raise DocumentParseError(f"PDF 文件不存在: {source}")
            with source.open("rb") as file_obj:
                reader = PdfReader(file_obj)
                if reader.is_encrypted:
                    try:
                        if reader.decrypt("") == 0:
                            raise DocumentParseError(
                                f"PDF 已加密，无法合并: {source.name}"
                            )
                    except Exception as exc:
                        raise DocumentParseError(
                            f"PDF 已加密或密码错误: {source.name}"
                        ) from exc
                for page in reader.pages:
                    writer.add_page(page)

        with temporary_target.open("wb") as output_file:
            writer.write(output_file)
        temporary_target.replace(target)
    except DocumentParseError:
        if temporary_target.exists():
            temporary_target.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary_target.exists():
            temporary_target.unlink(missing_ok=True)
        raise DocumentParseError(f"PDF 合并写回失败: {exc}") from exc
    finally:
        writer.close()

    return target
~~~~

## src/vector_store.py

~~~~text
"""Local BGE embeddings and persistent ChromaDB vector storage."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import Settings


logger = logging.getLogger(__name__)


class VectorStoreError(RuntimeError):
    """Raised for embedding or vector database failures."""


@dataclass(frozen=True)
class SearchHit:
    """One retrieval result."""

    text: str
    metadata: dict[str, Any]
    score: float
    distance: float
    vector_id: str


class LocalBGEEmbedder:
    """Run BAAI/bge-small-zh locally through sentence-transformers."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh",
        *,
        device: str = "cpu",
        cache_dir: str | Path | None = None,
        local_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self.local_only = local_only
        self._model: Any | None = None
        self._lock = threading.RLock()

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise VectorStoreError(
                    "缺少 sentence-transformers，请执行 "
                    "pip install -r requirements.txt。"
                ) from exc

            if self.cache_dir is not None:
                self.cache_dir.mkdir(parents=True, exist_ok=True)

            if self.local_only:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

            kwargs: dict[str, Any] = {"device": self.device}
            if self.cache_dir is not None:
                kwargs["cache_folder"] = str(self.cache_dir)
            kwargs["local_files_only"] = self.local_only

            try:
                self._model = SentenceTransformer(self.model_name, **kwargs)
            except TypeError:
                # Older sentence-transformers versions do not expose
                # local_files_only as a direct constructor argument.
                kwargs.pop("local_files_only", None)
                if self.local_only:
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    os.environ["TRANSFORMERS_OFFLINE"] = "1"
                try:
                    self._model = SentenceTransformer(self.model_name, **kwargs)
                except Exception as exc:
                    raise VectorStoreError(
                        f"本地嵌入模型加载失败: {self.model_name}。"
                        "首次运行需联网下载模型，或设置 "
                        "EMBEDDING_LOCAL_ONLY=false 并检查缓存目录。"
                    ) from exc
            except Exception as exc:
                raise VectorStoreError(
                    f"本地嵌入模型加载失败: {self.model_name}。"
                    "请检查网络、模型缓存目录和 sentence-transformers 版本。"
                ) from exc

            return self._model

    def encode(
        self,
        texts: Iterable[str],
        *,
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Encode texts locally. No external embedding API is used."""

        text_list = [text if isinstance(text, str) else str(text) for text in texts]
        if not text_list:
            return []

        model = self._load_model()
        try:
            vectors = model.encode(
                text_list,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise VectorStoreError(f"文本向量化失败: {exc}") from exc

        try:
            return [vector.tolist() for vector in vectors]
        except AttributeError:
            return [list(vector) for vector in vectors]

    def encode_query(self, query: str) -> list[float]:
        """Encode a retrieval query with the BGE Chinese instruction."""

        text = (query or "").strip()
        if not text:
            raise VectorStoreError("检索问题不能为空。")
        instruction = "为这个句子生成表示以用于检索相关文章："
        return self.encode([instruction + text])[0]


class ChromaVectorStore:
    """Persistent local ChromaDB collection."""

    def __init__(
        self,
        settings: Settings,
        embedder: LocalBGEEmbedder | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or LocalBGEEmbedder(
            model_name=settings.embedding_model_name,
            device=settings.embedding_device,
            cache_dir=settings.embedding_cache_dir,
            local_only=settings.embedding_local_only,
        )
        self.persist_dir = settings.chroma_persist_dir
        self.collection_name = settings.chroma_collection
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client: Any | None = None
        self._collection: Any | None = None
        self._lock = threading.RLock()

    def _get_collection(self) -> Any:
        if self._collection is not None:
            return self._collection

        with self._lock:
            if self._collection is not None:
                return self._collection

            try:
                import chromadb
            except ImportError as exc:
                raise VectorStoreError(
                    "缺少 chromadb，请执行 pip install -r requirements.txt。"
                ) from exc

            try:
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir)
                )
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as exc:
                raise VectorStoreError(
                    f"ChromaDB 初始化失败: {self.persist_dir}: {exc}"
                ) from exc

            return self._collection

    def add_chunks(
        self,
        *,
        doc_id: str,
        source: str,
        chunks: Iterable[Any],
        document: Any,
    ) -> int:
        """Embed and upsert chunks after replacing the same document."""

        chunk_list = list(chunks)
        if not chunk_list:
            return 0

        text_list = [chunk.text for chunk in chunk_list]
        vectors = self.embedder.encode(text_list)
        ids = [f"{doc_id}:{chunk.index}" for chunk in chunk_list]
        metadatas = [
            self._sanitize_metadata(chunk.to_metadata(document))
            for chunk in chunk_list
        ]

        try:
            collection = self._get_collection()
            collection.delete(where={"doc_id": doc_id})
            collection.upsert(
                ids=ids,
                documents=text_list,
                metadatas=metadatas,
                embeddings=vectors,
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                f"写入 ChromaDB 失败 ({source}): {exc}"
            ) from exc

        return len(chunk_list)

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        source_filter: str | None = None,
    ) -> list[SearchHit]:
        """Retrieve nearest chunks from the local collection."""

        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        requested_k = max(1, int(top_k or self.settings.retrieval_top_k))
        try:
            collection = self._get_collection()
            total = collection.count()
            if total == 0:
                return []

            query_vector = self.embedder.encode_query(normalized_query)
            # Fetch extra candidates when a source filter is requested.
            n_results = min(
                total,
                requested_k * 3 if source_filter else requested_k,
            )
            result = collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"ChromaDB 检索失败: {exc}") from exc

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: list[SearchHit] = []
        filter_value = (source_filter or "").strip().lower()
        for vector_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            metadata_dict = dict(metadata or {})
            if filter_value:
                source = str(metadata_dict.get("source", "")).lower()
                filename = str(metadata_dict.get("filename", "")).lower()
                if filter_value not in source and filter_value not in filename:
                    continue

            distance_value = float(distance)
            hits.append(
                SearchHit(
                    vector_id=vector_id,
                    text=text or "",
                    metadata=metadata_dict,
                    distance=distance_value,
                    score=1.0 - distance_value,
                )
            )
            if len(hits) >= requested_k:
                break

        return hits

    def get_document_chunks(
        self,
        doc_id: str,
        *,
        max_chunks: int = 200,
    ) -> list[SearchHit]:
        """Return all known chunks for one document in source order."""

        if not doc_id:
            return []

        try:
            collection = self._get_collection()
            result = collection.get(
                where={"doc_id": doc_id},
                limit=max(1, max_chunks),
                include=["documents", "metadatas"],
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"读取文档分块失败: {exc}") from exc

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        hits = [
            SearchHit(
                vector_id=vector_id,
                text=text or "",
                metadata=dict(metadata or {}),
                score=0.0,
                distance=0.0,
            )
            for vector_id, text, metadata in zip(ids, documents, metadatas)
        ]
        hits.sort(
            key=lambda item: int(item.metadata.get("chunk_index", 0))
        )
        return hits

    def find_document_id(self, source: str) -> str | None:
        """Find one document id by full source path or filename."""

        query = (source or "").strip().lower()
        if not query:
            return None

        for document in self.list_documents():
            full_source = str(document.get("source", "")).lower()
            filename = str(document.get("filename", "")).lower()
            if query == full_source or query == filename:
                return str(document.get("doc_id", "")) or None
        for document in self.list_documents():
            full_source = str(document.get("source", "")).lower()
            filename = str(document.get("filename", "")).lower()
            if query in full_source or query in filename:
                return str(document.get("doc_id", "")) or None
        return None

    def list_documents(self) -> list[dict[str, Any]]:
        """Aggregate chunk metadata into a document list."""

        try:
            collection = self._get_collection()
            if collection.count() == 0:
                return []
            result = collection.get(include=["metadatas"])
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"读取文档列表失败: {exc}") from exc

        documents: dict[str, dict[str, Any]] = {}
        for metadata in result.get("metadatas") or []:
            item = dict(metadata or {})
            doc_id = str(item.get("doc_id", ""))
            if not doc_id:
                continue
            if doc_id not in documents:
                documents[doc_id] = {
                    "doc_id": doc_id,
                    "source": str(item.get("source", "")),
                    "filename": str(item.get("filename", "")),
                    "title": str(item.get("title", "")),
                    "extension": str(item.get("extension", "")),
                    "chunks": 0,
                }
            documents[doc_id]["chunks"] += 1

        return sorted(
            documents.values(),
            key=lambda item: str(item.get("filename", "")).lower(),
        )

    def delete_document(self, doc_id: str) -> None:
        if not doc_id:
            return
        try:
            self._get_collection().delete(where={"doc_id": doc_id})
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"删除文档失败 {doc_id}: {exc}") from exc

    def reset(self) -> None:
        """Delete and recreate the configured collection."""

        with self._lock:
            try:
                import chromadb

                if self._client is None:
                    self._client = chromadb.PersistentClient(
                        path=str(self.persist_dir)
                    )
                try:
                    self._client.delete_collection(self.collection_name)
                except Exception:
                    logger.info(
                        "Collection %s did not exist before reset.",
                        self.collection_name,
                    )
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except VectorStoreError:
                raise
            except Exception as exc:
                raise VectorStoreError(f"清空知识库失败: {exc}") from exc

    def count(self) -> int:
        try:
            return int(self._get_collection().count())
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"读取知识库数量失败: {exc}") from exc

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[str(key)] = value
            else:
                clean[str(key)] = str(value)
        return clean
~~~~

## src/agent_tools.py

~~~~text
"""Function-calling tools, document indexing, and the enterprise agent."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import Settings
from .conversation_mem import ConversationMemory
from .document_parser import (
    DocumentParseError,
    DocumentParser,
    ParsedDocument,
)
from .llm_client import LLMClientError, ZhipuLLMClient
from .vector_store import ChromaVectorStore, SearchHit, VectorStoreError


logger = logging.getLogger(__name__)


class AgentToolError(RuntimeError):
    """Raised when a tool cannot complete its operation."""


@dataclass(frozen=True)
class ToolResult:
    """Normalized output returned by a function-calling tool."""

    content: str
    sources: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexingResult:
    """Result of indexing one source document."""

    source: str
    success: bool
    chunks: int = 0
    doc_id: str = ""
    message: str = ""


@dataclass(frozen=True)
class AgentResponse:
    """Final answer and execution trace."""

    answer: str
    sources: list[dict[str, str]]
    tool_calls: list[dict[str, Any]]
    report_path: str | None = None


class DocumentIndexer:
    """Parse documents and persist chunks in the local vector store."""

    def __init__(
        self,
        settings: Settings,
        vector_store: ChromaVectorStore,
        parser: DocumentParser | None = None,
    ) -> None:
        self.settings = settings
        self.vector_store = vector_store
        self.parser = parser or DocumentParser(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    def index_paths(self, paths: Iterable[str | Path]) -> list[IndexingResult]:
        """Index explicit files. Each file fails independently."""

        results: list[IndexingResult] = []
        for item in paths:
            path = Path(item).expanduser()
            if not path.exists():
                results.append(
                    IndexingResult(
                        source=str(path),
                        success=False,
                        message="文件不存在。",
                    )
                )
                continue
            try:
                document = self.parser.parse_file(path)
                results.append(self._index_document(document))
            except (DocumentParseError, VectorStoreError, OSError) as exc:
                logger.warning("Indexing failed for %s: %s", path, exc)
                results.append(
                    IndexingResult(
                        source=str(path),
                        success=False,
                        message=str(exc),
                    )
                )
        return results

    def index_directory(
        self,
        directory: str | Path,
        *,
        recursive: bool = True,
    ) -> list[IndexingResult]:
        """Collect supported files from a directory and index them."""

        files = self.parser.collect_files(directory, recursive=recursive)
        return self.index_paths(files)

    def _index_document(self, document: ParsedDocument) -> IndexingResult:
        if not document.chunks:
            return IndexingResult(
                source=document.path,
                success=False,
                doc_id=document.doc_id,
                message="未生成有效文本分块。",
            )

        old_doc_id = self.vector_store.find_document_id(document.path)
        if old_doc_id and old_doc_id != document.doc_id:
            self.vector_store.delete_document(old_doc_id)

        chunk_count = self.vector_store.add_chunks(
            doc_id=document.doc_id,
            source=document.path,
            chunks=document.chunks,
            document=document,
        )
        return IndexingResult(
            source=document.path,
            success=True,
            chunks=chunk_count,
            doc_id=document.doc_id,
            message="索引完成。",
        )


class KnowledgeRetrieveTool:
    """Retrieve private knowledge from ChromaDB."""

    definition: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "knowledge_retrieve",
            "description": (
                "检索企业私有知识库。回答制度、流程、产品、项目或文档事实问题时，"
                "必须优先调用本工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "用于语义检索的问题或关键词，应保留关键实体。",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回的候选片段数量，默认使用系统配置。",
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "source_filter": {
                        "type": "string",
                        "description": "可选，按文件名或路径片段过滤来源。",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        default_top_k: int = 4,
    ) -> None:
        self.vector_store = vector_store
        self.default_top_k = default_top_k

    def run(
        self,
        *,
        query: str,
        top_k: int | None = None,
        source_filter: str | None = None,
    ) -> ToolResult:
        normalized_query = (query or "").strip()
        if not normalized_query:
            raise AgentToolError("knowledge_retrieve 缺少有效 query。")

        requested_k = int(top_k or self.default_top_k)
        requested_k = max(1, min(10, requested_k))
        try:
            hits = self.vector_store.search(
                normalized_query,
                top_k=requested_k,
                source_filter=source_filter,
            )
        except VectorStoreError as exc:
            raise AgentToolError(str(exc)) from exc

        if not hits:
            return ToolResult(
                content=(
                    "知识库未检索到相关内容。请提示用户先上传并索引文档，"
                    "或将问题改写为更具体的关键词。"
                ),
                metadata={"query": normalized_query, "hit_count": 0},
            )

        context_parts: list[str] = []
        sources: list[dict[str, str]] = []
        context_items: list[dict[str, Any]] = []

        for rank, hit in enumerate(hits, start=1):
            source = str(hit.metadata.get("source", "未知来源"))
            filename = str(hit.metadata.get("filename", Path(source).name))
            chunk_index = str(hit.metadata.get("chunk_index", ""))
            score = round(hit.score, 4)
            context_parts.append(
                f"[片段 {rank} | 来源: {filename} | 分块: {chunk_index} | "
                f"相似度: {score}]\n{hit.text}"
            )
            sources.append(
                {
                    "doc_id": str(hit.metadata.get("doc_id", "")),
                    "source": source,
                    "filename": filename,
                }
            )
            context_items.append(
                {
                    "rank": rank,
                    "text": hit.text,
                    "score": score,
                    "metadata": hit.metadata,
                }
            )

        return ToolResult(
            content="\n\n".join(context_parts),
            sources=sources,
            metadata={
                "query": normalized_query,
                "hit_count": len(hits),
                "context_items": context_items,
            },
        )


class DocSummaryTool:
    """Summarize one indexed document through GLM-4.7-Flash."""

    definition: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "doc_summary",
            "description": (
                "对知识库中某一篇已索引文档生成结构化摘要。"
                "用户要求总结整篇文档时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "文档 ID，可从 knowledge_retrieve 的来源中获取。",
                    },
                    "source": {
                        "type": "string",
                        "description": "也可传文件名或路径片段，由工具查找文档。",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "最多送入摘要模型的原文字符数。",
                        "minimum": 1000,
                        "maximum": 30000,
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        llm_client: ZhipuLLMClient,
    ) -> None:
        self.vector_store = vector_store
        self.llm_client = llm_client

    def run(
        self,
        *,
        doc_id: str | None = None,
        source: str | None = None,
        max_chars: int = 12000,
    ) -> ToolResult:
        resolved_doc_id = (doc_id or "").strip()
        if not resolved_doc_id and source:
            resolved_doc_id = self.vector_store.find_document_id(source) or ""
        if not resolved_doc_id:
            raise AgentToolError(
                "未找到目标文档。请先调用 knowledge_retrieve，"
                "或传入正确的 doc_id/source。"
            )

        try:
            chunks = self.vector_store.get_document_chunks(resolved_doc_id)
        except VectorStoreError as exc:
            raise AgentToolError(str(exc)) from exc
        if not chunks:
            raise AgentToolError(f"文档 {resolved_doc_id} 没有可摘要内容。")

        limit = max(1000, min(30000, int(max_chars or 12000)))
        content_parts: list[str] = []
        used_chars = 0
        source_label = ""
        filename = ""

        for hit in chunks:
            if used_chars >= limit:
                break
            remaining = limit - used_chars
            text = hit.text[:remaining]
            content_parts.append(text)
            used_chars += len(text)
            source_label = source_label or str(hit.metadata.get("source", ""))
            filename = filename or str(hit.metadata.get("filename", ""))

        try:
            summary = self.llm_client.summarize(
                "\n\n".join(content_parts),
                instruction=(
                    f"请总结文档《{filename or resolved_doc_id}》。"
                    "摘要要覆盖文档目的、核心内容、关键结论和待办风险。"
                ),
                max_chars=limit,
            )
        except LLMClientError as exc:
            raise AgentToolError(f"文档摘要模型调用失败: {exc}") from exc

        source_item = {
            "doc_id": resolved_doc_id,
            "source": source_label,
            "filename": filename or Path(source_label).name,
        }
        return ToolResult(
            content=summary,
            sources=[source_item],
            metadata={
                "doc_id": resolved_doc_id,
                "characters_used": used_chars,
                "chunk_count": len(chunks),
            },
        )


class ExportReportTool:
    """Write a Q&A result to a local Markdown report."""

    definition: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "export_report",
            "description": (
                "将当前问答结论、依据和来源导出为本地 Markdown 报告。"
                "当用户明确要求保存、导出或生成报告时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户原始问题。",
                    },
                    "answer": {
                        "type": "string",
                        "description": "准备写入报告的完整回答。",
                    },
                    "sources": {
                        "type": "array",
                        "description": "回答所依据的来源名称或路径。",
                        "items": {"type": "string"},
                    },
                    "report_name": {
                        "type": "string",
                        "description": "报告文件名前缀，可选。",
                    },
                },
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, report_dir: str | Path) -> None:
        self.report_dir = Path(report_dir).expanduser().resolve()
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def run(
        self,
        *,
        question: str,
        answer: str,
        sources: list[str] | str | None = None,
        report_name: str | None = None,
    ) -> ToolResult:
        question_text = (question or "").strip()
        answer_text = (answer or "").strip()
        if not question_text or not answer_text:
            raise AgentToolError("export_report 需要 question 和 answer。")

        source_list = self._normalize_sources(sources)
        stem = self._safe_stem(report_name or "enterprise_qa_report")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{stem}_{timestamp}_{uuid.uuid4().hex[:6]}.md"
        report_path = (self.report_dir / filename).resolve()

        if self.report_dir not in report_path.parents:
            raise AgentToolError("报告路径越界，已拒绝写入。")

        source_lines = (
            "\n".join(f"- {item}" for item in source_list)
            if source_list
            else "- 未提供来源"
        )
        content = (
            "# 企业文档智能助手问答报告\n\n"
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 报告主题：{question_text}\n\n"
            "## 问题\n\n"
            f"{question_text}\n\n"
            "## 回答\n\n"
            f"{answer_text}\n\n"
            "## 依据来源\n\n"
            f"{source_lines}\n"
        )

        try:
            with self._lock:
                report_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise AgentToolError(f"报告写入失败: {exc}") from exc

        return ToolResult(
            content=f"报告已导出到: {report_path}",
            metadata={"report_path": str(report_path)},
        )

    @staticmethod
    def _normalize_sources(sources: list[str] | str | None) -> list[str]:
        if sources is None:
            return []
        if isinstance(sources, str):
            return [
                item.strip()
                for item in re.split(r"[\n,;]+", sources)
                if item.strip()
            ]
        return [str(item).strip() for item in sources if str(item).strip()]

    @staticmethod
    def _safe_stem(value: str) -> str:
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" ._")
        stem = stem[:60]
        return stem or "enterprise_qa_report"


class DocumentAgent:
    """GLM-4.7-Flash agent with complete function-calling execution."""

    SYSTEM_PROMPT = """你是 enterprise-doc-assistant 企业文档智能助手。
你的职责是基于企业私有知识库进行准确问答、文档摘要和报告导出。

工具使用规则：
1. 涉及企业制度、流程、产品、项目、文档事实时，必须先调用 knowledge_retrieve。
2. 用户要求总结整篇文档时，优先调用 doc_summary。
3. 用户明确要求保存、导出或生成 Markdown 报告时，调用 export_report。
4. 每次工具调用后，根据工具结果继续推理；必要时可连续调用多个工具。
5. 最终回答只依据工具返回内容和用户明确提供的信息，不得编造来源。
6. 检索为空时要明确说明知识库未检索到依据，并给出可执行的补充建议。
7. 回答使用清晰中文，先给结论，再给依据和必要注意事项，并列出引用文件名。
"""

    def __init__(
        self,
        settings: Settings,
        *,
        llm_client: ZhipuLLMClient | None = None,
        vector_store: ChromaVectorStore | None = None,
        memory: ConversationMemory | None = None,
        max_tool_rounds: int = 6,
    ) -> None:
        self.settings = settings
        self.llm_client = llm_client or ZhipuLLMClient(settings)
        self.vector_store = vector_store or ChromaVectorStore(settings)
        self.memory = memory or ConversationMemory(
            max_messages=settings.max_history_messages,
            max_context_chars=settings.max_context_chars,
        )
        self.max_tool_rounds = max(1, max_tool_rounds)

        self.knowledge_tool = KnowledgeRetrieveTool(
            self.vector_store,
            default_top_k=settings.retrieval_top_k,
        )
        self.summary_tool = DocSummaryTool(
            self.vector_store,
            self.llm_client,
        )
        self.export_tool = ExportReportTool(settings.report_dir)
        self.tool_definitions = [
            self.knowledge_tool.definition,
            self.summary_tool.definition,
            self.export_tool.definition,
        ]

    def run(self, question: str) -> AgentResponse:
        """Run one user turn through the tool-calling loop."""

        question_text = (question or "").strip()
        if not question_text:
            raise ValueError("问题不能为空。")

        messages = self.memory.context_messages(
            self.SYSTEM_PROMPT,
            current_user_message=question_text,
        )
        source_items: list[dict[str, str]] = []
        tool_records: list[dict[str, Any]] = []
        assistant_content = ""

        for round_index in range(self.max_tool_rounds):
            response = self.llm_client.chat_completion(
                messages,
                tools=self.tool_definitions,
                tool_choice="auto",
            )
            tool_calls = response.get("tool_calls") or []
            assistant_content = str(response.get("content") or "").strip()

            if not tool_calls:
                break

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_content or None,
                "tool_calls": tool_calls,
            }
            messages.append(assistant_message)

            for tool_call in tool_calls:
                function = tool_call.get("function") or {}
                tool_name = str(function.get("name", ""))
                tool_call_id = str(tool_call.get("id") or f"call_{uuid.uuid4().hex}")
                arguments, parse_error = self._parse_arguments(
                    function.get("arguments")
                )

                if parse_error:
                    result_content = json.dumps(
                        {"ok": False, "error": parse_error},
                        ensure_ascii=False,
                    )
                    tool_record = {
                        "name": tool_name,
                        "arguments": {},
                        "status": "error",
                        "error": parse_error,
                    }
                else:
                    (
                        result_content,
                        result_sources,
                        metadata,
                        tool_error,
                    ) = self._execute_tool(tool_name, arguments)
                    self._merge_sources(source_items, result_sources)
                    tool_record = {
                        "name": tool_name,
                        "arguments": arguments,
                        "status": "error" if tool_error else "success",
                        "metadata": metadata,
                    }
                    if tool_error:
                        tool_record["error"] = tool_error

                tool_records.append(tool_record)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_content,
                    }
                )

            if round_index == self.max_tool_rounds - 1:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "工具调用轮次已达上限。请停止调用工具，"
                            "现在基于已有工具结果给出最终中文回答。"
                        ),
                    }
                )
                final_response = self.llm_client.chat_completion(
                    messages,
                    temperature=0.1,
                )
                assistant_content = str(
                    final_response.get("content") or ""
                ).strip()

        if not assistant_content:
            assistant_content = (
                "当前未能生成有效回答。请检查 GLM-4.7-Flash 配置和知识库状态后重试。"
            )

        report_path: str | None = None
        for record in tool_records:
            metadata = record.get("metadata") or {}
            if record.get("name") == "export_report" and metadata.get("report_path"):
                report_path = str(metadata["report_path"])

        self.memory.add_exchange(question_text, assistant_content)
        return AgentResponse(
            answer=assistant_content,
            sources=source_items,
            tool_calls=tool_records,
            report_path=report_path,
        )

    def _execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], dict[str, Any], str | None]:
        try:
            if name == "knowledge_retrieve":
                result = self.knowledge_tool.run(
                    query=str(arguments.get("query", "")),
                    top_k=arguments.get("top_k"),
                    source_filter=arguments.get("source_filter"),
                )
            elif name == "doc_summary":
                result = self.summary_tool.run(
                    doc_id=arguments.get("doc_id"),
                    source=arguments.get("source"),
                    max_chars=int(arguments.get("max_chars") or 12000),
                )
            elif name == "export_report":
                result = self.export_tool.run(
                    question=str(arguments.get("question", "")),
                    answer=str(arguments.get("answer", "")),
                    sources=arguments.get("sources"),
                    report_name=arguments.get("report_name"),
                )
            else:
                raise AgentToolError(f"未知工具: {name}")
        except (AgentToolError, ValueError, TypeError) as exc:
            logger.warning("Tool %s failed: %s", name, exc)
            payload = {
                "ok": False,
                "error": str(exc),
                "instruction": "请修正参数；无法修正时向用户说明原因。",
            }
            return (
                json.dumps(payload, ensure_ascii=False),
                [],
                {},
                str(exc),
            )
        except Exception as exc:
            logger.exception("Unexpected tool error: %s", name)
            message = f"工具 {name} 发生未预期错误: {exc}"
            return (
                json.dumps({"ok": False, "error": message}, ensure_ascii=False),
                [],
                {},
                message,
            )

        payload = {
            "ok": True,
            "result": result.content,
            "metadata": result.metadata,
        }
        return (
            json.dumps(payload, ensure_ascii=False, default=str),
            result.sources,
            result.metadata,
            None,
        )

    @staticmethod
    def _parse_arguments(raw: Any) -> tuple[dict[str, Any], str | None]:
        if isinstance(raw, dict):
            return raw, None
        if raw is None or raw == "":
            return {}, None
        try:
            parsed = json.loads(str(raw))
        except json.JSONDecodeError as exc:
            return {}, f"工具参数不是合法 JSON: {exc}"
        if not isinstance(parsed, dict):
            return {}, "工具参数必须是 JSON 对象。"
        return parsed, None

    @staticmethod
    def _merge_sources(
        target: list[dict[str, str]],
        incoming: list[dict[str, str]],
    ) -> None:
        seen = {
            (item.get("doc_id", ""), item.get("source", ""))
            for item in target
        }
        for item in incoming:
            key = (item.get("doc_id", ""), item.get("source", ""))
            if key not in seen:
                target.append(item)
                seen.add(key)

    def clear_memory(self) -> None:
        self.memory.clear()
~~~~

## src/conversation_mem.py

~~~~text
"""Bounded multi-turn conversation memory."""

from __future__ import annotations

import threading
from copy import deepcopy
from typing import Any


class ConversationMemory:
    """Keep recent user/assistant messages under a fixed message budget."""

    def __init__(
        self,
        max_messages: int = 12,
        max_context_chars: int = 14000,
    ) -> None:
        if max_messages < 2:
            raise ValueError("max_messages 不能小于 2。")
        if max_context_chars < 1000:
            raise ValueError("max_context_chars 不能小于 1000。")

        self.max_messages = max_messages
        self.max_context_chars = max_context_chars
        self._messages: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def add_exchange(self, user_message: str, assistant_message: str) -> None:
        """Append one completed user/assistant turn and trim old turns."""

        user_content = (user_message or "").strip()
        assistant_content = (assistant_message or "").strip()
        if not user_content:
            return
        if not assistant_content:
            assistant_content = "本轮未生成有效回答。"

        with self._lock:
            self._messages.extend(
                [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ]
            )
            self._trim()

    def add_message(self, role: str, content: str) -> None:
        """Append a single role message. Primarily useful for tests."""

        if role not in {"user", "assistant"}:
            raise ValueError("ConversationMemory 仅保存 user 或 assistant 消息。")
        text = (content or "").strip()
        if not text:
            return
        with self._lock:
            self._messages.append({"role": role, "content": text})
            self._trim()

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._messages)

    def context_messages(
        self,
        system_prompt: str,
        current_user_message: str | None = None,
    ) -> list[dict[str, str]]:
        """Build a size-bounded OpenAI-style context."""

        with self._lock:
            history = deepcopy(self._messages)

        selected: list[dict[str, str]] = []
        remaining = max(0, self.max_context_chars - len(system_prompt))
        current_content = (current_user_message or "").strip()

        if current_content:
            current_budget = min(remaining, max(500, remaining // 2))
            current_content = (
                current_content[:current_budget] if current_budget > 0 else ""
            )
            remaining -= len(current_content)

        for message in reversed(history):
            content = str(message.get("content", ""))
            if remaining <= 0:
                break
            if len(content) > remaining:
                content = content[-remaining:]
            selected.append(
                {
                    "role": str(message.get("role", "user")),
                    "content": content,
                }
            )
            remaining -= len(content)

        selected.reverse()
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(selected)

        if current_content:
            messages.append({"role": "user", "content": current_content})
        return messages

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._messages)

    def _trim(self) -> None:
        while len(self._messages) > self.max_messages:
            self._messages.pop(0)

        # A history should start with a user message, not an orphan assistant reply.
        while self._messages and self._messages[0]["role"] != "user":
            self._messages.pop(0)
~~~~

## src/evaluator.py

~~~~text
"""Offline retrieval evaluator for CSV Q&A datasets."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import Settings
from .vector_store import ChromaVectorStore, VectorStoreError


logger = logging.getLogger(__name__)


class EvaluationError(RuntimeError):
    """Raised when an evaluation dataset or run is invalid."""


@dataclass
class EvaluationResult:
    """Summary and per-question evaluation tables."""

    summary: pd.DataFrame
    details: pd.DataFrame
    output_path: str | None = None

    def summary_text(self) -> str:
        if self.summary.empty:
            return "没有可展示的评测结果。"
        row = self.summary.iloc[0]
        return (
            f"样本数: {int(row['样本数'])} | "
            f"命中数: {int(row['命中数'])} | "
            f"Hit@{int(row['K'])}: {float(row['Hit@K']):.4f} | "
            f"MRR: {float(row['MRR']):.4f}"
        )


class RetrievalEvaluator:
    """Compute Top-K retrieval hit rate without invoking an LLM."""

    REQUIRED_COLUMNS = {"question", "expected_source"}

    def __init__(
        self,
        settings: Settings,
        vector_store: ChromaVectorStore,
    ) -> None:
        self.settings = settings
        self.vector_store = vector_store

    def evaluate(
        self,
        dataset_path: str | Path,
        *,
        top_k: int = 5,
        output_path: str | Path | None = None,
    ) -> EvaluationResult:
        """Read CSV, run retrieval, and optionally export XLSX tables."""

        dataset = self._load_dataset(dataset_path)
        requested_k = max(1, int(top_k))
        detail_rows: list[dict[str, Any]] = []

        for row_index, row in dataset.iterrows():
            question = str(row.get("question", "")).strip()
            expected_source = str(row.get("expected_source", "")).strip()
            expected_answer = str(row.get("expected_answer", "")).strip()

            if not question:
                detail_rows.append(
                    self._error_row(
                        row_index,
                        question,
                        expected_source,
                        expected_answer,
                        requested_k,
                        "question 为空。",
                    )
                )
                continue

            try:
                hits = self.vector_store.search(question, top_k=requested_k)
            except VectorStoreError as exc:
                detail_rows.append(
                    self._error_row(
                        row_index,
                        question,
                        expected_source,
                        expected_answer,
                        requested_k,
                        str(exc),
                    )
                )
                continue

            retrieved_sources = [
                str(hit.metadata.get("source", "")) for hit in hits
            ]
            retrieved_filenames = [
                str(hit.metadata.get("filename", "")) for hit in hits
            ]
            hit_rank = self._first_hit_rank(
                expected_source,
                retrieved_sources,
                retrieved_filenames,
            )
            hit = hit_rank is not None

            detail_rows.append(
                {
                    "序号": int(row_index) + 1,
                    "问题": question,
                    "期望来源": expected_source,
                    "期望答案": expected_answer,
                    "K": requested_k,
                    "是否命中": bool(hit),
                    "首次命中排名": hit_rank,
                    "倒数排名": 1.0 / hit_rank if hit_rank else 0.0,
                    "检索来源": " | ".join(retrieved_sources),
                    "检索文件": " | ".join(retrieved_filenames),
                    "错误": "",
                }
            )

        details = pd.DataFrame(detail_rows)
        if details.empty:
            details = pd.DataFrame(
                columns=[
                    "序号",
                    "问题",
                    "期望来源",
                    "期望答案",
                    "K",
                    "是否命中",
                    "首次命中排名",
                    "倒数排名",
                    "检索来源",
                    "检索文件",
                    "错误",
                ]
            )

        valid_rows = details[details["错误"].fillna("").astype(str) == ""]
        total = int(len(valid_rows))
        hit_count = int(valid_rows["是否命中"].sum()) if total else 0
        hit_rate = hit_count / total if total else 0.0
        mrr = float(valid_rows["倒数排名"].mean()) if total else 0.0

        summary = pd.DataFrame(
            [
                {
                    "数据集": str(Path(dataset_path)),
                    "K": requested_k,
                    "样本数": total,
                    "命中数": hit_count,
                    "错误数": int(len(details) - total),
                    "Hit@K": hit_rate,
                    "MRR": mrr,
                    "评测时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            ]
        )

        result = EvaluationResult(summary=summary, details=details)
        if output_path is not None:
            saved = self.save_results(result, output_path)
            result.output_path = str(saved)
        return result

    def save_results(
        self,
        result: EvaluationResult,
        output_path: str | Path,
    ) -> Path:
        """Write professional XLSX summary and detail sheets."""

        path = Path(output_path).expanduser()
        if not path.is_absolute():
            path = self.settings.eval_output_dir / path
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                result.summary.to_excel(
                    writer,
                    sheet_name="评测指标",
                    index=False,
                )
                result.details.to_excel(
                    writer,
                    sheet_name="问题明细",
                    index=False,
                )
            self._format_workbook(path)
        except Exception as exc:
            raise EvaluationError(f"评测表格导出失败: {exc}") from exc
        return path.resolve()

    def default_output_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.settings.eval_output_dir / f"retrieval_eval_{timestamp}.xlsx"

    @staticmethod
    def _load_dataset(path: str | Path) -> pd.DataFrame:
        dataset_path = Path(path).expanduser()
        try:
            dataset_path = dataset_path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise EvaluationError(f"评测数据集不存在: {dataset_path}") from exc
        if not dataset_path.is_file():
            raise EvaluationError(f"评测数据集不是文件: {dataset_path}")
        if dataset_path.suffix.lower() != ".csv":
            raise EvaluationError("评测数据集必须是 CSV 文件。")

        try:
            dataset = pd.read_csv(dataset_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                dataset = pd.read_csv(dataset_path, encoding="gb18030")
            except Exception as exc:
                raise EvaluationError(
                    f"CSV 编码无法识别: {dataset_path}"
                ) from exc
        except pd.errors.EmptyDataError as exc:
            raise EvaluationError("评测 CSV 为空。") from exc
        except pd.errors.ParserError as exc:
            raise EvaluationError(f"CSV 格式解析失败: {exc}") from exc
        except OSError as exc:
            raise EvaluationError(f"CSV 读取失败: {exc}") from exc

        dataset.columns = [str(column).strip() for column in dataset.columns]
        missing = RetrievalEvaluator.REQUIRED_COLUMNS - set(dataset.columns)
        if missing:
            raise EvaluationError(
                "CSV 缺少必要列: " + ", ".join(sorted(missing))
            )
        if dataset.empty:
            raise EvaluationError("评测 CSV 没有数据行。")

        if "expected_answer" not in dataset.columns:
            dataset["expected_answer"] = ""
        return dataset

    @staticmethod
    def _first_hit_rank(
        expected_source: str,
        retrieved_sources: list[str],
        retrieved_filenames: list[str],
    ) -> int | None:
        expected_items = [
            item.strip().lower()
            for item in re.split(r"[|;]+", expected_source or "")
            if item.strip()
        ]
        if not expected_items:
            return None

        for rank, (source, filename) in enumerate(
            zip(retrieved_sources, retrieved_filenames),
            start=1,
        ):
            for expected in expected_items:
                if RetrievalEvaluator.source_matches(
                    expected,
                    source,
                    filename,
                ):
                    return rank
        return None

    @staticmethod
    def source_matches(
        expected: str,
        retrieved_source: str,
        retrieved_filename: str = "",
    ) -> bool:
        expected_value = (expected or "").strip().lower()
        source_value = (retrieved_source or "").strip().lower()
        filename_value = (retrieved_filename or "").strip().lower()
        if not expected_value:
            return False
        if not source_value and not filename_value:
            return False
        if expected_value in {source_value, filename_value}:
            return True
        if not filename_value and source_value:
            filename_value = Path(source_value).name.lower()
        checks = []
        if source_value:
            checks.extend(
                [
                    expected_value in source_value,
                    source_value in expected_value,
                ]
            )
        if filename_value:
            checks.extend(
                [
                    expected_value in filename_value,
                    filename_value in expected_value,
                ]
            )
        return any(checks)

    @staticmethod
    def _error_row(
        row_index: int,
        question: str,
        expected_source: str,
        expected_answer: str,
        top_k: int,
        error: str,
    ) -> dict[str, Any]:
        return {
            "序号": int(row_index) + 1,
            "问题": question,
            "期望来源": expected_source,
            "期望答案": expected_answer,
            "K": top_k,
            "是否命中": False,
            "首次命中排名": None,
            "倒数排名": 0.0,
            "检索来源": "",
            "检索文件": "",
            "错误": error,
        }

    @staticmethod
    def _format_workbook(path: Path) -> None:
        try:
            from openpyxl import load_workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError as exc:
            raise EvaluationError(
                "缺少 openpyxl，无法格式化评测表格。"
            ) from exc

        workbook = load_workbook(path)
        header_fill = PatternFill("solid", fgColor="D9EAF7")
        header_font = Font(name="Arial", bold=True, color="1F2937")
        body_font = Font(name="Arial", color="111827")

        for worksheet in workbook.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True,
                )
            for row in worksheet.iter_rows(min_row=2):
                for cell in row:
                    cell.font = body_font
                    cell.alignment = Alignment(vertical="top", wrap_text=True)

            for column_cells in worksheet.columns:
                max_length = max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in column_cells
                )
                column_letter = column_cells[0].column_letter
                worksheet.column_dimensions[column_letter].width = min(
                    max(max_length + 2, 12),
                    50,
                )

        summary_sheet = workbook["评测指标"]
        for cell in summary_sheet[2]:
            if cell.column_letter in {"F", "G"}:
                cell.number_format = "0.00%"

        workbook.save(path)
~~~~

## src/cli_main.py

~~~~text
"""Command-line interface for enterprise-doc-assistant."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent_tools import DocumentAgent, DocumentIndexer, IndexingResult
from src.config import Settings, get_settings
from src.document_parser import DocumentParseError
from src.evaluator import EvaluationError, RetrievalEvaluator
from src.llm_client import LLMClientError
from src.vector_store import ChromaVectorStore, VectorStoreError


logger = logging.getLogger(__name__)


def _configure_console() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enterprise-doc-assistant",
        description="企业文档智能助手 CLI（GLM-4.7-Flash + 本地 BGE + ChromaDB）",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    subparsers = parser.add_subparsers(dest="command")

    ingest = subparsers.add_parser("ingest", help="上传并索引 PDF/DOCX/MD/TXT")
    ingest.add_argument("paths", nargs="+", help="文件或目录路径")
    ingest.add_argument(
        "--no-recursive",
        action="store_true",
        help="目录模式不递归子目录",
    )
    ingest.add_argument(
        "--reset",
        action="store_true",
        help="索引前清空现有知识库",
    )

    chat = subparsers.add_parser("chat", help="启动多轮对话")
    chat.add_argument(
        "--show-tools",
        action="store_true",
        help="显示工具调用轨迹",
    )

    ask = subparsers.add_parser("ask", help="执行一次问答")
    ask.add_argument("question", help="问题文本")
    ask.add_argument(
        "--show-tools",
        action="store_true",
        help="显示工具调用轨迹",
    )

    subparsers.add_parser("documents", help="列出已索引文档")

    delete = subparsers.add_parser("delete", help="按 doc_id 删除文档")
    delete.add_argument("doc_id", help="文档 ID")

    evaluate = subparsers.add_parser("evaluate", help="运行离线 Top-K 检索评测")
    evaluate.add_argument(
        "--dataset",
        default="test_dataset/test_qa.csv",
        help="CSV 数据集路径",
    )
    evaluate.add_argument("--top-k", type=int, default=5, help="Top-K")
    evaluate.add_argument(
        "--output",
        default="",
        help="XLSX 输出路径；为空时写入 data/evaluations",
    )

    subparsers.add_parser("config", help="显示脱敏配置")
    return parser


def _build_services(
    settings: Settings,
) -> tuple[ChromaVectorStore, DocumentIndexer, DocumentAgent]:
    vector_store = ChromaVectorStore(settings)
    indexer = DocumentIndexer(settings, vector_store)
    agent = DocumentAgent(settings, vector_store=vector_store)
    return vector_store, indexer, agent


def _print_index_results(results: list[Any]) -> int:
    success_count = 0
    for result in results:
        if result.success:
            success_count += 1
            print(
                f"[成功] {result.source} | {result.chunks} 个分块 | "
                f"doc_id={result.doc_id}"
            )
        else:
            print(f"[失败] {result.source} | {result.message}")

    print(
        f"\n处理完成：成功 {success_count}，失败 {len(results) - success_count}。"
    )
    return 0 if success_count == len(results) else 1


def _command_ingest(args: argparse.Namespace, settings: Settings) -> int:
    vector_store, indexer, _ = _build_services(settings)
    if args.reset:
        vector_store.reset()
        print("知识库已清空。")

    results: list[Any] = []
    for raw_path in args.paths:
        path = Path(raw_path).expanduser()
        if path.is_dir():
            try:
                results.extend(
                    indexer.index_directory(
                        path,
                        recursive=not args.no_recursive,
                    )
                )
            except DocumentParseError as exc:
                print(f"[失败] {path} | {exc}")
                results.append(
                    IndexingResult(
                        source=str(path),
                        success=False,
                        message=str(exc),
                    )
                )
        else:
            results.extend(indexer.index_paths([path]))

    if not results:
        print("未发现可处理的 PDF/DOCX/MD/TXT 文件。")
        return 1
    return _print_index_results(results)


def _print_agent_response(response: Any, *, show_tools: bool) -> None:
    print("\n助手：")
    print(response.answer)
    if response.sources:
        print("\n来源：")
        seen: set[str] = set()
        for source in response.sources:
            label = source.get("filename") or source.get("source") or source.get(
                "doc_id", ""
            )
            if label and label not in seen:
                print(f"- {label}")
                seen.add(label)
    if show_tools and response.tool_calls:
        print("\n工具轨迹：")
        for record in response.tool_calls:
            print(
                f"- {record.get('name')} | {record.get('status')} | "
                f"{record.get('arguments', {})}"
            )
    if response.report_path:
        print(f"\n报告：{response.report_path}")


def _command_ask(args: argparse.Namespace, settings: Settings) -> int:
    _, _, agent = _build_services(settings)
    response = agent.run(args.question)
    _print_agent_response(response, show_tools=args.show_tools)
    return 0


def _command_chat(args: argparse.Namespace, settings: Settings) -> int:
    _, _, agent = _build_services(settings)
    print("=" * 68)
    print("enterprise-doc-assistant | 输入 /exit 退出，/clear 清空会话记忆")
    print("=" * 68)

    while True:
        try:
            question = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n会话已结束。")
            return 0

        if not question:
            continue
        if question.lower() in {"/exit", "exit", "quit"}:
            print("会话已结束。")
            return 0
        if question.lower() == "/clear":
            agent.clear_memory()
            print("会话记忆已清空。")
            continue

        try:
            response = agent.run(question)
            _print_agent_response(response, show_tools=args.show_tools)
        except (LLMClientError, VectorStoreError, ValueError) as exc:
            print(f"\n[错误] {exc}")


def _command_documents(settings: Settings) -> int:
    vector_store = ChromaVectorStore(settings)
    try:
        documents = vector_store.list_documents()
        total_chunks = vector_store.count()
    except VectorStoreError as exc:
        print(f"[错误] {exc}")
        return 1

    if not documents:
        print("知识库为空。")
        return 0

    print(f"文档数：{len(documents)}，总向量分块数：{total_chunks}\n")
    print(f"{'文件名':<30} {'分块':>6}  doc_id")
    print("-" * 72)
    for document in documents:
        filename = str(document.get("filename", ""))[:28]
        print(
            f"{filename:<30} {int(document.get('chunks', 0)):>6}  "
            f"{document.get('doc_id', '')}"
        )
    return 0


def _command_delete(args: argparse.Namespace, settings: Settings) -> int:
    vector_store = ChromaVectorStore(settings)
    try:
        vector_store.delete_document(args.doc_id)
    except VectorStoreError as exc:
        print(f"[错误] {exc}")
        return 1
    print(f"已删除 doc_id={args.doc_id} 的文档分块。")
    return 0


def _command_evaluate(args: argparse.Namespace, settings: Settings) -> int:
    vector_store = ChromaVectorStore(settings)
    evaluator = RetrievalEvaluator(settings, vector_store)
    output = args.output or str(evaluator.default_output_path())
    result = evaluator.evaluate(
        args.dataset,
        top_k=args.top_k,
        output_path=output,
    )
    print(result.summary_text())
    print("\n问题明细：")
    print(
        result.details[
            ["序号", "问题", "期望来源", "是否命中", "首次命中排名", "错误"]
        ].to_string(index=False)
    )
    print(f"\n评测表格：{result.output_path}")
    return 0


def _command_config(settings: Settings) -> int:
    for key, value in settings.safe_summary().items():
        print(f"{key}: {value}")
    print(f"chunk_size: {settings.chunk_size}")
    print(f"chunk_overlap: {settings.chunk_overlap}")
    print(f"max_history_messages: {settings.max_history_messages}")
    print(f"max_context_chars: {settings.max_context_chars}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console()
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not args.command:
        parser.print_help()
        return 0

    settings = get_settings()
    try:
        if args.command == "ingest":
            return _command_ingest(args, settings)
        if args.command == "ask":
            return _command_ask(args, settings)
        if args.command == "chat":
            return _command_chat(args, settings)
        if args.command == "documents":
            return _command_documents(settings)
        if args.command == "delete":
            return _command_delete(args, settings)
        if args.command == "evaluate":
            return _command_evaluate(args, settings)
        if args.command == "config":
            return _command_config(settings)
    except (DocumentParseError, EvaluationError, LLMClientError, VectorStoreError) as exc:
        print(f"\n[错误] {exc}")
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消。")
        return 130
    except Exception as exc:
        logger.exception("Unhandled CLI error")
        print(f"\n[未预期错误] {exc}")
        return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
~~~~

## src/web_gradio.py

~~~~text
"""Gradio web interface for enterprise-doc-assistant."""

from __future__ import annotations

import logging
import shutil
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio as gr

from src.agent_tools import DocumentAgent, DocumentIndexer
from src.config import Settings, get_settings
from src.document_parser import DocumentParser
from src.evaluator import RetrievalEvaluator
from src.llm_client import LLMClientError, ZhipuLLMClient
from src.vector_store import ChromaVectorStore, VectorStoreError


logger = logging.getLogger(__name__)

_SERVICES_LOCK = threading.RLock()
_SERVICES: "WebServices | None" = None


class WebServices:
    """Lazily initialized shared application services."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vector_store = ChromaVectorStore(settings)
        self.llm_client = ZhipuLLMClient(settings)
        self.indexer = DocumentIndexer(settings, self.vector_store)
        self.agent = DocumentAgent(
            settings,
            llm_client=self.llm_client,
            vector_store=self.vector_store,
        )
        self.evaluator = RetrievalEvaluator(settings, self.vector_store)


def get_services() -> WebServices:
    global _SERVICES
    with _SERVICES_LOCK:
        if _SERVICES is None:
            _SERVICES = WebServices(get_settings())
        return _SERVICES


def _copy_uploads(paths: list[str] | tuple[str, ...] | None) -> list[Path]:
    if not paths:
        return []

    services = get_services()
    upload_dir = services.settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []

    for raw_path in paths:
        source = Path(raw_path).expanduser()
        if not source.is_file():
            continue
        safe_name = source.name.replace(" ", "_")
        target = upload_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"
        try:
            shutil.copy2(source, target)
            copied.append(target)
        except OSError as exc:
            logger.warning("Upload copy failed for %s: %s", source, exc)
    return copied


def _format_documents(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "知识库暂无已索引文档。"

    lines = [
        "| 文件名 | 类型 | 分块数 | doc_id |",
        "|---|---:|---:|---|",
    ]
    for document in documents[:100]:
        filename = str(document.get("filename", "")).replace("|", "\\|")
        extension = str(document.get("extension", "")).replace("|", "\\|")
        chunks = int(document.get("chunks", 0))
        doc_id = str(document.get("doc_id", ""))
        lines.append(
            f"| {filename} | {extension} | {chunks} | `{doc_id}` |"
        )
    if len(documents) > 100:
        lines.append(f"| 其余 {len(documents) - 100} 个文档已省略 |  |  |  |")
    return "\n".join(lines)


def _knowledge_state() -> str:
    services = get_services()
    try:
        count = services.vector_store.count()
        documents = services.vector_store.list_documents()
        return (
            f"**知识库状态**：{len(documents)} 个文档，"
            f"{count} 个向量分块"
        )
    except VectorStoreError as exc:
        return f"**知识库状态**：初始化失败，{exc}"


def initial_status() -> str:
    services = get_services()
    summary = services.settings.safe_summary()
    api_state = (
        "已配置" if summary["api_key_configured"] else "未配置 ZHIPU_API_KEY"
    )
    return (
        f"**模型**：`{summary['model']}`（{api_state}）  \n"
        f"**嵌入模型**：`{summary['embedding_model']}`  \n"
        f"**ChromaDB**：`{summary['chroma_dir']}`  \n"
        f"**检索 Top-K**：{summary['retrieval_top_k']}"
    )


def health_handler() -> str:
    services = get_services()
    lines = [initial_status()]
    try:
        count = services.vector_store.count()
        lines.append(f"**知识库**：{count} 个向量分块")
    except VectorStoreError as exc:
        lines.append(f"**知识库异常**：{exc}")

    healthy, message = services.llm_client.health_check()
    lines.append(
        f"**GLM 连通性**：{'正常' if healthy else '失败'}  \n`{message}`"
    )
    return "\n\n".join(lines)


def ingest_handler(
    files: list[str] | tuple[str, ...] | None,
    chunk_size: int,
    chunk_overlap: int,
    reset_first: bool,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str, str]:
    services = get_services()
    if not files:
        return "请选择 PDF、DOCX、MD 或 TXT 文件。", _format_documents([]), _knowledge_state()

    if int(chunk_overlap) >= int(chunk_size):
        return (
            "分块重叠必须小于分块大小。",
            _format_documents(services.vector_store.list_documents()),
            _knowledge_state(),
        )

    try:
        if reset_first:
            progress(0.05, desc="正在清空知识库")
            services.vector_store.reset()

        copied = _copy_uploads(files)
        if not copied:
            return "上传文件复制失败，请检查磁盘权限。", _format_documents([]), _knowledge_state()

        parser = DocumentParser(
            chunk_size=int(chunk_size),
            chunk_overlap=int(chunk_overlap),
        )
        indexer = DocumentIndexer(
            services.settings,
            services.vector_store,
            parser=parser,
        )

        progress(0.15, desc="正在解析并向量化")
        results = indexer.index_paths(copied)
        succeeded = [item for item in results if item.success]
        failed = [item for item in results if not item.success]
        total_chunks = sum(item.chunks for item in succeeded)

        status_lines = [
            (
                f"**索引完成**：成功 {len(succeeded)} 个，失败 "
                f"{len(failed)} 个，新增/更新 {total_chunks} 个分块。"
            )
        ]
        for item in failed:
            status_lines.append(
                f"- `{Path(item.source).name}`：{item.message}"
            )

        documents = services.vector_store.list_documents()
        progress(1.0, desc="完成")
        return (
            "\n".join(status_lines),
            _format_documents(documents),
            _knowledge_state(),
        )
    except (ValueError, VectorStoreError, OSError) as exc:
        return f"索引失败：{exc}", _format_documents([]), _knowledge_state()
    except Exception as exc:
        logger.exception("Unexpected web ingestion error")
        return f"索引失败：{exc}", _format_documents([]), _knowledge_state()


def refresh_documents_handler() -> tuple[str, str]:
    services = get_services()
    try:
        documents = services.vector_store.list_documents()
        return _format_documents(documents), _knowledge_state()
    except VectorStoreError as exc:
        return f"读取文档列表失败：{exc}", f"**知识库状态**：{exc}"


def clear_knowledge_handler() -> tuple[str, str, str]:
    services = get_services()
    try:
        services.vector_store.reset()
        return "知识库已清空。", _format_documents([]), _knowledge_state()
    except VectorStoreError as exc:
        return f"清空失败：{exc}", _format_documents([]), _knowledge_state()


def chat_handler(
    message: str,
    history: list[dict[str, Any]] | None,
) -> tuple[str, list[dict[str, Any]], str]:
    history = list(history or [])
    question = (message or "").strip()
    if not question:
        return "", history, _knowledge_state()

    history.append({"role": "user", "content": question})
    services = get_services()

    try:
        response = services.agent.run(question)
        answer = response.answer
        if response.sources:
            source_names: list[str] = []
            seen: set[str] = set()
            for source in response.sources:
                label = (
                    source.get("filename")
                    or source.get("source")
                    or source.get("doc_id", "")
                )
                if label and label not in seen:
                    source_names.append(label)
                    seen.add(label)
            if source_names:
                answer += "\n\n**引用来源**  \n" + "  \n".join(
                    f"- {name}" for name in source_names
                )
        if response.report_path:
            answer += f"\n\n**报告文件**：`{response.report_path}`"
        history.append({"role": "assistant", "content": answer})
        status = _knowledge_state()
    except (LLMClientError, VectorStoreError, ValueError) as exc:
        history.append({"role": "assistant", "content": f"请求失败：{exc}"})
        status = f"**请求失败**：{exc}"
    except Exception as exc:
        logger.exception("Unexpected web chat error")
        history.append(
            {
                "role": "assistant",
                "content": f"系统发生未预期错误：{exc}",
            }
        )
        status = f"**系统异常**：{exc}"

    return "", history, status


def clear_chat_handler() -> tuple[list[Any], str]:
    get_services().agent.clear_memory()
    return [], "会话记忆已清空。"


def build_demo(settings: Settings | None = None) -> gr.Blocks:
    """Build the complete Gradio application."""

    global _SERVICES
    if settings is not None:
        with _SERVICES_LOCK:
            _SERVICES = WebServices(settings)

    services = get_services()
    initial_documents = _format_documents(
        services.vector_store.list_documents()
    )
    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.teal,
        secondary_hue=gr.themes.colors.blue,
        neutral_hue=gr.themes.colors.gray,
        font=[
            "Segoe UI",
            "Microsoft YaHei",
            "sans-serif",
        ],
    )

    css = """
    :root {
      --ink: #17212b;
      --muted: #5d6b78;
      --line: #d8dee5;
      --accent: #0f766e;
      --accent-soft: #e7f4f2;
      --surface: #f7f8fa;
    }
    .gradio-container {
      max-width: 1440px !important;
      background: #ffffff !important;
      color: var(--ink);
    }
    .app-header {
      border-bottom: 1px solid var(--line);
      padding: 14px 2px 12px;
      margin-bottom: 12px;
    }
    .app-title {
      font-size: 25px !important;
      font-weight: 700 !important;
      letter-spacing: 0 !important;
      margin: 0 !important;
    }
    .app-subtitle {
      color: var(--muted) !important;
      margin-top: 3px !important;
    }
    .panel {
      border: 1px solid var(--line) !important;
      border-radius: 8px !important;
      padding: 12px !important;
      background: #ffffff !important;
    }
    .status-box {
      background: var(--surface) !important;
      border-left: 3px solid var(--accent) !important;
      border-radius: 4px !important;
      padding: 10px 12px !important;
    }
    .send-button {
      min-width: 96px !important;
    }
    .chatbot {
      border: 1px solid var(--line) !important;
      border-radius: 8px !important;
    }
    footer { display: none !important; }
    """

    with gr.Blocks(
        title="企业文档智能助手",
        theme=theme,
        css=css,
        fill_height=True,
    ) as demo:
        with gr.Row(elem_classes=["app-header"]):
            with gr.Column(scale=8):
                gr.Markdown(
                    "# 企业文档智能助手",
                    elem_classes=["app-title"],
                )
                gr.Markdown(
                    "私有知识库问答 · GLM-4.7-Flash · 本地 BGE · ChromaDB",
                    elem_classes=["app-subtitle"],
                )
            with gr.Column(scale=3, min_width=260):
                status = gr.Markdown(
                    initial_status(),
                    elem_classes=["status-box"],
                )

        with gr.Row(equal_height=False):
            with gr.Column(scale=5, min_width=360):
                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("### 文档管理")
                    upload = gr.File(
                        label="文档",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".md", ".txt"],
                        type="filepath",
                    )
                    with gr.Accordion("分块参数", open=False):
                        chunk_size = gr.Slider(
                            minimum=200,
                            maximum=1500,
                            value=services.settings.chunk_size,
                            step=50,
                            label="分块大小（字符）",
                        )
                        chunk_overlap = gr.Slider(
                            minimum=0,
                            maximum=500,
                            value=min(
                                services.settings.chunk_overlap,
                                500,
                            ),
                            step=25,
                            label="重叠字符数",
                        )
                        reset_first = gr.Checkbox(
                            value=False,
                            label="索引前清空知识库",
                        )
                    with gr.Row():
                        ingest_button = gr.Button(
                            "建立索引",
                            variant="primary",
                        )
                        refresh_button = gr.Button("刷新列表")
                    ingest_status = gr.Markdown(
                        "尚未执行索引。",
                        elem_classes=["status-box"],
                    )
                    knowledge_status = gr.Markdown(_knowledge_state())
                    document_table = gr.Markdown(initial_documents)
                    clear_knowledge_button = gr.Button(
                        "清空知识库",
                        variant="stop",
                    )

            with gr.Column(scale=7, min_width=460):
                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("### 知识问答")
                    chatbot = gr.Chatbot(
                        value=[],
                        type="messages",
                        label="对话",
                        height=590,
                        elem_classes=["chatbot"],
                    )
                    with gr.Row():
                        message = gr.Textbox(
                            placeholder="输入问题",
                            label="",
                            lines=1,
                            max_lines=6,
                            scale=8,
                            autofocus=True,
                        )
                        send_button = gr.Button(
                            "发送",
                            variant="primary",
                            elem_classes=["send-button"],
                            scale=1,
                        )
                    with gr.Row():
                        clear_chat_button = gr.Button("清空会话")
                        health_button = gr.Button("检查连接")

        ingest_button.click(
            fn=ingest_handler,
            inputs=[
                upload,
                chunk_size,
                chunk_overlap,
                reset_first,
            ],
            outputs=[ingest_status, document_table, knowledge_status],
            show_progress="full",
        )
        refresh_button.click(
            fn=refresh_documents_handler,
            inputs=[],
            outputs=[document_table, knowledge_status],
        )
        clear_knowledge_button.click(
            fn=clear_knowledge_handler,
            inputs=[],
            outputs=[
                ingest_status,
                document_table,
                knowledge_status,
            ],
        )
        send_button.click(
            fn=chat_handler,
            inputs=[message, chatbot],
            outputs=[message, chatbot, status],
        )
        message.submit(
            fn=chat_handler,
            inputs=[message, chatbot],
            outputs=[message, chatbot, status],
        )
        clear_chat_button.click(
            fn=clear_chat_handler,
            inputs=[],
            outputs=[chatbot, status],
        )
        health_button.click(
            fn=health_handler,
            inputs=[],
            outputs=[status],
        )

    return demo


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = get_settings()
    demo = build_demo(settings)
    demo.queue(default_concurrency_limit=4).launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        show_error=True,
        inbrowser=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~~

## test_dataset/test_qa.csv

~~~~text
question,expected_source,expected_answer
员工入职后多久可以申请年假？,employee_handbook.md,员工通过试用期后可按规定申请年假。
报销申请需要提交哪些材料？,expense_policy.md,需要提交发票、费用明细和审批记录。
客户数据可以导出到个人设备吗？,data_security_policy.md,未经审批不得导出客户数据到个人设备。
产品故障的升级响应时限是多少？,service_sla.md,高优先级故障应在约定时限内升级处理。
项目变更由谁审批？,project_management.md,项目变更需经项目经理和业务负责人审批。
会议室预订最长可以提前多少天？,office_operations.md,会议室可按公司规定提前预订。
新供应商准入需要完成哪些步骤？,procurement_policy.md,需完成资质审查、风险评估和合同审批。
研发环境代码提交有哪些要求？,engineering_standard.md,代码需通过评审和自动化检查后合并。
员工培训记录在哪里查询？,training_guide.md,员工可在内部学习平台查询培训记录。
文档对外发送前需要做什么？,information_classification.md,对外发送前需完成密级确认和授权审批。
~~~~

## tests/__init__.py

~~~~text
"""Test package."""
~~~~

## tests/test_core.py

~~~~text
"""Core tests that do not require external model downloads."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.conversation_mem import ConversationMemory
from src.document_parser import DocumentParseError, DocumentParser, chunk_text
from src.evaluator import RetrievalEvaluator


class DocumentParserTests(unittest.TestCase):
    def test_chunk_text_has_overlap_and_multiple_chunks(self) -> None:
        text = "第一句。" * 160
        chunks = chunk_text(text, chunk_size=220, chunk_overlap=50)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.text for chunk in chunks))
        self.assertEqual(chunks[0].index, 0)
        self.assertLess(chunks[1].start_char, chunks[0].end_char)

    def test_parse_markdown_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.md"
            path.write_text("# 标题\n\n这是用于测试的文档内容。", encoding="utf-8")
            document = DocumentParser(chunk_size=100, chunk_overlap=20).parse_file(
                path
            )

            self.assertEqual(document.filename, "sample.md")
            self.assertIn("测试", document.text)
            self.assertGreaterEqual(len(document.chunks), 1)
            self.assertEqual(document.chunks[0].metadata, {})

    def test_missing_file_raises_clear_error(self) -> None:
        with self.assertRaises(DocumentParseError):
            DocumentParser().parse_file("missing-file.pdf")

    def test_parse_docx_paragraphs(self) -> None:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            self.skipTest("python-docx is not installed.")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "handbook.docx"
            document = DocxDocument()
            document.add_heading("员工手册", level=1)
            document.add_paragraph("员工通过试用期后可以申请年假。")
            document.save(path)

            parsed = DocumentParser().parse_file(path)

            self.assertIn("员工手册", parsed.text)
            self.assertIn("试用期", parsed.text)
            self.assertEqual(parsed.extension, ".docx")


class ConversationMemoryTests(unittest.TestCase):
    def test_history_is_trimmed_to_message_limit(self) -> None:
        memory = ConversationMemory(max_messages=4, max_context_chars=2000)
        memory.add_exchange("问题1", "回答1")
        memory.add_exchange("问题2", "回答2")
        memory.add_exchange("问题3", "回答3")

        snapshot = memory.snapshot()
        self.assertEqual(len(snapshot), 4)
        self.assertEqual(snapshot[0]["content"], "问题2")
        self.assertEqual(snapshot[-1]["content"], "回答3")

    def test_context_keeps_system_and_current_question(self) -> None:
        memory = ConversationMemory(max_messages=4, max_context_chars=2000)
        memory.add_exchange("旧问题", "旧回答")
        messages = memory.context_messages("系统提示", "当前问题")

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["content"], "当前问题")

    def test_long_current_question_is_bounded(self) -> None:
        memory = ConversationMemory(max_messages=4, max_context_chars=1000)
        messages = memory.context_messages("系统提示", "长问题" * 2000)

        total_chars = sum(len(message["content"]) for message in messages)
        self.assertLessEqual(total_chars, 1000)


class EvaluatorTests(unittest.TestCase):
    def test_source_matching_accepts_filename_and_path(self) -> None:
        self.assertTrue(
            RetrievalEvaluator.source_matches(
                "employee_handbook.md",
                "/data/docs/employee_handbook.md",
                "employee_handbook.md",
            )
        )
        self.assertFalse(
            RetrievalEvaluator.source_matches(
                "security_policy.md",
                "/data/docs/employee_handbook.md",
                "employee_handbook.md",
            )
        )


if __name__ == "__main__":
    unittest.main()
~~~~

## tests/test_agent_loop.py

~~~~text
"""Function-calling loop tests using local fakes."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import deque
from pathlib import Path
from typing import Any

from src.agent_tools import DocumentAgent
from src.config import Settings
from src.evaluator import RetrievalEvaluator
from src.vector_store import SearchHit


def make_settings(root: Path) -> Settings:
    data_dir = root / "data"
    return Settings(
        project_root=root,
        zhipu_api_key="test-key",
        zhipu_base_url="https://open.bigmodel.cn/api/paas/v4",
        zhipu_model="glm-4.7-flash",
        llm_temperature=0.2,
        llm_timeout=30.0,
        llm_max_retries=0,
        embedding_model_name="BAAI/bge-small-zh",
        embedding_device="cpu",
        embedding_local_only=True,
        embedding_cache_dir=data_dir / "models",
        chroma_persist_dir=data_dir / "chroma",
        chroma_collection="test_collection",
        chunk_size=500,
        chunk_overlap=100,
        retrieval_top_k=3,
        max_history_messages=6,
        max_context_chars=8000,
        upload_dir=data_dir / "uploads",
        report_dir=data_dir / "reports",
        eval_output_dir=data_dir / "evaluations",
        gradio_server_name="127.0.0.1",
        gradio_server_port=7860,
        gradio_share=False,
    )


class FakeVectorStore:
    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        source_filter: str | None = None,
    ) -> list[SearchHit]:
        return [
            SearchHit(
                vector_id="doc-1:0",
                text="员工通过试用期后可以申请年假。",
                metadata={
                    "doc_id": "doc-1",
                    "source": "/docs/employee_handbook.md",
                    "filename": "employee_handbook.md",
                    "chunk_index": 0,
                },
                score=0.93,
                distance=0.07,
            )
        ][: top_k or 3]


class FakeLLM:
    def __init__(self) -> None:
        self.responses = deque(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_retrieve",
                            "type": "function",
                            "function": {
                                "name": "knowledge_retrieve",
                                "arguments": json.dumps(
                                    {"query": "员工何时申请年假"},
                                    ensure_ascii=False,
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_export",
                            "type": "function",
                            "function": {
                                "name": "export_report",
                                "arguments": json.dumps(
                                    {
                                        "question": "员工何时申请年假？",
                                        "answer": "通过试用期后可以申请。",
                                        "sources": ["employee_handbook.md"],
                                        "report_name": "annual_leave",
                                    },
                                    ensure_ascii=False,
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": "员工通过试用期后可以申请年假。",
                    "tool_calls": [],
                },
            ]
        )
        self.calls: list[dict[str, Any]] = []

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append({"messages": list(messages), "kwargs": dict(kwargs)})
        return self.responses.popleft()


class AgentLoopTests(unittest.TestCase):
    def test_agent_executes_tools_and_exports_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings(root)
            settings.ensure_directories()
            fake_llm = FakeLLM()
            agent = DocumentAgent(
                settings,
                llm_client=fake_llm,  # type: ignore[arg-type]
                vector_store=FakeVectorStore(),  # type: ignore[arg-type]
            )

            response = agent.run("员工何时申请年假？")

            self.assertIn("试用期", response.answer)
            self.assertEqual(len(response.tool_calls), 2)
            self.assertEqual(response.tool_calls[0]["name"], "knowledge_retrieve")
            self.assertEqual(response.tool_calls[1]["name"], "export_report")
            self.assertIsNotNone(response.report_path)
            self.assertTrue(Path(response.report_path or "").is_file())
            self.assertEqual(len(agent.memory), 2)
            self.assertEqual(len(fake_llm.calls[0]["kwargs"]["tools"]), 3)

            second_call_messages = fake_llm.calls[1]["messages"]
            self.assertTrue(
                any(message.get("role") == "tool" for message in second_call_messages)
            )

    def test_evaluator_exports_summary_and_detail_sheets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings(root)
            settings.ensure_directories()
            dataset_path = root / "qa.csv"
            dataset_path.write_text(
                "question,expected_source,expected_answer\n"
                "员工何时申请年假？,employee_handbook.md,通过试用期后。\n",
                encoding="utf-8-sig",
            )
            evaluator = RetrievalEvaluator(
                settings,
                FakeVectorStore(),  # type: ignore[arg-type]
            )

            result = evaluator.evaluate(
                dataset_path,
                top_k=3,
                output_path=root / "eval.xlsx",
            )

            self.assertEqual(float(result.summary.iloc[0]["Hit@K"]), 1.0)
            self.assertIsNotNone(result.output_path)
            from openpyxl import load_workbook

            workbook = load_workbook(result.output_path or "")
            self.assertEqual(
                workbook.sheetnames,
                ["评测指标", "问题明细"],
            )
            self.assertEqual(workbook["问题明细"]["F2"].value, True)


if __name__ == "__main__":
    unittest.main()
~~~~

## tests/test_web_smoke.py

~~~~text
"""Optional Gradio UI smoke tests.

The tests are skipped when the full web dependency stack is unavailable.
"""

from __future__ import annotations

import importlib.util
import unittest


FULL_WEB_STACK = all(
    importlib.util.find_spec(name) is not None
    for name in ("gradio", "openai", "chromadb", "sentence_transformers")
)


@unittest.skipUnless(FULL_WEB_STACK, "Web dependency stack is not installed.")
class WebSmokeTests(unittest.TestCase):
    def test_ui_contains_core_components(self) -> None:
        from src.config import get_settings
        from src.web_gradio import build_demo

        demo = build_demo(get_settings())
        component_types = {type(item).__name__ for item in demo.blocks.values()}

        self.assertIn("File", component_types)
        self.assertIn("Chatbot", component_types)
        self.assertIn("Textbox", component_types)
        self.assertIn("Button", component_types)


if __name__ == "__main__":
    unittest.main()
~~~~

