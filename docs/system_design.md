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
