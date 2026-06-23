# Modular RAG MCP Server

一个本地优先的模块化 RAG 项目，包含：

- 离线摄取：PDF -> Chunk -> Embedding -> Chroma + BM25
- 在线检索：Dense + Sparse + RRF + 可选 Rerank
- MCP Server：通过 stdio 暴露 `query_knowledge_hub` 等工具
- Dashboard：查看数据、摄取追踪、查询追踪、评估结果
- Evaluation：支持 custom retrieval 指标和 Ragas 语义评估

这份 README 的目标不是讲理念，而是让你能尽快把项目跑起来。

## 1. Quick Start

### 1.1 环境要求

- Windows PowerShell
- Python 3.11+
- 已创建项目虚拟环境 `.venv`

本项目后续所有命令都建议显式使用项目虚拟环境：

```powershell
.\.venv\Scripts\python.exe --version
```

### 1.2 安装依赖

如果你还没有安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

开发测试依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

如果 `.[dev]` 在你的环境里不可用，也可以单独安装：

```powershell
.\.venv\Scripts\python.exe -m pip install pytest pytest-asyncio pytest-cov pytest-mock ruff mypy
```

### 1.3 准备环境变量

复制 `.env.example` 为 `.env`：

```powershell
Copy-Item .env.example .env
```

然后填写你要使用的模型密钥。当前项目内置了这些文本 LLM profile：

- `minimax`
- `qwen`
- `deepseek`
- `deepseek_flash`
- `deepseek_chat`
- `openai`

Vision LLM profile：

- `qwen`
- `gemini_flash`

例如，如果你要使用 DeepSeek 文本模型和 Gemini Vision：

```dotenv
DEEPSEEK_LLM_API_KEY=your_key_here
GEMINI_VISION_API_KEY=your_key_here
```

### 1.4 检查配置是否可加载

```powershell
.\.venv\Scripts\python.exe main.py
```

如果成功，你会看到类似输出：

```text
Modular RAG MCP project skeleton is ready.
```

## 2. First Run

推荐按下面顺序走一遍：

1. 先 ingest 一份 PDF
2. 再跑一次 query
3. 然后打开 Dashboard
4. 最后再接 MCP Client 或做 evaluate

### 2.1 摄取 PDF

摄取单个 PDF：

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --path .\tests\fixtures\sample_documents\complex_technical_doc.pdf --collection default
```

摄取整个目录下的 PDF：

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --path .\tests\fixtures\sample_documents --collection default
```

强制重建，不走增量跳过：

```powershell
.\.venv\Scripts\python.exe scripts\ingest.py --path .\tests\fixtures\sample_documents\complex_technical_doc.pdf --collection default --force
```

你会看到类似输出：

```text
[INGEST] start total=1 collection=default force=False
[1/1][OK] ... chunks=... vectors=... images=... bm25_terms=...
[INGEST] done total=1 success=1 failed=0
```

### 2.2 执行查询

基础查询：

```powershell
.\.venv\Scripts\python.exe scripts\query.py --query "如何配置 Azure？"
```

查看中间过程：

```powershell
.\.venv\Scripts\python.exe scripts\query.py --query "如何配置 Azure？" --verbose
```

限定 collection：

```powershell
.\.venv\Scripts\python.exe scripts\query.py --query "hybrid search" --collection default
```

关闭 rerank：

```powershell
.\.venv\Scripts\python.exe scripts\query.py --query "hybrid search" --no-rerank
```

`--verbose` 下常见输出阶段：

- `dense`：向量检索召回结果
- `sparse`：BM25 关键词检索结果
- `fusion`：RRF 融合后的统一排序
- `rerank`：重排后的最终排序
- `fallback`：如果重排后端异常，是否回退到 fusion 顺序

### 2.3 启动 Dashboard

```powershell
.\.venv\Scripts\python.exe scripts\start_dashboard.py
```

默认地址：

- `http://localhost:8501`

## 3. settings.yaml 说明

主配置文件在：

- [config/settings.yaml](Q:\Code\PythonProject\MODULAR-RAG-MCP\config\settings.yaml)

配置加载代码在：

- [src/core/settings.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\src\core\settings.py)

### 3.1 `llm`

文本模型配置。当前采用 `profile + profiles` 的方式切换。

最常改的字段：

- `llm.profile`
- `llm.timeout`
- `llm.max_retries`

例子：

```yaml
llm:
  profile: deepseek_flash
```

表示文本 LLM 改用 `llm.profiles.deepseek_flash` 这套 provider/model/base_url/api_key。

### 3.2 `embedding`

查询和摄取阶段使用的向量模型。

当前默认：

- `provider: huggingface_local`
- `model: data/models/all-MiniLM-L6-v2`

这表示项目优先使用本地 embedding 模型，避免运行时依赖外网。

### 3.3 `vector_store`

向量库存储配置。

当前默认：

