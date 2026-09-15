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
