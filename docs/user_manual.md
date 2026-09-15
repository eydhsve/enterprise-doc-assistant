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