```yaml
vector_store:
  provider: chroma
  persist_dir: data/db/chroma
```

这里的 `persist_dir` 是 Chroma 持久化目录。

### 3.4 `retrieval`

检索参数。

- `top_k`：默认最终返回多少条
- `sparse_top_k`：BM25 路线先召回多少条

### 3.5 `rerank`

重排配置。

- `enabled`
- `provider`
- `top_m`
- `timeout`

当前支持的典型值：

- `provider: none`
- `provider: cross_encoder`
- `provider: llm`

### 3.6 `vision_llm`

图片描述模型。用于 ingest 过程中对图片做 caption，增强检索。

如果你暂时不需要图片能力，可以关掉：

```yaml
vision_llm:
  enabled: false
```

### 3.7 `evaluation`

评估配置。

关键字段：

- `enabled`
- `provider`
- `backends`
- `golden_test_set`
- `evaluation.ragas.llm_profile`

例如：

```yaml
evaluation:
  provider: ragas
  enabled: false
  backends:
    - ragas
    - custom
  golden_test_set: tests/fixtures/golden_test_set.json
  ragas:
    llm_profile: deepseek_chat
```

### 3.8 `observability`

追踪日志配置。

```yaml
observability:
  log_level: INFO
  trace_file: logs/traces.jsonl
```

`logs/traces.jsonl` 很重要：

- ingest 追踪页读它
- query 追踪页也读它
- 服务重启后旧记录仍会保留，新的记录继续追加

### 3.9 `dashboard`

Dashboard 自身配置。

- `enabled`
- `port`
- `traces_dir`
- `auto_refresh`
- `refresh_interval`

### 3.10 `ingestion`

摄取阶段配置。

关键字段：

- `splitter`
- `chunk_size`
- `chunk_overlap`
- `batch_size`
- `chunk_refiner.use_llm`
- `metadata_enricher.use_llm`

如果你想先跑一个更稳定、更少外部依赖的版本，可以先把这两个关掉：

```yaml
ingestion:
  chunk_refiner:
    use_llm: false
  metadata_enricher:
    use_llm: false
```

## 4. MCP 使用

当前 MCP Server 入口：

- [src/mcp_server/server.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\src\mcp_server\server.py)

协议处理：

- [src/mcp_server/protocol_handler.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\src\mcp_server\protocol_handler.py)

当前已暴露工具：

- `query_knowledge_hub`
- `list_collections`
- `get_document_summary`

### 4.1 手工启动 MCP Server

```powershell
.\.venv\Scripts\python.exe -m mcp_server.server
```

它使用 stdio 通信，不是 HTTP 服务。正常情况下它是被 MCP Client 拉起，而不是你手工在终端里直接交互。

### 4.2 GitHub Copilot `mcp.json` 示例

下面给一个本地项目常见写法。你需要把路径改成你自己的绝对路径。

```json
{
  "servers": {
    "modular-rag-mcp": {
      "command": "Q:\\Code\\PythonProject\\MODULAR-RAG-MCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "Q:\\Code\\PythonProject\\MODULAR-RAG-MCP"
    }
  }
}
```

关键点：

- `command` 用项目 `.venv` 里的 Python
- `args` 用 `-m mcp_server.server`
- `cwd` 指向项目根目录，这样 `config/settings.yaml` 和 `data/` 相对路径才会对

### 4.3 Claude Desktop `claude_desktop_config.json` 示例

```json
{
  "mcpServers": {
    "modular-rag-mcp": {
      "command": "Q:\\Code\\PythonProject\\MODULAR-RAG-MCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "Q:\\Code\\PythonProject\\MODULAR-RAG-MCP"
    }
  }
}
```

### 4.4 这三个 MCP Tool 是干什么的

`query_knowledge_hub`

- 输入 `query`
- 可选 `top_k`
- 可选 `collection`
- 返回相关片段、结构化结果、citations、trace_id

`list_collections`

- 列出当前可用集合
- 适合先确认数据有没有被摄取进去

`get_document_summary`

- 按 `doc_id` 查询文档标题、摘要、标签

## 5. Dashboard 使用

Dashboard 入口：

- [src/observability/dashboard/app.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\src\observability\dashboard\app.py)

启动命令：

```powershell
.\.venv\Scripts\python.exe scripts\start_dashboard.py
```

### 5.1 六个页面分别做什么

1. `Overview`
   展示系统配置、集合统计、整体状态。

2. `Data Browser`
   浏览文档、chunk、图片和 metadata。

3. `Ingestion Manager`
   上传 PDF、触发摄取、查看实时进度、删除文档。

4. `Ingestion Traces`
   查看每次 ingest 的阶段详情，例如 load/split/transform/embed/upsert。

5. `Query Traces`
   查看每次 query 的处理过程，例如 dense/sparse/fusion/rerank。

6. `Evaluation Panel`
   运行评估并查看 hit_rate、mrr、Ragas 指标。

### 5.2 Dashboard 正常显示数据的前提

要想页面不是空的，至少要满足：

1. 你已经成功跑过 `scripts/ingest.py`
2. `observability.trace_file` 指向的 `logs/traces.jsonl` 存在并持续追加
3. Dashboard 启动时读取的是同一套 `config/settings.yaml`、`data/`、`logs/`

如果你在 Dashboard 上传 PDF，原文件会先被复制到项目临时上传目录，再进入正式摄取流程。这是正常行为，不影响最终索引结果。

## 6. Evaluation

评估脚本：

- [scripts/evaluate.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\scripts\evaluate.py)

黄金测试集：

- [tests/fixtures/golden_test_set.json](Q:\Code\PythonProject\MODULAR-RAG-MCP\tests\fixtures\golden_test_set.json)

### 6.1 只跑 retrieval 指标

```powershell
.\.venv\Scripts\python.exe scripts\evaluate.py --backend custom
```

这会计算：

- `hit_rate`
- `mrr`

### 6.2 跑真实 Ragas

```powershell
.\.venv\Scripts\python.exe scripts\evaluate.py --backend ragas
```

典型输出包括：

- `faithfulness`
- `answer_relevancy`
- `context_precision`

注意：

- `Ragas` 需要真实可用的 LLM 配置
- `golden_test_set.json` 需要有可用的测试集内容
- 第一次跑可能比较慢

## 7. Test Commands

### 7.1 全量测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### 7.2 常用分层测试

单元测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\unit
```

集成测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\integration
```

端到端测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\e2e
```

### 7.3 关键专项测试

MCP Client E2E：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\e2e\test_mcp_client.py
```

Dashboard Smoke：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\e2e\test_dashboard_smoke.py
```

Recall 回归：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\e2e\test_recall.py
```

真实 Ragas 评估相关：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\unit\test_ragas_evaluator.py
```

## 8. Troubleshooting

### 8.1 `Settings file not found`

通常是工作目录不对。

解决办法：

- 在项目根目录执行命令
- MCP 配置里显式写 `cwd`
- Dashboard/MCP/脚本都优先使用项目 `.venv`

### 8.2 `Missing required environment variable`

说明 `.env` 里缺少对应 key，或者 `settings.yaml` 选中的 profile 需要的环境变量没有填。

先检查：

- `.env` 是否存在
- 变量名是否和 `.env.example` 一致
- `llm.profile` / `vision_llm.profile` 是否选到了你实际配置过的 profile

### 8.3 `未找到相关文档，请先运行 ingest.py 摄取数据`

通常是这几种情况：

- 你还没 ingest
- ingest 写入的 collection 和 query 时指定的 collection 不一致
- 当前读取的 `data/db/chroma` 不是你之前 ingest 的那套目录

### 8.4 Dashboard 页面是空的

重点检查：

- [config/settings.yaml](Q:\Code\PythonProject\MODULAR-RAG-MCP\config\settings.yaml) 中的 `observability.trace_file`
- `logs/traces.jsonl` 是否真的在追加
- Dashboard 启动时使用的项目根目录是否正确

### 8.5 `traces.jsonl` 没有生成

常见原因：

- 还没有真正执行过 ingest 或 query
- 脚本运行到了别的工作目录
- `observability.trace_file` 配到了不存在或你没注意的目录

当前实现中：

- `scripts/query.py` 结束时会持久化 query trace
- MCP 的 `query_knowledge_hub` 结束时也会持久化 query trace
- Ingestion pipeline 结束时会持久化 ingestion trace

### 8.6 `list_collections` 看不到预期集合

当前 `list_collections` 是按 `data/documents/` 下的目录做轻量扫描，不是直接读取向量库的全部 collection 元数据。

如果你主要想确认向量检索是否可用，优先：

1. 先跑 `scripts/query.py`
2. 再看 Dashboard 的 Data Browser / Query Traces

### 8.7 Ragas 很慢或没有输出

先区分两件事：

1. custom 检索评估是否正常
2. 真实 Ragas 模型调用是否正常

建议先跑：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate.py --backend custom
```

如果 custom 正常、ragas 很慢，再检查：

- `evaluation.ragas.llm_profile`
- 该 profile 的 API key / base_url
- 模型是否适合结构化评估输出
- `golden_test_set.json` 是否包含真实可用的数据

## 9. Project Entry Points

最常用入口如下：

- [main.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\main.py)
- [scripts/ingest.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\scripts\ingest.py)
- [scripts/query.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\scripts\query.py)
- [scripts/evaluate.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\scripts\evaluate.py)
- [scripts/start_dashboard.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\scripts\start_dashboard.py)
- [src/mcp_server/server.py](Q:\Code\PythonProject\MODULAR-RAG-MCP\src\mcp_server\server.py)

如果你是从 `clean-start` 分支一路跟着实现过来的，下一步通常就是继续补 I4 的契约一致性测试和 I5 的全链路验收。
