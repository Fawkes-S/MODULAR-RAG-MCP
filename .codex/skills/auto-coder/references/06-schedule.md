## 6. 椤圭洰鎺掓湡

> **鎺掓湡鍘熷垯锛堜弗鏍煎榻愭湰 DEV_SPEC 鐨勬灦鏋勫垎灞備笌鐩綍缁撴瀯锛?*
> 
> - **鍙寜鏈枃妗ｈ璁¤惤鍦?*锛氫互绗?5.2 鑺傜洰褰曟爲涓衡€滀氦浠樻竻鍗曗€濓紝姣忎竴姝ラ兘瑕佸湪鏂囦欢绯荤粺涓婁骇鐢熷彲瑙佸彉鍖栥€?
> - **1 灏忔椂涓€涓彲楠屾敹澧為噺**锛氭瘡涓皬闃舵锛堚増1h锛夐兘蹇呴』鍚屾椂缁欏嚭鈥滈獙鏀舵爣鍑?+ 娴嬭瘯鏂规硶鈥濓紝灏介噺鍋氬埌 TDD銆?
> - **鍏堟墦閫氫富闂幆锛屽啀琛ラ綈榛樿瀹炵幇**锛氫紭鍏堝仛鈥滃彲璺戦€氱殑绔埌绔矾寰勶紙Ingestion 鈫?Retrieval 鈫?MCP Tool锛夆€濓紝骞跺湪 Libs 灞傝ˉ榻愬彲杩愯鐨勯粯璁ゅ悗绔疄鐜帮紝閬垮厤鍑虹幇鈥滃彧鏈夋帴鍙ｆ病鏈夊疄鐜扳€濈殑绌鸿浆銆?
> - **澶栭儴渚濊禆鍙浛鎹?鍙?Mock**锛歀LM/Embedding/Vision/VectorStore 鐨勭湡瀹炶皟鐢ㄥ湪鍗曞厓娴嬭瘯涓竴寰嬬敤 Fake/Mock锛岄泦鎴愭祴璇曞啀寮€鐪熷疄鍚庣锛堝彲閫夛級銆?

### 闃舵鎬昏锛堝ぇ闃舵 鈫?鐩殑锛?

1. **闃舵 A锛氬伐绋嬮鏋朵笌娴嬭瘯鍩哄骇**
   - 鐩殑锛氬缓绔嬪彲杩愯銆佸彲閰嶇疆銆佸彲娴嬭瘯鐨勫伐绋嬮鏋讹紱鍚庣画鎵€鏈夋ā鍧楅兘鑳戒互 TDD 鏂瑰紡钀藉湴銆?
2. **闃舵 B锛歀ibs 鍙彃鎷斿眰锛團actory + Base 鎺ュ彛 + 榛樿鍙繍琛屽疄鐜帮級**
  - 鐩殑锛氭妸鈥滃彲鏇挎崲鈥濆彉鎴愪唬鐮佷簨瀹烇紱骞惰ˉ榻愬彲杩愯鐨勯粯璁ゅ悗绔疄鐜帮紝纭繚 Core / Ingestion 涓嶄粎鈥滃彲缂栬瘧鈥濓紝杩樺彲鍦ㄧ湡瀹炵幆澧冭窇閫氥€?
3. **闃舵 C锛欼ngestion Pipeline锛圥DF鈫扢D鈫扖hunk鈫扙mbedding鈫扷psert锛?*
  - 鐩殑锛氱绾挎憚鍙栭摼璺窇閫氾紝鑳芥妸鏍蜂緥鏂囨。鍐欏叆鍚戦噺搴?BM25 绱㈠紩骞舵敮鎸佸閲忋€?
4. **闃舵 D锛歊etrieval锛圖ense + Sparse + RRF + 鍙€?Rerank锛?*
  - 鐩殑锛氬湪绾挎煡璇㈤摼璺窇閫氾紝寰楀埌 Top-K chunks锛堝惈寮曠敤淇℃伅锛夛紝骞跺叿澶囩ǔ瀹氬洖閫€绛栫暐銆?
5. **闃舵 E锛歁CP Server 灞備笌 Tools 钀藉湴**
   - 鐩殑锛氭寜 MCP 鏍囧噯鏆撮湶 tools锛岃 Copilot/Claude 鍙洿鎺ヨ皟鐢ㄦ煡璇㈣兘鍔涖€?
6. **闃舵 F锛歍race 鍩虹璁炬柦涓庢墦鐐?*
   - 鐩殑锛氬寮?TraceContext锛屽疄鐜扮粨鏋勫寲鏃ュ織鎸佷箙鍖栵紝鍦?Ingestion + Query 鍙岄摼璺墦鐐癸紝娣诲姞 Pipeline 杩涘害鍥炶皟銆?
7. **闃舵 G锛氬彲瑙嗗寲绠＄悊骞冲彴 Dashboard**
   - 鐩殑锛氭惌寤?Streamlit 鍏〉闈㈢鐞嗗钩鍙帮紙绯荤粺鎬昏 / 鏁版嵁娴忚 / Ingestion 绠＄悊 / Ingestion 杩借釜 / Query 杩借釜 / 璇勪及鍗犱綅锛夛紝瀹炵幇 DocumentManager 璺ㄥ瓨鍌ㄥ崗璋冦€?
8. **闃舵 H锛氳瘎浼颁綋绯?*
   - 鐩殑锛氬疄鐜?RagasEvaluator + CompositeEvaluator + EvalRunner锛屽惎鐢ㄨ瘎浼伴潰鏉块〉闈紝寤虹珛 golden test set 鍥炲綊鍩虹嚎銆?
9. **闃舵 I锛氱鍒扮楠屾敹涓庢枃妗ｆ敹鍙?*
   - 鐩殑锛氳ˉ榻?E2E 娴嬭瘯锛圡CP Client 妯℃嫙 + Dashboard 鍐掔儫锛夛紝瀹屽杽 README锛屽叏閾捐矾楠屾敹锛岀‘淇濃€滃紑绠卞嵆鐢?+ 鍙鐜扳€濄€?


---

### 馃搳 杩涘害璺熻釜琛?(Progress Tracking)

> **鐘舵€佽鏄?*锛歚[ ]` 鏈紑濮?| `[~]` 杩涜涓?| `[x]` 宸插畬鎴?
> 
> **鏇存柊鏃堕棿**锛氭瘡瀹屾垚涓€涓瓙浠诲姟鍚庢洿鏂板搴旂姸鎬?

#### 闃舵 A锛氬伐绋嬮鏋朵笌娴嬭瘯鍩哄骇

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| A1 | 鍒濆鍖栫洰褰曟爲涓庢渶灏忓彲杩愯鍏ュ彛 | [x] | 2026-03-20 | compileall/import checks passed |
| A2 | 寮曞叆 pytest 骞跺缓绔嬫祴璇曠洰褰曠害瀹?| [x] | 2026-03-20 | pytest smoke and full run passed |
| A3 | 閰嶇疆鍔犺浇涓庢牎楠岋紙Settings锛?| [x] | 2026-03-20 | settings loader/validation + tests passed |

#### 闃舵 B锛歀ibs 鍙彃鎷斿眰

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| B1 | LLM 鎶借薄鎺ュ彛涓庡伐鍘?| [x] | 2026-03-20 | BaseLLM + LLMFactory + fake-provider tests passed |
| B2 | Embedding 鎶借薄鎺ュ彛涓庡伐鍘?| [x] | 2026-03-20 | BaseEmbedding + EmbeddingFactory + stable fake-vector tests passed |
| B3 | Splitter 鎶借薄鎺ュ彛涓庡伐鍘?| [x] | 2026-03-20 | BaseSplitter + SplitterFactory + provider routing tests passed |
| B4 | VectorStore 鎶借薄鎺ュ彛涓庡伐鍘?| [x] | 2026-03-20 | BaseVectorStore + VectorStoreFactory + contract tests passed |
| B5 | Reranker 鎶借薄鎺ュ彛涓庡伐鍘傦紙鍚?None 鍥為€€锛?| [x] | 2026-03-20 | BaseReranker + NoneReranker + RerankerFactory + tests passed |
| B6 | Evaluator 鎶借薄鎺ュ彛涓庡伐鍘?| [x] | 2026-03-20 | BaseEvaluator + EvaluatorFactory + CustomEvaluator + tests passed |
| B7.1 | OpenAI-Compatible LLM 瀹炵幇 | [x] | 2026-03-22 | OpenAI/Azure/DeepSeek providers + mock-http smoke tests passed |
| B7.2 | Ollama LLM 瀹炵幇 | [x] | 2026-03-22 | OllamaLLM + factory routing + mock-http tests passed |
| B7.3 | OpenAI & Azure Embedding 瀹炵幇 | [x] | 2026-03-22 | OpenAIEmbedding/AzureEmbedding + factory routing + mock-http tests passed |
| B7.4 | Ollama Embedding 瀹炵幇 | [x] | 2026-03-24 | OllamaEmbedding + factory routing + mock-http tests passed |
| B7.5 | Recursive Splitter 榛樿瀹炵幇 | [x] | 2026-03-24 | RecursiveSplitter + factory routing + markdown-structure tests passed |
| B7.6 | ChromaStore 榛樿瀹炵幇 | [x] | 2026-03-24 | ChromaStore + factory routing + roundtrip integration tests passed锛堝惈鍙楅檺鐜鑷姩闄嶇骇锛?|
| B7.7 | LLM Reranker 瀹炵幇 | [x] | 2026-03-24 | LLMReranker + prompt loading + fallback signal + schema validation + tests passed |
| B7.8 | Cross-Encoder Reranker 瀹炵幇 | [x] | 2026-03-25 | CrossEncoderReranker + fallback signal + factory routing + mock-scorer tests passed |
| B8 | Vision LLM 鎶借薄鎺ュ彛涓庡伐鍘傞泦鎴?| [x] | 2026-03-25 | BaseVisionLLM + LLMFactory.create_vision_llm + routing tests passed |
| B9 | Azure Vision LLM 瀹炵幇 | [x] | 2026-03-25 | AzureVisionLLM + image path/base64 + compression hook + error-code tests passed |
| B9.1 | DashScope Vision LLM锛圦wen3.5-Plus锛夊疄鐜?| [x] | 2026-03-25 | DashScopeVisionLLM + factory routing + image path/base64 + compression/error tests passed |

#### 闃舵 C锛欼ngestion Pipeline MVP

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| C1 | 瀹氫箟鏍稿績鏁版嵁绫诲瀷/濂戠害锛圖ocument/Chunk/ChunkRecord锛?| [x] | 2026-03-26 | core.types contracts + metadata/images validation + serialization tests passed |
| C2 | 鏂囦欢瀹屾暣鎬ф鏌ワ紙SHA256锛?| [x] | 2026-03-26 | SQLiteIntegrityChecker + WAL + skip鍒ゅ畾 + 骞跺彂鍐欏叆 tests passed |
| C3 | Loader 鎶借薄鍩虹被涓?PDF Loader | [x] | 2026-03-26 | BaseLoader + PdfLoader + image extraction/placeholder + degrade path tests passed |
| C4 | Splitter 闆嗘垚锛堣皟鐢?Libs锛?| [x] | 2026-03-27 | DocumentChunker 閫傞厤灞?+ 鍥剧墖鎸夐渶鍒嗗彂 + 閰嶇疆椹卞姩鍒囧垎 + 鍚堝悓娴嬭瘯閫氳繃 |
| C5 | Transform 鍩虹被 + ChunkRefiner | [x] | 2026-03-29 | BaseTransform + ChunkRefiner(rule+LLM+fallback) + TraceContext(min) + 27 unit tests passed; real-LLM integration tests added (env key required) |
| C6 | MetadataEnricher | [x] | 2026-03-30 | MetadataEnricher(rule+LLM+fallback) + trace缁熻 + contract tests(鍚湡瀹濴LM鐢ㄤ緥) |
| C7 | ImageCaptioner | [x] | 2026-03-30 | ImageCaptioner + fallback + prompt + tests passed |
| C8 | DenseEncoder | [x] | 2026-03-30 | DenseEncoder(batch encode + contract checks + tests passed) |
| C9 | SparseEncoder | [x] | 2026-03-31 | SparseEncoder(BM25 term weights + empty-text contract + tests passed) |
| C10 | BatchProcessor | [x] | 2026-04-03 | BatchProcessor(batch split + dense/sparse orchestration + per-batch timing + tests passed) |
| C11 | BM25Indexer锛堝€掓帓绱㈠紩+IDF璁＄畻锛?| [x] | 2026-04-03 | BM25Indexer(build/load/query + IDF formula + incremental/rebuild + tests passed) |
| C12 | VectorUpserter锛堝箓绛塽psert锛?| [x] | 2026-04-03 | VectorUpserter(stable id + idempotent upsert + trace stage) + tests passed |
| C13 | ImageStorage锛堝浘鐗囧瓨鍌?SQLite绱㈠紩锛?| [x] | 2026-04-04 | ImageStorage(file save + SQLite index + WAL + collection/doc_hash filters) + tests passed |
| C14 | Pipeline 缂栨帓锛圡VP 涓茶捣鏉ワ級 | [x] | 2026-04-04 | IngestionPipeline(end-to-end orchestration + stage error wrapping + incremental skip/force) + integration tests passed |
| C15 | 鑴氭湰鍏ュ彛 ingest.py | [x] | 2026-04-04 | scripts/ingest.py(cli path/collection/force + dir batch pdf) + tests/e2e/test_data_ingestion.py passed |

#### 闃舵 D锛歊etrieval MVP

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| D1 | QueryProcessor锛堝叧閿瘝鎻愬彇 + filters锛?| [x] | 2026-04-04 | QueryProcessor(瑙勫垯鍒嗚瘝+鍋滅敤璇?鍐呰仈filters瑙ｆ瀽) + tests/unit/test_query_processor.py passed |
| D2 | DenseRetriever锛堣皟鐢?VectorStore.query锛?| [x] | 2026-04-05 | RetrievalResult + DenseRetriever(embed->query缂栨帓) + tests/unit/test_dense_retriever.py passed |
| D3 | SparseRetriever锛圔M25 鏌ヨ锛?| [x] | 2026-05-27 | Base/Chroma get_by_ids + SparseRetriever(BM25->姝ｆ枃鍥炲～) + tests/unit/test_sparse_retriever.py passed |
| D4 | RRF Fusion | [x] | 2026-05-29 | RRFFusion(deterministic + configurable k) + tests/unit/test_fusion_rrf.py passed |
| D5 | HybridSearch 缂栨帓 | [x] | 2026-05-30 | HybridSearch(query->dense/sparse->RRF->post-filter) + tests/integration/test_hybrid_search.py passed |
| D6 | Reranker锛圕ore 灞傜紪鎺?+ Fallback锛?| [x] | 2026-05-31 | Core Reranker(fallback=true + reason) + tests/unit/test_reranker_fallback.py passed |
| D7 | 鑴氭湰鍏ュ彛 query.py锛堟煡璇㈠彲鐢級 | [x] | 2026-05-31 | scripts/query.py(cli + verbose + no-rerank + friendly-empty) verified |

#### 闃舵 E锛歁CP Server 灞備笌 Tools

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| E1 | MCP Server 鍏ュ彛涓?Stdio 绾︽潫 | [x] | 2026-06-05 | minimal stdio JSON-RPC server + initialize integration test passed |
| E2 | Protocol Handler 鍗忚瑙ｆ瀽涓庤兘鍔涘崗鍟?| [x] | 2026-06-06 | ProtocolHandler(initialize/tools/list/tools/call + JSON-RPC errors) + tests/unit/test_protocol_handler.py passed |
| E3 | query_knowledge_hub Tool | [x] | 2026-06-06 | query tool + response builder + citations + mcp integration tests passed |
| E4 | list_collections Tool | [x] | 2026-06-06 | list_collections directory scan tool + unit tests passed |
| E5 | get_document_summary Tool | [x] | 2026-06-06 | cache-backed summary tool + MCP integration tests passed |
| E6 | 澶氭ā鎬佽繑鍥炵粍瑁咃紙Text + Image锛?| [x] | 2026-06-07 | multimodal assembler + MCP image content integration test passed |

#### 闃舵 F锛歍race 鍩虹璁炬柦涓庢墦鐐?

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| F1 | TraceContext 澧炲己锛坒inish + 鑰楁椂缁熻 + trace_type锛?| [x] | 2026-06-07 | TraceContext(finish/elapsed/trace_type/to_dict) + tests/unit/test_trace_context.py passed |
| F2 | 缁撴瀯鍖栨棩蹇?logger锛圝SON Lines锛?| [x] | 2026-06-07 | JSONL logger + TraceCollector + tests/unit/test_jsonl_logger.py passed |
| F3 | 鍦?Query 閾捐矾鎵撶偣 | [x] | 2026-06-07 | query trace stages/method-provider fields + integration/unit tests passed |
| F4 | 鍦?Ingestion 閾捐矾鎵撶偣 | [x] | 2026-06-08 | ingestion trace stages/method-provider fields + integration tests passed |
| F5 | Pipeline 杩涘害鍥炶皟 (on_progress) | [x] | 2026-06-09 | pipeline on_progress callback + unit tests passed |

#### 闃舵 G锛氬彲瑙嗗寲绠＄悊骞冲彴 Dashboard

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| G1 | Dashboard 鍩虹鏋舵瀯涓庣郴缁熸€昏椤?| [x] | 2026-06-09 | Streamlit澶氶〉闈㈤鏋?+ Overview閰嶇疆/缁熻椤?+ start_dashboard鑴氭湰 + tests passed |
| G2 | DocumentManager 瀹炵幇 | [x] | 2026-06-09 | DocumentManager(list/detail/delete/stats) + Chroma metadata read/delete + tests passed |
| G3 | 鏁版嵁娴忚鍣ㄩ〉闈?| [x] | 2026-06-10 | data_browser 椤甸潰 + DataService 鏂囨。/chunk/鍥剧墖娴忚 + dashboard tests passed |
| G4 | Ingestion 绠＄悊椤甸潰 | [x] | 2026-06-10 | ingestion_manager 椤甸潰 + PDF 涓婁紶鎽勫彇 + on_progress 瀹炴椂杩涘害 + 鏂囨。鍒犻櫎 + dashboard tests passed |
| G5 | Ingestion 杩借釜椤甸潰 | [x] | 2026-06-11 | ingestion_traces 椤甸潰 + TraceService(JSONL瑙ｆ瀽/闃舵鑱氬悎) + dashboard tests passed |
| G6 | Query 杩借釜椤甸潰 | [x] | 2026-06-12 | query_traces 椤甸潰 + query trace鎸佷箙鍖?鍊欓€夐瑙?+ dashboard tests passed |

#### 闃舵 H锛氳瘎浼颁綋绯?

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| H1 | RagasEvaluator 瀹炵幇 | [x] | 2026-06-14 | RagasEvaluator(lazy import + standardized metrics) + tests/unit/test_ragas_evaluator.py passed |
| H2 | CompositeEvaluator 瀹炵幇 | [x] | 2026-06-14 | CompositeEvaluator(parallel merge + evaluation.backends routing) + tests/unit/test_composite_evaluator.py passed |
| H3 | EvalRunner + Golden Test Set | [x] | 2026-06-15 | EvalRunner(golden set + retrieval metrics + evaluator adaptation) + scripts/evaluate.py + unit tests passed |
| H4 | 璇勪及闈㈡澘椤甸潰 | [x] | 2026-06-15 | evaluation_panel 椤甸潰 + Dashboard 鎺ュ叆 + unit tests passed |
| H5 | Recall 鍥炲綊娴嬭瘯锛圗2E锛?| [x] | 2026-06-23 | tests/e2e/test_recall.py + H5 evaluation regression suite passed |

#### 闃舵 I锛氱鍒扮楠屾敹涓庢枃妗ｆ敹鍙?

| 浠诲姟缂栧彿 | 浠诲姟鍚嶇О | 鐘舵€?| 瀹屾垚鏃ユ湡 | 澶囨敞 |
|---------|---------|------|---------|------|
| I1 | E2E锛歁CP Client 渚ц皟鐢ㄦā鎷?| [x] | 2026-06-23 | tests/e2e/test_mcp_client.py + real ingest + stdio MCP client flow passed |
| I2 | E2E锛欴ashboard 鍐掔儫娴嬭瘯 | [x] | 2026-06-23 | tests/e2e/test_dashboard_smoke.py + Streamlit AppTest six-page smoke passed |
| I3 | 瀹屽杽 README锛堣繍琛岃鏄?+ MCP + Dashboard锛?| [ ] | | |
| I4 | 娓呯悊鎺ュ彛涓€鑷存€э紙濂戠害娴嬭瘯琛ラ綈锛?| [ ] | | |
| I5 | 鍏ㄩ摼璺?E2E 楠屾敹 | [ ] | | |

---

### 馃搱 鎬讳綋杩涘害

| 闃舵 | 鎬讳换鍔℃暟 | 宸插畬鎴?| 杩涘害 |
|------|---------|--------|------|
| 闃舵 A | 3 | 0 | 0% |
| 闃舵 B | 16 | 0 | 0% |
| 闃舵 C | 15 | 0 | 0% |
| 闃舵 D | 7 | 0 | 0% |
| 闃舵 E | 6 | 0 | 0% |
| 闃舵 F | 5 | 0 | 0% |
| 闃舵 G | 6 | 0 | 0% |
| 闃舵 H | 5 | 0 | 0% |
| 闃舵 I | 5 | 0 | 0% |
| **鎬昏** | **68** | **0** | **0%** |


---

## 闃舵 A锛氬伐绋嬮鏋朵笌娴嬭瘯鍩哄骇锛堢洰鏍囷細鍏堝彲瀵煎叆锛屽啀鍙祴璇曪級

### A1锛氬垵濮嬪寲鐩綍鏍戜笌鏈€灏忓彲杩愯鍏ュ彛
- **鐩爣**锛氬湪 repo 鏍圭洰褰曞垱寤虹 5.2 鑺傛墍杩扮洰褰曢鏋朵笌绌烘ā鍧楁枃浠讹紙鍙?import锛夈€?
- **淇敼鏂囦欢**锛?
  - `main.py`
  - `pyproject.toml`
  - `README.md`
  - `.gitignore`锛圥ython 椤圭洰鏍囧噯蹇界暐瑙勫垯锛歚__pycache__`銆乣.venv`銆乣.env`銆乣*.pyc`銆両DE 閰嶇疆绛夛級
  - `src/**/__init__.py`锛堟寜鐩綍鏍戣ˉ榻愶級
  - `config/settings.yaml`锛堟渶灏忓彲瑙ｆ瀽閰嶇疆锛?
  - `config/prompts/image_captioning.txt`锛堝彲鍏堟斁鍗犱綅鍐呭锛屽悗缁樁娈佃ˉ鍏?Prompt锛?
  - `config/prompts/chunk_refinement.txt`锛堝彲鍏堟斁鍗犱綅鍐呭锛屽悗缁樁娈佃ˉ鍏?Prompt锛?
  - `config/prompts/rerank.txt`锛堝彲鍏堟斁鍗犱綅鍐呭锛屽悗缁樁娈佃ˉ鍏?Prompt锛?
- **瀹炵幇绫?鍑芥暟**锛氭棤锛堜粎楠ㄦ灦锛夈€?
- **瀹炵幇绫?鍑芥暟**锛氭棤锛堜粎楠ㄦ灦锛屼笉瀹炵幇涓氬姟閫昏緫锛夈€?
- **瀹炵幇绫?鍑芥暟**锛氫负褰撳墠椤圭洰鍒涘缓涓€涓櫄鎷熺幆澧冩ā鍧椼€?
 - **楠屾敹鏍囧噯**锛?
  - 鐩綍缁撴瀯涓?DEV_SPEC 5.2 涓€鑷达紙鑷冲皯鎶婂搴旂洰褰曞垱寤哄嚭鏉ワ級銆?
  - `config/prompts/` 鐩綍瀛樺湪锛屼笖涓変釜 prompt 鏂囦欢鍙璇诲彇锛堝嵆浣垮彧鏄崰浣嶆枃鏈級銆?
  - 鑳藉鍏ュ叧閿《灞傚寘锛堜笌鐩綍缁撴瀯涓€涓€瀵瑰簲锛夛細
    - `python -c "import mcp_server; import core; import ingestion; import libs; import observability"`
  - 鍙互鍚姩铏氭嫙鐜妯″潡
- **娴嬭瘯鏂规硶**锛氳繍琛?`python -m compileall src`锛堜粎鍋氳娉?鍙鍏ユ€ф鏌ワ紱pytest 鍩哄骇鍦?A2 寤虹珛锛夈€?

### A2锛氬紩鍏?pytest 骞跺缓绔嬫祴璇曠洰褰曠害瀹?
- **鐩爣**锛氬缓绔?`tests/unit|integration|e2e|fixtures` 鐩綍涓?pytest 杩愯鍩哄骇銆?
- **淇敼鏂囦欢**锛?
  - `pyproject.toml`锛堟坊鍔?pytest 閰嶇疆锛歵estpaths銆乵arkers 绛夛級
  - `tests/unit/test_smoke_imports.py`
  - `tests/fixtures/sample_documents/`锛堟斁 1 涓渶灏忔牱渚嬫枃妗ｅ崰浣嶏級
- **瀹炵幇绫?鍑芥暟**锛氭棤銆?
- **瀹炵幇绫?鍑芥暟**锛氭棤锛堟柊澧炵殑鏄祴璇曟枃浠朵笌 pytest 閰嶇疆锛夈€?
- **楠屾敹鏍囧噯**锛?
  - `pytest -q` 鍙繍琛屽苟閫氳繃銆?
  - 鑷冲皯 1 涓啋鐑熸祴璇曪紙渚嬪 `tests/unit/test_smoke_imports.py` 鍙仛鍏抽敭鍖?import 鏍￠獙锛夈€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_smoke_imports.py`銆?

### A3锛氶厤缃姞杞戒笌鏍￠獙锛圫ettings锛?
- **鐩爣**锛氬疄鐜拌鍙?`config/settings.yaml` 鐨勯厤缃姞杞藉櫒锛屽苟鍦ㄥ惎鍔ㄦ椂鏍￠獙鍏抽敭瀛楁瀛樺湪銆?
- **淇敼鏂囦欢**锛?
  - `main.py`锛堝惎鍔ㄦ椂璋冪敤 `load_settings()`锛岀己瀛楁鐩存帴 fail-fast 閫€鍑猴級
  - `src/observability/logger.py`锛堝厛鍗犱綅锛氭彁渚?get_logger锛宻tderr 杈撳嚭锛?
  - `src/core/settings.py`锛堟柊澧烇細闆嗕腑鏀?Settings 鏁版嵁缁撴瀯涓庡姞杞?鏍￠獙閫昏緫锛?
  - `config/settings.yaml`锛堣ˉ榻愬瓧娈碉細llm/embedding/vector_store/retrieval/rerank/evaluation/observability锛?
  - `tests/unit/test_config_loading.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `Settings`锛坉ataclass锛氬彧鍋氱粨鏋勪笌鏈€灏忔牎楠岋紱涓嶅湪杩欓噷鍋氫换浣曠綉缁?IO 鐨勨€滀笟鍔″垵濮嬪寲鈥濓級
  - `load_settings(path: str) -> Settings`锛堣鍙?YAML -> 瑙ｆ瀽涓?Settings -> 鏍￠獙蹇呭～瀛楁锛?
  - `validate_settings(settings: Settings) -> None`锛堟妸鈥滃繀濉瓧娈垫鏌モ€濋泦涓寲锛岄敊璇俊鎭寘鍚瓧娈佃矾寰勶紝渚嬪 `embedding.provider`锛?
- **楠屾敹鏍囧噯**锛?
  - `main.py` 鍚姩鏃惰兘鎴愬姛鍔犺浇 `config/settings.yaml` 骞舵嬁鍒?`Settings` 瀵硅薄銆?
  - 鍒犻櫎/缂哄け鍏抽敭瀛楁鏃讹紙渚嬪 `embedding.provider`锛夛紝鍚姩鎴?`load_settings()` 鎶涘嚭鈥滃彲璇婚敊璇€濓紙鏄庣‘鎸囧嚭缂虹殑鏄摢涓瓧娈碉級銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_config_loading.py`銆?

---

## 闃舵 B锛歀ibs 鍙彃鎷斿眰锛堢洰鏍囷細Factory 鍙伐浣滐紝涓旇嚦灏戞湁鈥滈粯璁ゅ悗绔€濆彲璺戦€氱鍒扮锛?

### B1锛歀LM 鎶借薄鎺ュ彛涓庡伐鍘?
- **鐩爣**锛氬畾涔?`BaseLLM` 涓?`LLMFactory`锛屾敮鎸佹寜閰嶇疆閫夋嫨 provider銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/llm/base_llm.py`
  - `src/libs/llm/llm_factory.py`
  - `tests/unit/test_llm_factory.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseLLM.chat(messages) -> str`锛堟垨缁熶竴 response 瀵硅薄锛?
  - `LLMFactory.create(settings) -> BaseLLM`
- **楠屾敹鏍囧噯**锛氬湪娴嬭瘯閲岀敤 Fake provider锛堟祴璇曞唴 stub锛夐獙璇佸伐鍘傝矾鐢遍€昏緫銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_llm_factory.py`銆?

### B2锛欵mbedding 鎶借薄鎺ュ彛涓庡伐鍘?
- **鐩爣**锛氬畾涔?`BaseEmbedding` 涓?`EmbeddingFactory`锛屾敮鎸佹壒閲?embed銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/embedding/base_embedding.py`
  - `src/libs/embedding/embedding_factory.py`
  - `tests/unit/test_embedding_factory.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseEmbedding.embed(texts: list[str], trace: TraceContext | None = None) -> list[list[float]]`
  - `EmbeddingFactory.create(settings) -> BaseEmbedding`
- **楠屾敹鏍囧噯**锛欶ake embedding 杩斿洖绋冲畾鍚戦噺锛屽伐鍘傛寜 provider 鍒嗘祦銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_embedding_factory.py`銆?

### B3锛歋plitter 鎶借薄鎺ュ彛涓庡伐鍘?
- **鐩爣**锛氬畾涔?`BaseSplitter` 涓?`SplitterFactory`锛屾敮鎸佷笉鍚屽垏鍒嗙瓥鐣ワ紙Recursive/Semantic/Fixed锛夈€?
- **淇敼鏂囦欢**锛?
  - `src/libs/splitter/base_splitter.py`
  - `src/libs/splitter/splitter_factory.py`
  - `tests/unit/test_splitter_factory.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseSplitter.split_text(text: str, trace: TraceContext | None = None) -> List[str]`
  - `SplitterFactory.create(settings) -> BaseSplitter`
- **楠屾敹鏍囧噯**锛欶actory 鑳芥牴鎹厤缃繑鍥炰笉鍚岀被鍨嬬殑 Splitter 瀹炰緥锛堟祴璇曚腑鍙敤 Fake 瀹炵幇锛夈€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_splitter_factory.py`銆?

### B4锛歏ectorStore 鎶借薄鎺ュ彛涓庡伐鍘傦紙鍏堝畾涔夊绾︼級
- **鐩爣**锛氬畾涔?`BaseVectorStore` 涓?`VectorStoreFactory`锛屽厛涓嶆帴鐪熷疄 DB銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/vector_store/base_vector_store.py`
  - `src/libs/vector_store/vector_store_factory.py`
  - `tests/unit/test_vector_store_contract.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseVectorStore.upsert(records, trace: TraceContext | None = None)`
  - `BaseVectorStore.query(vector, top_k, filters, trace: TraceContext | None = None)`
- **楠屾敹鏍囧噯**锛氬绾︽祴璇曪紙contract test锛夌害鏉熻緭鍏ヨ緭鍑?shape銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_vector_store_contract.py`銆?

### B5锛歊eranker 鎶借薄鎺ュ彛涓庡伐鍘傦紙鍚?None 鍥為€€锛?
- **鐩爣**锛氬疄鐜?`BaseReranker`銆乣RerankerFactory`锛屾彁渚?`NoneReranker` 浣滀负榛樿鍥為€€銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/reranker/base_reranker.py`
  - `src/libs/reranker/reranker_factory.py`
  - `tests/unit/test_reranker_factory.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseReranker.rerank(query, candidates, trace: TraceContext | None = None) -> ranked_candidates`
  - `NoneReranker`锛堜繚鎸佸師椤哄簭锛?
- **楠屾敹鏍囧噯**锛歜ackend=none 鏃朵笉浼氭敼鍙樻帓搴忥紱鏈煡 backend 鏄庣‘鎶ラ敊銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_reranker_factory.py`銆?

### B6锛欵valuator 鎶借薄鎺ュ彛涓庡伐鍘傦紙鍏堝仛鑷畾涔夎交閲忔寚鏍囷級
- **鐩爣**锛氬畾涔?`BaseEvaluator`銆乣EvaluatorFactory`锛屽疄鐜版渶灏?`CustomEvaluator`锛堜緥濡?hit_rate/mrr锛夈€?
- **淇敼鏂囦欢**锛?
  - `src/libs/evaluator/base_evaluator.py`
  - `src/libs/evaluator/evaluator_factory.py`
  - `src/libs/evaluator/custom_evaluator.py`
  - `tests/unit/test_custom_evaluator.py`
- **楠屾敹鏍囧噯**锛氳緭鍏?query + retrieved_ids + golden_ids 鑳借緭鍑虹ǔ瀹?metrics銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_custom_evaluator.py`銆?

### B7锛氳ˉ榻?Libs 榛樿瀹炵幇锛堟媶鍒嗕负鈮?h鍙獙鏀跺閲忥級

> 璇存槑锛欱7 鍙ˉ榻愪笌绔埌绔富閾捐矾寮虹浉鍏崇殑榛樿瀹炵幇锛圠LM/Embedding/Splitter/VectorStore/Reranker锛夈€傚叾浣欏彲閫夋墿灞曪紙渚嬪棰濆 splitter 绛栫暐銆佹洿澶?vector store 鍚庣銆佹洿澶?evaluator 鍚庣绛夛級淇濇寔鍘熸帓鏈熶笉鎻愬墠銆?

### B7.1锛歄penAI-Compatible LLM锛圤penAI/Azure/DeepSeek锛?
- **鐩爣**锛氳ˉ榻?OpenAI-compatible 鐨?LLM 瀹炵幇锛岀‘淇濋€氳繃 `LLMFactory` 鍙垱寤哄苟鍙 mock 娴嬭瘯銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/llm/openai_llm.py`
  - `src/libs/llm/azure_llm.py`
  - `src/libs/llm/deepseek_llm.py`
  - `tests/unit/test_llm_providers_smoke.py`锛坢ock HTTP锛屼笉璧扮湡瀹炵綉缁滐級
- **楠屾敹鏍囧噯**锛?
  - 閰嶇疆涓嶅悓 `provider` 鏃跺伐鍘傝矾鐢辨纭€?
  - `chat(messages)` 瀵硅緭鍏?shape 鏍￠獙娓呮櫚锛屽紓甯镐俊鎭彲璇伙紙鍖呭惈 provider 涓庨敊璇被鍨嬶級銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_llm_providers_smoke.py`銆?

### B7.2锛歄llama LLM锛堟湰鍦板悗绔級
- **鐩爣**锛氳ˉ榻?`ollama_llm.py`锛屾敮鎸佹湰鍦?HTTP endpoint锛堥粯璁?`base_url` + `model`锛夛紝骞跺彲琚?mock 娴嬭瘯銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/llm/ollama_llm.py`
  - `tests/unit/test_ollama_llm.py`锛坢ock HTTP锛?
- **楠屾敹鏍囧噯**锛?
  - provider=ollama 鏃跺彲鐢?`LLMFactory` 鍒涘缓銆?
  - 鍦ㄨ繛鎺ュけ璐?瓒呮椂绛夊満鏅笅锛屾姏鍑哄彲璇婚敊璇笖涓嶆硠闇叉晱鎰熼厤缃€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_ollama_llm.py`銆?

### B7.3锛歄penAI & Azure Embedding 瀹炵幇
- **鐩爣**锛氳ˉ榻?`openai_embedding.py` 鍜?`azure_embedding.py`锛屾敮鎸?OpenAI 瀹樻柟 API 鍜?Azure OpenAI 鏈嶅姟鐨?Embedding 璋冪敤锛屾敮鎸佹壒閲?`embed(texts)`锛屽苟鍙 mock 娴嬭瘯銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/embedding/openai_embedding.py`
  - `src/libs/embedding/azure_embedding.py`
  - `tests/unit/test_embedding_providers_smoke.py`锛坢ock HTTP锛屽寘鍚?OpenAI 鍜?Azure 娴嬭瘯鐢ㄤ緥锛?
- **楠屾敹鏍囧噯**锛?
  - provider=openai 鏃?`EmbeddingFactory` 鍙垱寤猴紝鏀寔 OpenAI 瀹樻柟 API 鐨?text-embedding-3-small/large 绛夋ā鍨嬨€?
  - provider=azure 鏃?`EmbeddingFactory` 鍙垱寤猴紝姝ｇ‘澶勭悊 Azure 鐗规湁鐨?endpoint銆乤pi-version銆乤pi-key 閰嶇疆锛屾敮鎸?Azure 閮ㄧ讲鐨?text-embedding-ada-002 绛夋ā鍨嬨€?
  - 绌鸿緭鍏ャ€佽秴闀胯緭鍏ユ湁鏄庣‘琛屼负锛堟姤閿欐垨鎴柇绛栫暐鐢遍厤缃喅瀹氾級銆?
  - Azure 瀹炵幇澶嶇敤 OpenAI Embedding 鐨勬牳蹇冮€昏緫锛屼繚鎸佽涓轰竴鑷存€с€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_embedding_providers_smoke.py`銆?

### B7.4锛歄llama Embedding 瀹炵幇
- **鐩爣**锛氳ˉ榻?`ollama_embedding.py`锛屾敮鎸侀€氳繃 Ollama HTTP API 璋冪敤鏈湴閮ㄧ讲鐨?Embedding 妯″瀷锛堝 `nomic-embed-text`銆乣mxbai-embed-large` 绛夛級锛屽疄鐜?`embed(texts)` 鎵归噺鍚戦噺鍖栧姛鑳姐€?
- **淇敼鏂囦欢**锛?
  - `src/libs/embedding/ollama_embedding.py`
  - `tests/unit/test_ollama_embedding.py`锛堝寘鍚?mock HTTP 娴嬭瘯锛?
- **楠屾敹鏍囧噯**锛?
  - provider=ollama 鏃?`EmbeddingFactory` 鍙垱寤恒€?
  - 鏀寔閰嶇疆 Ollama 鏈嶅姟鍦板潃锛堥粯璁?http://localhost:11434锛夊拰妯″瀷鍚嶇О銆?
  - 杈撳嚭鍚戦噺缁村害鐢辨ā鍨嬪喅瀹氾紙濡?nomic-embed-text 涓?768 缁达級锛屾弧瓒?ingestion/retrieval 鐨勬帴鍙ｅ绾︺€?
  - 鏀寔鎵归噺 `embed(texts)` 璋冪敤锛屽唴閮ㄥ鐞嗗崟鏉?鎵归噺璇锋眰閫昏緫銆?
  - 绌鸿緭鍏ャ€佽秴闀胯緭鍏ユ湁鏄庣‘琛屼负锛堟姤閿欐垨鎴柇绛栫暐锛夈€?
  - mock 娴嬭瘯瑕嗙洊姝ｅ父鍝嶅簲銆佽繛鎺ュけ璐ャ€佽秴鏃剁瓑鍦烘櫙銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_ollama_embedding.py`銆?

### B7.5锛歊ecursive Splitter 榛樿瀹炵幇
- **鐩爣**锛氳ˉ榻?`recursive_splitter.py`锛屽皝瑁?LangChain 鐨勫垏鍒嗛€昏緫锛屼綔涓洪粯璁ゅ垏鍒嗗櫒銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/splitter/recursive_splitter.py`
  - `tests/unit/test_recursive_splitter_lib.py`
- **楠屾敹鏍囧噯**锛?
  - provider=recursive 鏃?`SplitterFactory` 鍙垱寤恒€?
  - `split_text` 鑳芥纭鐞?Markdown 缁撴瀯锛堟爣棰?浠ｇ爜鍧椾笉琚墦鏂級銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_recursive_splitter_lib.py`銆?

### B7.6锛欳hromaStore锛圴ectorStore 榛樿鍚庣锛?
- **鐩爣**锛氳ˉ榻?`chroma_store.py`锛屾敮鎸佹渶灏?`upsert(records)` 涓?`query(vector, top_k, filters)`锛屽苟鏀寔鏈湴鎸佷箙鍖栫洰褰曪紙渚嬪 `data/db/chroma/`锛夈€?
- **淇敼鏂囦欢**锛?
  - `src/libs/vector_store/chroma_store.py`
  - `tests/integration/test_chroma_store_roundtrip.py`
- **楠屾敹鏍囧噯**锛?
  - provider=chroma 鏃?`VectorStoreFactory` 鍙垱寤恒€?
  - **蹇呴』瀹屾垚瀹屾暣鐨?upsert鈫抭uery roundtrip 娴嬭瘯**锛氫娇鐢?mock 鏁版嵁瀹屾垚鐪熷疄鐨勫瓨鍌ㄥ拰妫€绱㈡祦绋嬶紝楠岃瘉杩斿洖缁撴灉鐨勭‘瀹氭€у拰姝ｇ‘鎬с€?
  - 娴嬭瘯搴旇鐩栵細鍩烘湰 upsert銆佸悜閲忔煡璇€乼op_k 鍙傛暟銆乵etadata filters锛堝鏀寔锛夈€?
  - 浣跨敤涓存椂鐩綍杩涜鎸佷箙鍖栨祴璇曪紝娴嬭瘯缁撴潫鍚庢竻鐞嗐€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_chroma_store_roundtrip.py`

### B7.7锛歀LM Reranker锛堣鍙?rerank prompt锛?
- **鐩爣**锛氳ˉ榻?`llm_reranker.py`锛岃鍙?`config/prompts/rerank.txt` 鏋勯€?prompt锛堟祴璇曚腑鍙敞鍏ユ浛浠ｆ枃鏈級锛屽苟鍙湪澶辫触鏃惰繑鍥炲彲鍥為€€淇″彿銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/reranker/llm_reranker.py`
  - `tests/unit/test_llm_reranker.py`锛坢ock LLM锛?
- **楠屾敹鏍囧噯**锛?
  - backend=llm 鏃?`RerankerFactory` 鍙垱寤恒€?
  - 杈撳嚭涓ユ牸缁撴瀯鍖栵紙渚嬪 ranked ids锛夛紝涓嶆弧瓒?schema 鏃舵姏鍑哄彲璇婚敊璇€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_llm_reranker.py`銆?

### B7.8锛欳ross-Encoder Reranker锛堟湰鍦?鎵樼妯″瀷锛屽崰浣嶅彲璺戯級
- **鐩爣**锛氳ˉ榻?`cross_encoder_reranker.py`锛屾敮鎸佸 Top-M candidates 鎵撳垎鎺掑簭锛涙祴璇曚腑鐢?mock scorer 淇濊瘉 deterministic銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/reranker/cross_encoder_reranker.py`
  - `tests/unit/test_cross_encoder_reranker.py`锛坢ock scorer锛?
- **楠屾敹鏍囧噯**锛?
  - backend=cross_encoder 鏃?`RerankerFactory` 鍙垱寤恒€?
  - 鎻愪緵瓒呮椂/澶辫触鍥為€€淇″彿锛堜緵 Core 灞?`D6` fallback 浣跨敤锛夈€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_cross_encoder_reranker.py`銆?

### B8锛歏ision LLM 鎶借薄鎺ュ彛涓庡伐鍘傞泦鎴?
- **鐩爣**锛氬畾涔?`BaseVisionLLM` 鎶借薄鎺ュ彛锛屾墿灞?`LLMFactory` 鏀寔 Vision LLM 鍒涘缓锛屼负 C7 鐨?ImageCaptioner 鎻愪緵搴曞眰鎶借薄銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/llm/base_vision_llm.py`
  - `src/libs/llm/llm_factory.py`锛堟墿灞?`create_vision_llm` 鏂规硶锛?
  - `tests/unit/test_vision_llm_factory.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseVisionLLM.chat_with_image(text: str, image_path: str | bytes, trace: TraceContext | None = None) -> ChatResponse`
  - `LLMFactory.create_vision_llm(settings) -> BaseVisionLLM`
- **楠屾敹鏍囧噯**锛?
  - 鎶借薄鎺ュ彛娓呮櫚瀹氫箟澶氭ā鎬佽緭鍏ワ紙鏂囨湰+鍥剧墖璺緞/base64锛夈€?
  - 宸ュ巶鏂规硶 `create_vision_llm` 鑳芥牴鎹厤缃矾鐢卞埌涓嶅悓 provider锛堟祴璇曚腑鐢?Fake Vision LLM 楠岃瘉锛夈€?
  - 鎺ュ彛璁捐鏀寔鍥剧墖棰勫鐞嗭紙鍘嬬缉銆佹牸寮忚浆鎹級鐨勬墿灞曠偣銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_vision_llm_factory.py`銆?

### B9锛欰zure Vision LLM 瀹炵幇
- **鐩爣**锛氬疄鐜?`AzureVisionLLM`锛屾敮鎸侀€氳繃 Azure OpenAI 璋冪敤 GPT-4o/GPT-4-Vision-Preview 杩涜鍥惧儚鐞嗚В銆?
- **淇敼鏂囦欢**锛?
  - `src/libs/llm/azure_vision_llm.py`
  - `tests/unit/test_azure_vision_llm.py`锛坢ock HTTP锛屼笉璧扮湡瀹?API锛?
- **瀹炵幇绫?鍑芥暟**锛?
  - `AzureVisionLLM(BaseVisionLLM)`锛氬疄鐜?`chat_with_image` 鏂规硶
  - 鏀寔 Azure 鐗规湁閰嶇疆锛歚azure_endpoint`, `api_version`, `deployment_name`, `api_key`
- **楠屾敹鏍囧噯**锛?
  - provider=azure 涓旈厤缃?vision_llm 鏃讹紝`LLMFactory.create_vision_llm()` 鍙垱寤?Azure Vision LLM 瀹炰緥銆?
  - 鏀寔鍥剧墖璺緞鍜?base64 涓ょ杈撳叆鏂瑰紡銆?
  - 鍥剧墖杩囧ぇ鏃惰嚜鍔ㄥ帇缂╄嚦 `max_image_size` 閰嶇疆鐨勫昂瀵革紙榛樿2048px锛夈€?
  - API 璋冪敤澶辫触鏃舵姏鍑烘竻鏅伴敊璇紝鍖呭惈 Azure 鐗规湁閿欒鐮併€?
  - mock 娴嬭瘯瑕嗙洊锛氭甯歌皟鐢ㄣ€佸浘鐗囧帇缂┿€佽秴鏃躲€佽璇佸け璐ョ瓑鍦烘櫙銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_azure_vision_llm.py`銆?

### B9.1锛欴ashScope Vision LLM锛圦wen3.5-Plus锛夊疄鐜?
- **鐩爣**锛氬疄鐜?`DashScopeVisionLLM`锛屾敮鎸侀€氳繃闃块噷浜戠櫨鐐硷紙DashScope锛夎皟鐢?`qwen3.5-plus` 杩涜鍥惧儚鐞嗚В锛岃ˉ榻愨€滃浗鍐?+ 鍥藉鍙屾ā鍨嬧€濇柟妗堜腑鐨勫浗鍐呴粯璁ゅ疄鐜般€?
- **淇敼鏂囦欢**锛?
  - `src/libs/llm/dashscope_vision_llm.py`
  - `src/libs/llm/llm_factory.py`锛坴ision provider 娉ㄥ唽 `dashscope`锛?
  - `config/settings.yaml`锛堟柊澧?鏇存柊 `vision_llm.provider: dashscope` 绀轰緥閰嶇疆锛?
  - `tests/unit/test_dashscope_vision_llm.py`锛坢ock HTTP锛屼笉璧扮湡瀹?API锛?
- **瀹炵幇绫?鍑芥暟**锛?
  - `DashScopeVisionLLM(BaseVisionLLM)`锛氬疄鐜?`chat_with_image` 鏂规硶
  - 鏀寔 DashScope 閰嶇疆锛歚base_url`, `api_key`, `model`, `timeout`, `max_image_size`
- **楠屾敹鏍囧噯**锛?
  - provider=dashscope 涓旈厤缃?vision_llm 鏃讹紝`LLMFactory.create_vision_llm()` 鍙垱寤?DashScope Vision LLM 瀹炰緥銆?
  - 鏀寔鍥剧墖璺緞鍜?base64 涓ょ杈撳叆鏂瑰紡銆?
  - 鍥剧墖杩囧ぇ鏃惰嚜鍔ㄥ帇缂╄嚦 `max_image_size` 閰嶇疆鐨勫昂瀵革紙榛樿2048px锛夈€?
  - API 璋冪敤澶辫触鏃舵姏鍑烘竻鏅伴敊璇紙鍖呭惈 provider 涓庨敊璇被鍨?鐘舵€佺爜锛夈€?
  - mock 娴嬭瘯瑕嗙洊锛氭甯歌皟鐢ㄣ€佸浘鐗囧帇缂┿€佽秴鏃躲€佽璇佸け璐ョ瓑鍦烘櫙銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_dashscope_vision_llm.py`銆?

---

## 闃舵 C锛欼ngestion Pipeline MVP锛堢洰鏍囷細鑳芥妸 PDF 鏍蜂緥鎽勫彇鍒版湰鍦板瓨鍌級

> 娉細鏈樁娈典弗鏍兼寜 5.4.1 鐨勭绾挎暟鎹祦钀藉湴锛屽苟浼樺厛瀹炵幇鈥滃閲忚烦杩囷紙SHA256锛夆€濄€?

### C1锛氬畾涔夋牳蹇冩暟鎹被鍨?濂戠害锛圖ocument/Chunk/ChunkRecord锛?
- **鐩爣**锛氬畾涔夊叏閾捐矾锛坕ngestion 鈫?retrieval 鈫?mcp tools锛夊叡鐢ㄧ殑鏁版嵁缁撴瀯/濂戠害锛岄伩鍏嶆暎钀藉湪鍚勫瓙妯″潡鍐呭鑷寸殑鑰﹀悎涓庨噸澶嶃€?
- **淇敼鏂囦欢**锛?
  - `src/core/types.py`
  - `src/core/__init__.py`锛堝彲閫夛細缁熶竴 re-export 浠ョ畝鍖栧鍏ヨ矾寰勶級
  - `tests/unit/test_core_types.py`
- **瀹炵幇绫?鍑芥暟**锛堝缓璁級锛?
  - `Document(id, text, metadata)`
  - `Chunk(id, text, metadata, start_offset, end_offset, source_ref?)`
  - `ChunkRecord(id, text, metadata, dense_vector?, sparse_vector?)`锛堢敤浜庡瓨鍌?妫€绱㈣浇浣擄紱瀛楁鎸夊悗缁?C8~C12 婕旇繘锛?
- **楠屾敹鏍囧噯**锛?
  - 绫诲瀷鍙簭鍒楀寲锛坉ict/json锛変笖瀛楁绋冲畾锛堝崟鍏冩祴璇曟柇瑷€锛夈€?
  - `metadata` 绾﹀畾鏈€灏戝寘鍚?`source_path`锛屽叾浣欏瓧娈靛厑璁稿閲忔墿灞曚絾涓嶅緱鐮村潖鍏煎銆?
  - **`metadata.images` 瀛楁瑙勮寖**锛堢敤浜庡妯℃€佹敮鎸侊級锛?
    - 缁撴瀯锛歚List[{"id": str, "path": str, "page": int, "text_offset": int, "text_length": int, "position": dict}]`
    - `id`锛氬叏灞€鍞竴鍥剧墖鏍囪瘑绗︼紙寤鸿鏍煎紡锛歚{doc_hash}_{page}_{seq}`锛?
    - `path`锛氬浘鐗囨枃浠跺瓨鍌ㄨ矾寰勶紙绾﹀畾锛歚data/images/{collection}/{image_id}.png`锛?
    - `page`锛氬浘鐗囧湪鍘熸枃妗ｄ腑鐨勯〉鐮侊紙鍙€夛紝閫傜敤浜嶱DF绛夊垎椤垫枃妗ｏ級
    - `text_offset`锛氬崰浣嶇鍦?`Document.text` 涓殑璧峰瀛楃浣嶇疆锛堜粠0寮€濮嬭鏁帮級
    - `text_length`锛氬崰浣嶇鐨勫瓧绗﹂暱搴︼紙閫氬父涓?`len("[IMAGE: {image_id}]")`锛?
    - `position`锛氬浘鐗囧湪鍘熸枃妗ｄ腑鐨勭墿鐞嗕綅缃俊鎭紙鍙€夛紝濡侾DF鍧愭爣銆佸儚绱犱綅缃€佸昂瀵哥瓑锛?
    - 璇存槑锛氶€氳繃 `text_offset` 鍜?`text_length` 鍙簿纭畾浣嶅浘鐗囧湪鏂囨湰涓殑浣嶇疆锛屾敮鎸佸悓涓€鍥剧墖澶氭鍑虹幇鐨勫満鏅?
  - **鏂囨湰涓浘鐗囧崰浣嶇瑙勮寖**锛氬湪 `Document.text` 涓紝鍥剧墖浣嶇疆浣跨敤 `[IMAGE: {image_id}]` 鏍煎紡鏍囪銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_core_types.py`銆?

### C2锛氭枃浠跺畬鏁存€ф鏌ワ紙SHA256锛?
- **鐩爣**锛氬湪Libs涓疄鐜?`file_integrity.py`锛氳绠楁枃浠?hash锛屽苟鎻愪緵鈥滄槸鍚﹁烦杩団€濈殑鍒ゅ畾鎺ュ彛锛堜娇鐢?SQLite 浣滀负榛樿瀛樺偍锛屾敮鎸佸悗缁浛鎹负 Redis/PostgreSQL锛夈€?
- **淇敼鏂囦欢**锛?
  - `src/libs/loader/file_integrity.py`
  - `tests/unit/test_file_integrity.py`
  - 鏁版嵁搴撴枃浠讹細`data/db/ingestion_history.db`锛堣嚜鍔ㄥ垱寤猴級
- **瀹炵幇绫?鍑芥暟**锛?
  - `FileIntegrityChecker` 绫伙紙鎶借薄鎺ュ彛锛?
  - `SQLiteIntegrityChecker(FileIntegrityChecker)` 绫伙紙榛樿瀹炵幇锛?
    - `compute_sha256(path: str) -> str`
    - `should_skip(file_hash: str) -> bool`
    - `mark_success(file_hash: str, file_path: str, ...)`
    - `mark_failed(file_hash: str, error_msg: str)`
- **楠屾敹鏍囧噯**锛?
  - 鍚屼竴鏂囦欢澶氭璁＄畻hash缁撴灉涓€鑷?
  - 鏍囪 success 鍚庯紝`should_skip` 杩斿洖 `True`
  - 鏁版嵁搴撴枃浠舵纭垱寤哄湪 `data/db/ingestion_history.db`
  - 鏀寔骞跺彂鍐欏叆锛圫QLite WAL妯″紡锛?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_file_integrity.py`銆?

### C3锛歀oader 鎶借薄鍩虹被涓?PDF Loader 澹冲瓙
- **鐩爣**锛氬湪Libs涓畾涔?`BaseLoader`锛屽苟瀹炵幇 `PdfLoader` 鐨勬渶灏忚涓恒€?
- **淇敼鏂囦欢**锛?
  - `src/libs/loader/base_loader.py`
  - `src/libs/loader/pdf_loader.py`
  - `tests/unit/test_loader_pdf_contract.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseLoader.load(path) -> Document`
  - `PdfLoader.load(path)`
- **楠屾敹鏍囧噯**锛?
  - **鍩虹瑕佹眰**锛氬 sample PDF锛坒ixtures锛夎兘浜у嚭 Document锛宮etadata 鑷冲皯鍚?`source_path`銆?
  - **鍥剧墖澶勭悊瑕佹眰**锛堥伒寰?C1 瀹氫箟鐨勫绾︼級锛?
    - 鑻?PDF 鍖呭惈鍥剧墖锛屽簲鎻愬彇鍥剧墖骞朵繚瀛樺埌 `data/images/{doc_hash}/` 鐩綍
    - 鍦?`Document.text` 涓紝鍥剧墖浣嶇疆鎻掑叆鍗犱綅绗︼細`[IMAGE: {image_id}]`
    - 鍦?`metadata.images` 涓褰曞浘鐗囦俊鎭紙鏍煎紡瑙?C1 瑙勮寖锛?
    - 鑻?PDF 鏃犲浘鐗囷紝`metadata.images` 鍙负绌哄垪琛ㄦ垨鐪佺暐璇ュ瓧娈?
  - **闄嶇骇琛屼负**锛氬浘鐗囨彁鍙栧け璐ヤ笉搴旈樆濉炴枃鏈В鏋愶紝鍙湪鏃ュ織涓褰曡鍛娿€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_loader_pdf_contract.py`銆?
- **娴嬭瘯寤鸿**锛?
  - 鍑嗗涓や釜娴嬭瘯鏂囦欢锛歚simple.pdf`锛堢函鏂囨湰锛夊拰 `with_images.pdf`锛堝寘鍚浘鐗囷級
  - 楠岃瘉绾枃鏈琍DF鑳芥甯歌В鏋?
  - 楠岃瘉甯﹀浘鐗嘝DF鑳芥彁鍙栧浘鐗囧苟姝ｇ‘鎻掑叆鍗犱綅绗?

### C4锛歋plitter 闆嗘垚锛堣皟鐢?Libs锛?
- **鐩爣**锛氬疄鐜?Chunking 妯″潡浣滀负 `libs.splitter` 鍜?Ingestion Pipeline 涔嬮棿鐨?*閫傞厤鍣ㄥ眰**锛屽畬鎴?Document鈫扖hunks 鐨勪笟鍔″璞¤浆鎹€?
- **鏍稿績鑱岃矗锛圖ocumentChunker 鐩告瘮 libs.splitter 鐨勫鍊硷級**锛?
  - **鑱岃矗杈圭晫璇存槑**锛?
    - `libs.splitter`锛氱函鏂囨湰鍒囧垎宸ュ叿锛坄str 鈫?List[str]`锛夛紝涓嶆秹鍙婁笟鍔″璞?
    - `DocumentChunker`锛氫笟鍔￠€傞厤鍣紙`Document瀵硅薄 鈫?List[Chunk瀵硅薄]`锛夛紝娣诲姞涓氬姟閫昏緫
  - **6 涓鍊煎姛鑳?*锛?
    1. **Chunk ID 鐢熸垚**锛氫负姣忎釜鏂囨湰鐗囨鐢熸垚鍞竴涓旂‘瀹氭€х殑 ID锛堟牸寮忥細`{doc_id}_{index:04d}_{hash_8chars}`锛?
    2. **鍏冩暟鎹户鎵?*锛氬皢 Document.metadata 澶嶅埗鍒版瘡涓?Chunk.metadata锛坰ource_path, doc_type, title 绛夛級
    3. **娣诲姞 chunk_index**锛氳褰?chunk 鍦ㄦ枃妗ｄ腑鐨勫簭鍙凤紙浠?0 寮€濮嬶級锛岀敤浜庢帓搴忓拰瀹氫綅
    4. **寤虹珛 source_ref**锛氳褰?Chunk.source_ref 鎸囧悜鐖?Document.id锛屾敮鎸佹函婧?
    5. **鍥剧墖寮曠敤鎸夐渶鍒嗗彂**锛氭壂鎻忔瘡涓?chunk 鏂囨湰涓殑 `[IMAGE: {id}]` 鍗犱綅绗︼紝浠?`Document.metadata["images"]` 涓彁鍙栬 chunk 瀹為檯寮曠敤鐨?ImageRef锛屽啓鍏?`chunk.metadata["images"]`锛堜粎鍚 chunk 寮曠敤鐨勫瓙闆嗭級鍜?`chunk.metadata["image_refs"]`锛坕mage_id 鍒楄〃锛夈€傛棤鍗犱綅绗︾殑 chunk 涓嶅惈 `images` 瀛楁銆傗殸锔?涓嶅彲绠€鍗曟暣浣撶户鎵挎垨涓㈠純鏂囨。绾?`images`锛屽惁鍒欎笅娓?C7 ImageCaptioner 灏嗘棤娉曞畾浣嶅浘鐗囪矾寰勩€?
    6. **绫诲瀷杞崲**锛氬皢 libs.splitter 鐨?`List[str]` 杞崲涓虹鍚?core.types 濂戠害鐨?`List[Chunk]` 瀵硅薄
- **淇敼鏂囦欢**锛?
  - `src/ingestion/chunking/document_chunker.py`
  - `src/ingestion/chunking/__init__.py`
  - `tests/unit/test_document_chunker.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `DocumentChunker` 绫?
  - `__init__(settings: Settings)`锛氶€氳繃 SplitterFactory 鑾峰彇閰嶇疆鐨?splitter 瀹炰緥
  - `split_document(document: Document) -> List[Chunk]`锛氬畬鏁寸殑杞崲娴佺▼
  - `_generate_chunk_id(doc_id: str, index: int, text: str) -> str`锛氱敓鎴愮ǔ瀹?Chunk ID
  - `_inherit_metadata(document: Document, chunk_index: int, chunk_text: str) -> dict`锛氬厓鏁版嵁缁ф壙 + 鍥剧墖寮曠敤鎸夐渶鍒嗗彂閫昏緫锛堥渶瑕?chunk_text 鏉ユ壂鎻?`[IMAGE: id]` 鍗犱綅绗︼級
- **楠屾敹鏍囧噯**锛?
  - **閰嶇疆椹卞姩**锛氶€氳繃淇敼 settings.yaml 涓殑 splitter 閰嶇疆锛堝 chunk_size锛夛紝浜у嚭鐨?chunk 鏁伴噺鍜岄暱搴﹀彂鐢熺浉搴斿彉鍖?
  - **ID 鍞竴鎬?*锛氭瘡涓?Chunk 鐨?ID 鍦ㄦ暣涓枃妗ｄ腑鍞竴
  - **ID 纭畾鎬?*锛氬悓涓€ Document 瀵硅薄閲嶅鍒囧垎浜х敓鐩稿悓鐨?Chunk ID 搴忓垪
  - **鍏冩暟鎹畬鏁存€?*锛欳hunk.metadata 鍖呭惈鎵€鏈?Document.metadata 瀛楁 + chunk_index 瀛楁
  - **鍥剧墖鍒嗗彂姝ｇ‘鎬?*锛氬惈 `[IMAGE: id]` 鍗犱綅绗︾殑 chunk 鍏?`metadata["images"]` 浠呭寘鍚 chunk 寮曠敤鐨勫浘鐗囧瓙闆嗭紱涓嶅惈鍗犱綅绗︾殑 chunk 鏃?`images` 瀛楁锛沗metadata["image_refs"]` 鍒楄〃涓庡崰浣嶇涓€鑷?
  - **婧簮閾炬帴**锛氭墍鏈?Chunk.source_ref 姝ｇ‘鎸囧悜鐖?Document.id
  - **绫诲瀷濂戠害**锛氳緭鍑虹殑 Chunk 瀵硅薄绗﹀悎 `core/types.py` 涓殑 Chunk 瀹氫箟锛堝彲搴忓垪鍖栥€佸瓧娈靛畬鏁达級
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_document_chunker.py`锛堜娇鐢?FakeSplitter 闅旂娴嬭瘯锛屾棤闇€鐪熷疄 LLM/澶栭儴渚濊禆锛夈€?

### C5锛歍ransform 鎶借薄鍩虹被 + ChunkRefiner锛堣鍒欏幓鍣?+ LLM 澧炲己锛?
- **鐩爣**锛氬畾涔?`BaseTransform`锛涘疄鐜?`ChunkRefiner`锛氬厛鍋氳鍒欏幓鍣紝鍐嶉€氳繃LLM杩涜鏅鸿兘澧炲己锛屽苟鎻愪緵澶辫触闄嶇骇鏈哄埗锛圠LM寮傚父鏃跺洖閫€鍒拌鍒欑粨鏋滐紝涓嶉樆濉?ingestion锛夈€?
- **鍓嶇疆鏉′欢**锛堝繀椤诲噯澶囷級锛?
  - **蹇呴』閰嶇疆LLM**锛氬湪 `config/settings.yaml` 涓厤缃彲鐢ㄧ殑LLM锛坧rovider/model/api_key锛?
  - **鐜鍙橀噺**锛氳缃搴旂殑API key鐜鍙橀噺锛坄OPENAI_API_KEY`/`OLLAMA_BASE_URL`绛夛級
  - **楠岃瘉鐩殑**锛氶€氳繃鐪熷疄LLM娴嬭瘯楠岃瘉閰嶇疆姝ｇ‘鎬у拰refinement鏁堟灉
- **淇敼鏂囦欢**锛?
  - `src/ingestion/transform/base_transform.py`锛堟柊澧烇級
  - `src/ingestion/transform/chunk_refiner.py`锛堟柊澧烇級
  - `src/core/trace/trace_context.py`锛堟柊澧烇細鏈€灏忓疄鐜帮紝Phase F 瀹屽杽锛?
  - `config/prompts/chunk_refinement.txt`锛堝凡瀛樺湪锛岄渶楠岃瘉鍐呭骞惰ˉ鍏?{text} 鍗犱綅绗︼級
  - `tests/fixtures/noisy_chunks.json`锛堟柊澧烇細8涓吀鍨嬪櫔澹板満鏅級
  - `tests/unit/test_chunk_refiner.py`锛堟柊澧烇細27涓崟鍏冩祴璇曪級
  - `tests/integration/test_chunk_refiner_llm.py`锛堟柊澧烇細鐪熷疄LLM闆嗘垚娴嬭瘯锛?
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseTransform.transform(chunks, trace) -> List[Chunk]`
  - `ChunkRefiner.__init__(settings, llm?, prompt_path?)`
  - `ChunkRefiner.transform(chunks, trace) -> List[Chunk]`
  - `ChunkRefiner._rule_based_refine(text) -> str`锛堝幓绌虹櫧/椤电湁椤佃剼/鏍煎紡鏍囪/HTML娉ㄩ噴锛?
  - `ChunkRefiner._llm_refine(text, trace) -> str | None`锛堝彲閫?LLM 閲嶅啓锛屽け璐ヨ繑鍥?None锛?
  - `ChunkRefiner._load_prompt(prompt_path?)`锛堜粠鏂囦欢鍔犺浇prompt妯℃澘锛屾敮鎸侀粯璁allback锛?
- **瀹炵幇娴佺▼寤鸿**锛?
  1. 鍏堝垱寤?`tests/fixtures/noisy_chunks.json`锛屽寘鍚?涓吀鍨嬪櫔澹板満鏅細
     - typical_noise_scenario: 缁煎悎鍣０锛堥〉鐪?椤佃剼/绌虹櫧锛?
     - ocr_errors: OCR閿欒鏂囨湰
     - page_header_footer: 椤电湁椤佃剼妯″紡
     - excessive_whitespace: 澶氫綑绌虹櫧
     - format_markers: HTML/Markdown鏍囪
     - clean_text: 骞插噣鏂囨湰锛堥獙璇佷笉杩囧害娓呯悊锛?
     - code_blocks: 浠ｇ爜鍧楋紙楠岃瘉淇濈暀鍐呴儴鏍煎紡锛?
     - mixed_noise: 鐪熷疄娣峰悎鍦烘櫙
  2. 鍒涘缓 `TraceContext` 鍗犱綅瀹炵幇锛坲uid鐢熸垚trace_id锛宺ecord_stage瀛樺偍闃舵鏁版嵁锛?
  3. 瀹炵幇 `BaseTransform` 鎶借薄鎺ュ彛
  4. 瀹炵幇 `ChunkRefiner._rule_based_refine` 瑙勫垯鍘诲櫔閫昏緫锛堟鍒欏尮閰?鍒嗘澶勭悊锛?
  5. 缂栧啓瑙勫垯妯″紡鍗曞厓娴嬭瘯锛堜娇鐢?fixtures 鏂█娓呮礂鏁堟灉锛?
  6. 瀹炵幇 `_llm_refine` 鍙€夊寮猴紙璇诲彇 prompt銆佽皟鐢?LLM銆侀敊璇鐞嗭級
  7. 缂栧啓 LLM 妯″紡鍗曞厓娴嬭瘯锛坢ock LLM 鏂█璋冪敤涓庤緭鍑猴級
  8. 缂栧啓闄嶇骇鍦烘櫙娴嬭瘯锛圠LM 澶辫触鏃跺洖閫€鍒拌鍒欑粨鏋滐紝鏍囪 metadata锛?
  9. **缂栧啓鐪熷疄LLM闆嗘垚娴嬭瘯骞舵墽琛岄獙璇?*锛堝繀椤绘墽琛岋紝楠岃瘉LLM閰嶇疆锛?
- **楠屾敹鏍囧噯**锛?
  - **鍗曞厓娴嬭瘯锛堝揩閫熷弽棣堝惊鐜級**锛?
    - 瑙勫垯妯″紡锛氬 fixtures 鍣０鏍蜂緥鑳芥纭幓鍣紙杩炵画绌虹櫧/椤电湁椤佃剼/鏍煎紡鏍囪/鍒嗛殧绾匡級
    - 淇濈暀鑳藉姏锛氫唬鐮佸潡鍐呴儴鏍煎紡涓嶈鐮村潖锛孧arkdown缁撴瀯瀹屾暣淇濈暀
    - LLM 妯″紡锛歮ock LLM 鏃惰兘姝ｇ‘璋冪敤骞惰繑鍥為噸鍐欑粨鏋滐紝metadata 鏍囪 `refined_by: "llm"`
    - 闄嶇骇琛屼负锛歀LM 澶辫触鏃跺洖閫€鍒拌鍒欑粨鏋滐紝metadata 鏍囪 `refined_by: "rule"` 鍜?fallback 鍘熷洜
    - 閰嶇疆寮€鍏筹細閫氳繃 `settings.yaml` 鐨?`ingestion.chunk_refiner.use_llm` 鎺у埗琛屼负
    - 寮傚父澶勭悊锛氬崟涓猚hunk澶勭悊寮傚父涓嶅奖鍝嶅叾浠朿hunk锛屼繚鐣欏師鏂?
  - **闆嗘垚娴嬭瘯锛堥獙鏀跺繀椤婚」锛?*锛?
    - 鉁?**蹇呴』楠岃瘉鐪熷疄LLM璋冪敤鎴愬姛**锛氫娇鐢ㄥ墠缃潯浠朵腑閰嶇疆鐨凩LM杩涜鐪熷疄refinement
    - 鉁?**蹇呴』楠岃瘉杈撳嚭璐ㄩ噺**锛歀LM refined鏂囨湰纭疄鏇村共鍑€锛堝櫔澹板噺灏戙€佸唴瀹逛繚鐣欙級
    - 鉁?**蹇呴』楠岃瘉闄嶇骇鏈哄埗**锛氭棤鏁堟ā鍨嬪悕绉版椂浼橀泤闄嶇骇鍒皉ule-based锛屼笉宕╂簝
    - 璇存槑锛氳繖鏄獙璇?鍓嶇疆鏉′欢涓噯澶囩殑LLM閰嶇疆鏄惁姝ｇ‘"鐨勫繀瑕佹楠?
- **娴嬭瘯鏂规硶**锛?
  - **闃舵1-鍗曞厓娴嬭瘯锛堝紑鍙戜腑蹇€熻凯浠ｏ級**锛?
    ```bash
    pytest tests/unit/test_chunk_refiner.py -v
    # 鉁?27涓祴璇曞叏閮ㄩ€氳繃锛屼娇鐢∕ock闅旂锛屾棤闇€鐪熷疄API
    ```
  - **闃舵2-闆嗘垚娴嬭瘯锛堥獙鏀跺繀椤绘墽琛岋級**锛?
    ```bash
    # 1. 杩愯鐪熷疄LLM闆嗘垚娴嬭瘯锛堝繀椤伙級
    pytest tests/integration/test_chunk_refiner_llm.py -v -s
    # 鉁?楠岃瘉LLM閰嶇疆姝ｇ‘锛宺efinement鏁堟灉绗﹀悎棰勬湡
    # 鈿狅笍 浼氫骇鐢熺湡瀹濧PI璋冪敤涓庤垂鐢?
    
    # 2. Review鎵撳嵃杈撳嚭锛岀‘璁ょ簿鐐艰川閲?
    # - 鍣０鏄惁琚湁鏁堝幓闄わ紵
    # - 鏈夋晥鍐呭鏄惁瀹屾暣淇濈暀锛?
    # - 闄嶇骇鏈哄埗鏄惁姝ｅ父宸ヤ綔锛?
    ```
  - **娴嬭瘯鍒嗗眰閫昏緫**锛?
    - 鍗曞厓娴嬭瘯锛氶獙璇佷唬鐮侀€昏緫姝ｇ‘
    - 闆嗘垚娴嬭瘯锛氶獙璇佺郴缁熷彲鐢ㄦ€?
    - 涓よ€呬簰琛ワ紝缂轰竴涓嶅彲

### C6锛歁etadataEnricher锛堣鍒欏寮?+ 鍙€?LLM 澧炲己 + 闄嶇骇锛?
- **鐩爣**锛氬疄鐜板厓鏁版嵁澧炲己妯″潡锛氭彁渚涜鍒欏寮虹殑榛樿瀹炵幇锛屽苟閲嶇偣鏀寔 LLM 澧炲己锛堥厤缃凡灏辩华锛孡LM 寮€鍏虫墦寮€锛夈€傚埄鐢?LLM 瀵?chunk 杩涜楂樿川閲忕殑 title 鐢熸垚銆乻ummary 鎽樿鍜?tags 鎻愬彇銆傚悓鏃朵繚鐣欏け璐ラ檷绾ф満鍒讹紝纭繚涓嶉樆濉?ingestion銆?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/transform/metadata_enricher.py`
  - `tests/unit/test_metadata_enricher_contract.py`
- **楠屾敹鏍囧噯**锛?
  - 瑙勫垯妯″紡锛氫綔涓哄厹搴曢€昏緫锛岃緭鍑?metadata 蹇呴』鍖呭惈 `title/summary/tags`锛堣嚦灏戦潪绌猴級銆?
  - **LLM 妯″紡锛堟牳蹇冿級**锛氬湪 LLM 鎵撳紑鐨勬儏鍐典笅锛岀‘淇濈湡瀹炶皟鐢?LLM锛堟垨楂樿川閲?Mock锛夊苟鐢熸垚璇箟涓板瘜鐨?metadata銆傞渶楠岃瘉鍦ㄦ湁鐪熷疄 LLM 閰嶇疆涓嬬殑杩為€氭€т笌鏁堟灉銆?
  - 闄嶇骇琛屼负锛歀LM 璋冪敤澶辫触鏃跺洖閫€鍒拌鍒欐ā寮忕粨鏋滐紙鍙湪 metadata 鏍囪闄嶇骇鍘熷洜锛屼絾涓嶆姏鍑鸿嚧鍛藉紓甯革級銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_metadata_enricher_contract.py`锛屽苟纭繚鍖呭惈寮€鍚?LLM 鐨勯泦鎴愭祴璇曠敤渚嬨€?

### C7锛欼mageCaptioner锛堝彲閫夌敓鎴?caption + 闄嶇骇涓嶉樆濉烇級
- **鐩爣**锛氬疄鐜?`image_captioner.py`锛氬綋鍚敤 Vision LLM 涓斿瓨鍦?image_refs 鏃剁敓鎴?caption 骞跺啓鍥?chunk metadata锛涘綋绂佺敤/涓嶅彲鐢?寮傚父鏃惰蛋闄嶇骇璺緞锛屼笉闃诲 ingestion銆?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/transform/image_captioner.py`
  - `config/prompts/image_captioning.txt`锛堜綔涓洪粯璁?prompt 鏉ユ簮锛涘彲鍦ㄦ祴璇曚腑娉ㄥ叆鏇夸唬鏂囨湰锛?
  - `tests/unit/test_image_captioner_fallback.py`
- **楠屾敹鏍囧噯**锛?
  - 鍚敤妯″紡锛氬瓨鍦?image_refs 鏃朵細鐢熸垚 caption 骞跺啓鍏?metadata锛堟祴璇曚腑鐢?mock Vision LLM 鏂█璋冪敤涓庤緭鍑猴級銆?
  - 闄嶇骇妯″紡锛氬綋閰嶇疆绂佺敤鎴栧紓甯告椂锛宑hunk 淇濈暀 image_refs锛屼絾涓嶇敓鎴?caption 涓旀爣璁?`has_unprocessed_images`銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_image_captioner_fallback.py`銆?

### C8锛欴enseEncoder锛堜緷璧?libs.embedding锛?
- **鐩爣**锛氬疄鐜?`dense_encoder.py`锛屾妸 chunks.text 鎵归噺閫佸叆 `BaseEmbedding`銆?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/embedding/dense_encoder.py`
  - `tests/unit/test_dense_encoder.py`
- **楠屾敹鏍囧噯**锛歟ncoder 杈撳嚭鍚戦噺鏁伴噺涓?chunks 鏁伴噺涓€鑷达紝缁村害涓€鑷淬€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_dense_encoder.py`銆?

### C9锛歋parseEncoder锛圔M25 缁熻涓庤緭鍑哄绾︼級
- **鐩爣**锛氬疄鐜?`sparse_encoder.py`锛氬 chunks 寤虹珛 BM25 鎵€闇€缁熻锛堝彲鍏堜粎杈撳嚭 term weights 缁撴瀯锛岀储寮曡惤鍦颁笅涓€姝ュ仛锛夈€?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/embedding/sparse_encoder.py`
  - `tests/unit/test_sparse_encoder.py`
- **楠屾敹鏍囧噯**锛氳緭鍑虹粨鏋勫彲鐢ㄤ簬 bm25_indexer锛涘绌烘枃鏈湁鏄庣‘琛屼负銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_sparse_encoder.py`銆?

### C10锛欱atchProcessor锛堟壒澶勭悊缂栨帓锛?
- **鐩爣**锛氬疄鐜?`batch_processor.py`锛氬皢 chunks 鍒?batch锛岄┍鍔?dense/sparse 缂栫爜锛岃褰曟壒娆¤€楁椂锛堜负 trace 棰勭暀锛夈€?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/embedding/batch_processor.py`
  - `tests/unit/test_batch_processor.py`
- **楠屾敹鏍囧噯**锛歜atch_size=2 鏃跺 5 chunks 鍒嗘垚 3 鎵癸紝涓旈『搴忕ǔ瀹氥€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_batch_processor.py`銆?

---

**鈹佲攣鈹佲攣 瀛樺偍闃舵鍒嗙晫绾匡細浠ヤ笅浠诲姟璐熻矗灏嗙紪鐮佺粨鏋滄寔涔呭寲 鈹佲攣鈹佲攣**

> **璇存槑**锛欳8-C10瀹屾垚浜咲ense鍜孲parse鐨勭紪鐮佸伐浣滐紝C11-C13璐熻矗灏嗙紪鐮佺粨鏋滃瓨鍌ㄥ埌涓嶅悓鐨勫悗绔€?
> - **C11 (BM25Indexer)**锛氬鐞哠parse缂栫爜缁撴灉 鈫?鏋勫缓鍊掓帓绱㈠紩 鈫?瀛樺偍鍒版枃浠剁郴缁?
> - **C12 (VectorUpserter)**锛氬鐞咲ense缂栫爜缁撴灉 鈫?鐢熸垚绋冲畾ID 鈫?瀛樺偍鍒板悜閲忔暟鎹簱
> - **C13 (ImageStorage)**锛氬鐞嗗浘鐗囨暟鎹?鈫?鏂囦欢瀛樺偍 + 绱㈠紩鏄犲皠

---

### C11锛欱M25Indexer锛堝€掓帓绱㈠紩鏋勫缓涓庢寔涔呭寲锛?
- **鐩爣**锛氬疄鐜?`bm25_indexer.py`锛氭帴鏀?SparseEncoder 鐨則erm statistics杈撳嚭锛岃绠桰DF锛屾瀯寤哄€掓帓绱㈠紩锛屽苟鎸佷箙鍖栧埌 `data/db/bm25/`銆?
- **鏍稿績鍔熻兘**锛?
  - 璁＄畻 IDF (Inverse Document Frequency)锛歚IDF(term) = log((N - df + 0.5) / (df + 0.5))`
  - 鏋勫缓鍊掓帓绱㈠紩缁撴瀯锛歚{term: {idf, postings: [{chunk_id, tf, doc_length}]}}`
  - 绱㈠紩搴忓垪鍖栦笌鍔犺浇锛堟敮鎸佸閲忔洿鏂颁笌閲嶅缓锛?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/storage/bm25_indexer.py`
  - `tests/unit/test_bm25_indexer_roundtrip.py`
- **楠屾敹鏍囧噯**锛?
  - build 鍚庤兘 load 骞跺鍚屼竴璇枡鏌ヨ杩斿洖绋冲畾 top ids
  - IDF璁＄畻鍑嗙‘锛堝彲鐢ㄥ凡鐭ヨ鏂欏姣旈獙璇侊級
  - 鏀寔绱㈠紩閲嶅缓涓庡閲忔洿鏂?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_bm25_indexer_roundtrip.py`銆?
- **澶囨敞**锛氭湰浠诲姟瀹屾垚Sparse璺緞鐨勬渶鍚庝竴鐜紝涓篋3 (SparseRetriever) 鎻愪緵鍙煡璇㈢殑BM25绱㈠紩銆?

### C12锛歏ectorUpserter锛堝悜閲忓瓨鍌ㄤ笌骞傜瓑鎬т繚璇侊級
- **鐩爣**锛氬疄鐜?`vector_upserter.py`锛氭帴鏀?DenseEncoder 鐨勫悜閲忚緭鍑猴紝鐢熸垚绋冲畾鐨?`chunk_id`锛屽苟璋冪敤 VectorStore 杩涜骞傜瓑鍐欏叆銆?
- **鏍稿績鍔熻兘**锛?
  - 鐢熸垚纭畾鎬?chunk_id锛歚hash(source_path + chunk_index + content_hash[:8])`
  - 璋冪敤 `BaseVectorStore.upsert()` 鍐欏叆鍚戦噺鏁版嵁搴?
  - 淇濊瘉骞傜瓑鎬э細鍚屼竴鍐呭閲嶅鍐欏叆涓嶄骇鐢熼噸澶嶈褰?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/storage/vector_upserter.py`
  - `tests/unit/test_vector_upserter_idempotency.py`
- **楠屾敹鏍囧噯**锛?
  - 鍚屼竴 chunk 涓ゆ upsert 浜х敓鐩稿悓 id
  - 鍐呭鍙樻洿鏃?id 鍙樻洿
  - 鏀寔鎵归噺 upsert 涓斾繚鎸侀『搴?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_vector_upserter_idempotency.py`銆?
- **澶囨敞**锛氭湰浠诲姟瀹屾垚Dense璺緞鐨勬渶鍚庝竴鐜紝涓篋2 (DenseRetriever) 鎻愪緵鍙煡璇㈢殑鍚戦噺鏁版嵁搴撱€?

### C13锛欼mageStorage锛堝浘鐗囨枃浠跺瓨鍌ㄤ笌绱㈠紩琛ㄥ绾︼級
- **鐩爣**锛氬疄鐜?`image_storage.py`锛氫繚瀛樺浘鐗囧埌 `data/images/{collection}/`锛屽苟浣跨敤 **SQLite** 璁板綍 image_id鈫抪ath 鏄犲皠銆?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/storage/image_storage.py`
  - `tests/unit/test_image_storage.py`
- **楠屾敹鏍囧噯**锛氫繚瀛樺悗鏂囦欢瀛樺湪锛涙煡鎵?image_id 杩斿洖姝ｇ‘璺緞锛涙槧灏勫叧绯绘寔涔呭寲鍦?`data/db/image_index.db`銆?
- **鎶€鏈柟妗?*锛?
  - 澶嶇敤椤圭洰宸叉湁鐨?SQLite 鏋舵瀯妯″紡锛堝弬鑰?`file_integrity.py` 鐨?`SQLiteIntegrityChecker`锛?
  - 鏁版嵁搴撹〃缁撴瀯锛?
    ```sql
    CREATE TABLE image_index (
        image_id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        collection TEXT,
        doc_hash TEXT,
        page_num INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_collection ON image_index(collection);
    CREATE INDEX idx_doc_hash ON image_index(doc_hash);
    ```
  - 鎻愪緵骞跺彂瀹夊叏璁块棶锛圵AL 妯″紡锛?
  - 鏀寔鎸?collection 鎵归噺鏌ヨ
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_image_storage.py`銆?

### C14锛歅ipeline 缂栨帓锛圡VP 涓茶捣鏉ワ級
- **鐩爣**锛氬疄鐜?`pipeline.py`锛氫覆琛屾墽琛岋紙integrity鈫抣oad鈫抯plit鈫抰ransform鈫抏ncode鈫抯tore锛夛紝骞跺澶辫触姝ラ鍋氭竻鏅板紓甯搞€?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/pipeline.py`
  - `tests/integration/test_ingestion_pipeline.py`
- **娴嬭瘯鏁版嵁**锛?
  - **涓绘祴璇曟枃妗?*锛歚tests/fixtures/sample_documents/complex_technical_doc.pdf`
    - 8绔犺妭鎶€鏈枃妗ｏ紙~21KB锛?
    - 鍖呭惈3寮犲祵鍏ュ浘鐗囷紙闇€娴嬭瘯鍥剧墖鎻愬彇鍜屾弿杩帮級
    - 鍖呭惈5涓〃鏍硷紙娴嬭瘯琛ㄦ牸鍐呭瑙ｆ瀽锛?
    - 澶氶〉澶氭钀斤紙娴嬭瘯瀹屾暣鍒嗗潡娴佺▼锛?
  - **杈呭姪娴嬭瘯**锛歚tests/fixtures/sample_documents/simple.pdf`锛堢畝鍗曞満鏅洖褰掞級
- **楠屾敹鏍囧噯**锛?
  - 瀵?`complex_technical_doc.pdf` 璺戝畬鏁?pipeline锛屾垚鍔熻緭鍑猴細
    - 鍚戦噺绱㈠紩鏂囦欢鍒?ChromaDB
    - BM25 绱㈠紩鏂囦欢鍒?`data/db/bm25/`
    - 鎻愬彇鐨勫浘鐗囧埌 `data/images/` (SHA256鍛藉悕)
  - Pipeline 鏃ュ織娓呮櫚灞曠ず鍚勯樁娈佃繘搴?
  - 澶辫触姝ラ鎶涘嚭鏄庣‘寮傚父淇℃伅
- **娴嬭瘯鏂规硶**锛歚pytest -v tests/integration/test_ingestion_pipeline.py`銆?

### C15锛氳剼鏈叆鍙?ingest.py锛堢绾垮彲鐢級
- **鐩爣**锛氬疄鐜?`scripts/ingest.py`锛屾敮鎸?`--collection`銆乣--path`銆乣--force`锛屽苟璋冪敤 pipeline銆?
- **淇敼鏂囦欢**锛?
  - `scripts/ingest.py`
  - `tests/e2e/test_data_ingestion.py`
- **楠屾敹鏍囧噯**锛氬懡浠よ鍙繍琛屽苟鍦?`data/db` 浜х敓浜х墿锛涢噸澶嶈繍琛屽湪鏈彉鏇存椂璺宠繃銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/e2e/test_data_ingestion.py`锛堝敖閲忕敤涓存椂鐩綍锛夈€?

---

## 闃舵 D锛歊etrieval MVP锛堢洰鏍囷細鑳?query 骞惰繑鍥?Top-K chunks锛?

### D1锛歈ueryProcessor锛堝叧閿瘝鎻愬彇 + filters 缁撴瀯锛?
- **鐩爣**锛氬疄鐜?`query_processor.py`锛氬叧閿瘝鎻愬彇锛堝厛瑙勫垯/鍒嗚瘝锛夛紝骞惰В鏋愰€氱敤 filters 缁撴瀯锛堝彲绌哄疄鐜帮級銆?
- **淇敼鏂囦欢**锛?
  - `src/core/query_engine/query_processor.py`
  - `tests/unit/test_query_processor.py`
- **楠屾敹鏍囧噯**锛氬杈撳叆 query 杈撳嚭 `keywords` 闈炵┖锛堝彲鏍规嵁鍋滅敤璇嶇瓥鐣ワ級锛宖ilters 涓?dict銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_query_processor.py`銆?

### D2锛欴enseRetriever锛堣皟鐢?VectorStore.query锛?
- **鐩爣**锛氬疄鐜?`dense_retriever.py`锛岀粍鍚?`EmbeddingClient`锛坬uery 鍚戦噺鍖栵級+ `VectorStore`锛堝悜閲忔绱級锛屽畬鎴愯涔夊彫鍥炪€?
- **鍓嶇疆浠诲姟**锛?
  1. 闇€鍏堝湪 `src/core/types.py` 涓畾涔?`RetrievalResult` 绫诲瀷锛堝寘鍚?`chunk_id`, `score`, `text`, `metadata` 瀛楁锛?
  2. 闇€纭 ChromaStore.query() 杩斿洖缁撴灉鍖呭惈 text锛堝綋鍓嶅瓨鍌ㄥ湪 documents 瀛楁锛岄渶琛ュ厖杩斿洖锛?
- **淇敼鏂囦欢**锛?
  - `src/core/types.py`锛堟柊澧?`RetrievalResult` 绫诲瀷锛?
  - `src/libs/vector_store/chroma_store.py`锛堜慨澶嶏細query 杩斿洖缁撴灉闇€鍖呭惈 text 瀛楁锛?
  - `src/core/query_engine/dense_retriever.py`
  - `tests/unit/test_dense_retriever.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `RetrievalResult` dataclass锛歚chunk_id: str`, `score: float`, `text: str`, `metadata: Dict`
  - `DenseRetriever.__init__(settings, embedding_client?, vector_store?)`锛氭敮鎸佷緷璧栨敞鍏ョ敤浜庢祴璇?
  - `DenseRetriever.retrieve(query: str, top_k: int, filters?: dict, trace?) -> List[RetrievalResult]`
  - 鍐呴儴娴佺▼锛歚query 鈫?embedding_client.embed([query]) 鈫?vector_store.query(vector, top_k, filters) 鈫?浠庤繑鍥炵粨鏋滄彁鍙?text 鈫?瑙勮寖鍖栫粨鏋渀
- **楠屾敹鏍囧噯**锛?
  - `RetrievalResult` 绫诲瀷宸插畾涔夊苟鍙簭鍒楀寲
  - ChromaStore.query() 杩斿洖缁撴灉鍖呭惈 `text` 瀛楁
  - 瀵硅緭鍏?query 鑳界敓鎴?embedding 骞惰皟鐢?VectorStore 妫€绱?
  - 杩斿洖缁撴灉鍖呭惈 `chunk_id`銆乣score`銆乣text`銆乣metadata`
  - mock EmbeddingClient 鍜?VectorStore 鏃惰兘姝ｇ‘缂栨帓璋冪敤
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_dense_retriever.py`锛坢ock embedding + vector store锛夈€?

### D3锛歋parseRetriever锛圔M25 鏌ヨ锛?
- **鐩爣**锛氬疄鐜?`sparse_retriever.py`锛氫粠 `data/db/bm25/` 杞藉叆绱㈠紩骞舵煡璇€?
- **鍓嶇疆浠诲姟**锛氶渶鍦?`BaseVectorStore` 鍜?`ChromaStore` 涓坊鍔?`get_by_ids()` 鏂规硶锛岀敤浜庢牴鎹?chunk_id 鎵归噺鑾峰彇 text 鍜?metadata
- **淇敼鏂囦欢**锛?
  - `src/libs/vector_store/base_vector_store.py`锛堟柊澧?`get_by_ids()` 鎶借薄鏂规硶锛?
  - `src/libs/vector_store/chroma_store.py`锛堝疄鐜?`get_by_ids()` 鏂规硶锛?
  - `src/core/query_engine/sparse_retriever.py`
  - `tests/unit/test_sparse_retriever.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `BaseVectorStore.get_by_ids(ids: List[str]) -> List[Dict]`锛氭牴鎹?ID 鎵归噺鑾峰彇璁板綍
  - `ChromaStore.get_by_ids(ids: List[str]) -> List[Dict]`锛氳皟鐢?ChromaDB 鐨?get 鏂规硶
  - `SparseRetriever.__init__(settings, bm25_indexer?, vector_store?)`锛氭敮鎸佷緷璧栨敞鍏ョ敤浜庢祴璇?
  - `SparseRetriever.retrieve(keywords: List[str], top_k: int, trace?) -> List[RetrievalResult]`
  - 鍐呴儴娴佺▼锛?
    1. `keywords 鈫?bm25_indexer.query(keywords, top_k) 鈫?[{chunk_id, score}]`
    2. `chunk_ids 鈫?vector_store.get_by_ids(chunk_ids) 鈫?[{id, text, metadata}]`
    3. 鍚堝苟 score 涓?text/metadata锛岀粍瑁呬负 `RetrievalResult` 鍒楄〃
  - 娉ㄦ剰锛歬eywords 鏉ヨ嚜 `QueryProcessor.process()` 鐨?`ProcessedQuery.keywords`
- **楠屾敹鏍囧噯**锛?
  - `BaseVectorStore.get_by_ids()` 鍜?`ChromaStore.get_by_ids()` 宸插疄鐜?
  - 瀵瑰凡鏋勫缓绱㈠紩鐨?fixtures 璇枡锛屽叧閿瘝妫€绱㈠懡涓鏈?chunk_id
  - 杩斿洖缁撴灉鍖呭惈瀹屾暣鐨?text 鍜?metadata
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_sparse_retriever.py`銆?

### D4锛欶usion锛圧RF 瀹炵幇锛?
- **鐩爣**锛氬疄鐜?`fusion.py`锛歊RF 铻嶅悎 dense/sparse 鎺掑悕骞惰緭鍑虹粺涓€鎺掑簭銆?
- **淇敼鏂囦欢**锛?
  - `src/core/query_engine/fusion.py`
  - `tests/unit/test_fusion_rrf.py`
- **楠屾敹鏍囧噯**锛氬鏋勯€犵殑鎺掑悕杈撳叆杈撳嚭 deterministic锛沰 鍙傛暟鍙厤缃€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_fusion_rrf.py`銆?

### D5锛欻ybridSearch 缂栨帓
- **鐩爣**锛氬疄鐜?`hybrid_search.py`锛氱紪鎺?Dense + Sparse + Fusion 鐨勫畬鏁存贩鍚堟绱㈡祦绋嬶紝骞堕泦鎴?Metadata 杩囨护閫昏緫銆?
- **鍓嶇疆渚濊禆**锛欴1锛圦ueryProcessor锛夈€丏2锛圖enseRetriever锛夈€丏3锛圫parseRetriever锛夈€丏4锛團usion锛?
- **淇敼鏂囦欢**锛?
  - `src/core/query_engine/hybrid_search.py`
  - `tests/integration/test_hybrid_search.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `HybridSearch.__init__(settings, query_processor, dense_retriever, sparse_retriever, fusion)`
  - `HybridSearch.search(query: str, top_k: int, filters?: dict, trace?) -> List[RetrievalResult]`
  - `HybridSearch._apply_metadata_filters(candidates, filters) -> List[RetrievalResult]`锛氬悗缃繃婊ゅ厹搴?
  - 鍐呴儴娴佺▼锛歚query_processor.process() 鈫?骞惰(dense.retrieve + sparse.retrieve) 鈫?fusion.fuse() 鈫?metadata_filter 鈫?Top-K`
- **楠屾敹鏍囧噯**锛?
  - 瀵?fixtures 鏁版嵁锛岃兘杩斿洖 Top-K锛堝寘鍚?chunk 鏂囨湰涓?metadata锛?
  - 鏀寔 filters 鍙傛暟锛堝 `collection`銆乣doc_type`锛夎繘琛岃繃婊?
  - Dense/Sparse 浠讳竴璺緞澶辫触鏃惰兘闄嶇骇鍒板崟璺粨鏋?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_hybrid_search.py`銆?

### D6锛歊eranker锛圕ore 灞傜紪鎺?+ fallback锛?
- **鐩爣**锛氬疄鐜?`core/query_engine/reranker.py`锛氭帴鍏?`libs.reranker` 鍚庣锛屽け璐?瓒呮椂鍥為€€ fusion 鎺掑悕銆?
- **淇敼鏂囦欢**锛?
  - `src/core/query_engine/reranker.py`
  - `config/prompts/rerank.txt`锛堜粎褰撳惎鐢?LLM Rerank 鍚庣鏃朵娇鐢級
  - `tests/unit/test_reranker_fallback.py`
- **楠屾敹鏍囧噯**锛氭ā鎷熷悗绔紓甯告椂涓嶅奖鍝嶆渶缁堣繑鍥烇紝涓旀爣璁?fallback=true銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_reranker_fallback.py`銆?

### D7锛氳剼鏈叆鍙?query.py锛堟煡璇㈠彲鐢級
- **鐩爣**锛氬疄鐜?`scripts/query.py`锛屼綔涓哄湪绾挎煡璇㈢殑鍛戒护琛屽叆鍙ｏ紝璋冪敤瀹屾暣鐨?HybridSearch + Reranker 娴佺▼骞惰緭鍑烘绱㈢粨鏋溿€?
- **鍓嶇疆渚濊禆**锛欴5锛圚ybridSearch锛夈€丏6锛圧eranker锛?
- **淇敼鏂囦欢**锛?
  - `scripts/query.py`
- **瀹炵幇鍔熻兘**锛?
  - **鍙傛暟鏀寔**锛?
    - `--query "闂"`锛氬繀濉紝鏌ヨ鏂囨湰
    - `--top-k 10`锛氬彲閫夛紝杩斿洖缁撴灉鏁伴噺锛堥粯璁?10锛?
    - `--collection xxx`锛氬彲閫夛紝闄愬畾妫€绱㈤泦鍚?
    - `--verbose`锛氬彲閫夛紝鏄剧ず鍚勯樁娈典腑闂寸粨鏋?
    - `--no-rerank`锛氬彲閫夛紝璺宠繃 Reranker 闃舵
  - **杈撳嚭鍐呭**锛?
    - 榛樿妯″紡锛歍op-K 缁撴灉锛堝簭鍙枫€乻core銆佹枃鏈憳瑕併€佹潵婧愭枃浠躲€侀〉鐮侊級
    - Verbose 妯″紡锛氶澶栨樉绀?Dense 鍙洖缁撴灉銆丼parse 鍙洖缁撴灉銆丗usion 缁撴灉銆丷erank 缁撴灉
  - **鍐呴儴娴佺▼**锛?
    1. 鍔犺浇閰嶇疆 `Settings`
    2. 鍒濆鍖栫粍浠讹紙EmbeddingClient銆乂ectorStore銆丅M25Indexer銆丷eranker锛?
    3. 鍒涘缓 `QueryProcessor`銆乣DenseRetriever`銆乣SparseRetriever`銆乣HybridSearch` 瀹炰緥
    4. 璋冪敤 `HybridSearch.search()` 鑾峰彇鍊欓€夌粨鏋?
    5. 璋冪敤 `Reranker.rerank()` 杩涜绮炬帓锛堥櫎闈?`--no-rerank`锛?
    6. 鏍煎紡鍖栬緭鍑虹粨鏋?
- **楠屾敹鏍囧噯**锛?
  - 鍛戒护琛屽彲杩愯锛歚python scripts/query.py --query "濡備綍閰嶇疆 Azure锛?`
  - 杩斿洖鏍煎紡鍖栫殑 Top-K 妫€绱㈢粨鏋?
  - `--verbose` 妯″紡鏄剧ず鍚勯樁娈典腑闂寸粨鏋滐紙渚夸簬璋冭瘯锛?
  - 鏃犳暟鎹椂杩斿洖鍙嬪ソ鎻愮ず锛堝"鏈壘鍒扮浉鍏虫枃妗ｏ紝璇峰厛杩愯 ingest.py 鎽勫彇鏁版嵁"锛?
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄨ繍琛?`python scripts/query.py --query "娴嬭瘯鏌ヨ" --verbose`锛堜緷璧栧凡鎽勫彇鐨勬暟鎹級銆?
- **涓?MCP Tool 鐨勫叧绯?*锛?
  - `scripts/query.py` 鏄紑鍙戣皟璇曠敤鐨勫懡浠よ宸ュ叿
  - `E3 query_knowledge_hub` 鏄敓浜х幆澧冪殑 MCP Tool
  - 涓よ€呭叡浜?Core 灞傞€昏緫锛圚ybridSearch + Reranker锛夛紝浣嗗叆鍙ｅ拰杈撳嚭鏍煎紡涓嶅悓

---

## 闃舵 E锛歁CP Server 灞備笌 Tools锛堢洰鏍囷細瀵瑰鍙敤鐨?MCP tools锛?

### E1锛歁CP Server 鍏ュ彛涓?Stdio 绾︽潫
- **鐩爣**锛氬疄鐜?`mcp_server/server.py`锛氶伒寰?stdout 鍙緭鍑?MCP 娑堟伅锛屾棩蹇楀埌 stderr"銆?
- **淇敼鏂囦欢**锛?
  - `src/mcp_server/server.py`
  - `tests/integration/test_mcp_server.py`
- **楠屾敹鏍囧噯**锛氬惎鍔?server 鑳藉畬鎴?initialize锛泂tderr 鏈夋棩蹇椾絾 stdout 涓嶆薄鏌撱€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_mcp_server.py`锛堝瓙杩涚▼鏂瑰紡锛夈€?

### E2锛歅rotocol Handler 鍗忚瑙ｆ瀽涓庤兘鍔涘崗鍟?
- **鐩爣**锛氬疄鐜?`mcp_server/protocol_handler.py`锛氬皝瑁?JSON-RPC 2.0 鍗忚瑙ｆ瀽锛屽鐞?`initialize`銆乣tools/list`銆乣tools/call` 涓夌被鏍稿績鏂规硶锛屽苟瀹炵幇瑙勮寖鐨勯敊璇鐞嗐€?
- **淇敼鏂囦欢**锛?
  - `src/mcp_server/protocol_handler.py`
  - `tests/unit/test_protocol_handler.py`
- **瀹炵幇瑕佺偣**锛?
  - **ProtocolHandler 绫?*锛?
    - `handle_initialize(params)` 鈫?杩斿洖 server capabilities锛堟敮鎸佺殑 tools 鍒楄〃銆佺増鏈俊鎭級
    - `handle_tools_list()` 鈫?杩斿洖宸叉敞鍐岀殑 tool schema锛坣ame, description, inputSchema锛?
    - `handle_tools_call(name, arguments)` 鈫?璺敱鍒板叿浣?tool 鎵ц锛屾崟鑾峰紓甯稿苟杞崲涓?JSON-RPC error
  - **閿欒鐮佽鑼?*锛氶伒寰?JSON-RPC 2.0锛?32600 Invalid Request, -32601 Method not found, -32602 Invalid params, -32603 Internal error锛?
  - **鑳藉姏鍗忓晢**锛氬湪 `initialize` 鍝嶅簲涓０鏄?`capabilities.tools`
- **楠屾敹鏍囧噯**锛?
  - 鍙戦€?`initialize` 璇锋眰鑳借繑鍥炴纭殑 `serverInfo` 鍜?`capabilities`
  - 鍙戦€?`tools/list` 鑳借繑鍥炲凡娉ㄥ唽 tools 鐨?schema
  - 鍙戦€?`tools/call` 鑳芥纭矾鐢卞苟杩斿洖缁撴灉鎴栬鑼冮敊璇?
  - **閿欒澶勭悊**锛氭棤鏁堟柟娉曡繑鍥?-32601锛屽弬鏁伴敊璇繑鍥?-32602锛屽唴閮ㄥ紓甯歌繑鍥?-32603 涓斾笉娉勯湶鍫嗘爤
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_protocol_handler.py`銆?

### E3锛氬疄鐜?tool锛歲uery_knowledge_hub
- **鐩爣**锛氬疄鐜?`tools/query_knowledge_hub.py`锛氳皟鐢?HybridSearch + Reranker锛屾瀯寤哄甫寮曠敤鐨勫搷搴旓紝杩斿洖 Markdown + structured citations銆?
- **鍓嶇疆渚濊禆**锛欴5锛圚ybridSearch锛夈€丏6锛圧eranker锛夈€丒1锛圫erver锛夈€丒2锛圥rotocol Handler锛?
- **淇敼鏂囦欢**锛?
  - `src/mcp_server/tools/query_knowledge_hub.py`
  - `src/core/response/response_builder.py`锛堟柊澧烇細鏋勫缓 MCP 鍝嶅簲鏍煎紡锛?
  - `src/core/response/citation_generator.py`锛堟柊澧烇細鐢熸垚寮曠敤淇℃伅锛?
  - `tests/unit/test_response_builder.py`锛堟柊澧烇級
  - `tests/integration/test_mcp_server.py`锛堣ˉ鐢ㄤ緥锛?
- **瀹炵幇绫?鍑芥暟**锛?
  - `ResponseBuilder.build(retrieval_results, query) -> MCPResponse`锛氭瀯寤?MCP 鏍煎紡鍝嶅簲
  - `CitationGenerator.generate(retrieval_results) -> List[Citation]`锛氱敓鎴愬紩鐢ㄥ垪琛?
  - `query_knowledge_hub(query, top_k?, collection?) -> MCPToolResult`锛歍ool 鍏ュ彛鍑芥暟
- **楠屾敹鏍囧噯**锛?
  - tool 杩斿洖 `content[0]` 涓哄彲璇?Markdown锛堝惈 `[1]`銆乣[2]` 绛夊紩鐢ㄦ爣娉級
  - `structuredContent.citations` 鍖呭惈 `source`/`page`/`chunk_id`/`score` 瀛楁
  - 鏃犵粨鏋滄椂杩斿洖鍙嬪ソ鎻愮ず鑰岄潪绌烘暟缁?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_mcp_server.py -k query_knowledge_hub`銆?

### E4锛氬疄鐜?tool锛歭ist_collections
- **鐩爣**锛氬疄鐜?`tools/list_collections.py`锛氬垪鍑?`data/documents/` 涓嬮泦鍚堝苟闄勫甫缁熻锛堝彲寤跺悗鍒颁笅涓€姝ワ級銆?
- **淇敼鏂囦欢**锛?
  - `src/mcp_server/tools/list_collections.py`
  - `tests/unit/test_list_collections.py`
- **楠屾敹鏍囧噯**锛氬 fixtures 涓殑鐩綍缁撴瀯鑳借繑鍥為泦鍚堝悕鍒楄〃銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_list_collections.py`銆?

### E5锛氬疄鐜?tool锛歡et_document_summary
- **鐩爣**锛氬疄鐜?`tools/get_document_summary.py`锛氭寜 doc_id 杩斿洖 title/summary/tags锛堝彲鍏堜粠 metadata/缂撳瓨鍙栵級銆?
- **淇敼鏂囦欢**锛?
  - `src/mcp_server/tools/get_document_summary.py`
  - `tests/unit/test_get_document_summary.py`
- **楠屾敹鏍囧噯**锛氬涓嶅瓨鍦?doc_id 杩斿洖瑙勮寖閿欒锛涘瓨鍦ㄦ椂杩斿洖缁撴瀯鍖栦俊鎭€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_get_document_summary.py`銆?

### E6锛氬妯℃€佽繑鍥炵粍瑁咃紙Text + Image锛?
- **鐩爣**锛氬疄鐜?`multimodal_assembler.py`锛氬懡涓?chunk 鍚?image_refs 鏃惰鍙栧浘鐗囧苟 base64 杩斿洖 ImageContent銆?
- **淇敼鏂囦欢**锛?
  - `src/core/response/multimodal_assembler.py`
  - `tests/integration/test_mcp_server.py`锛堣ˉ鍥惧儚杩斿洖鐢ㄤ緥锛?
- **楠屾敹鏍囧噯**锛氳繑鍥?content 涓寘鍚?image type锛宮imeType 姝ｇ‘锛宒ata 涓?base64 瀛楃涓层€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_mcp_server.py -k image`銆?

---

## 闃舵 F锛歍race 鍩虹璁炬柦涓庢墦鐐癸紙鐩爣锛欼ngestion + Query 鍙岄摼璺彲杩借釜锛?

### F1锛歍raceContext 澧炲己锛坒inish + 鑰楁椂缁熻 + trace_type锛?
- **鐩爣**锛氬寮哄凡鏈夌殑 `TraceContext`锛圕5 宸插疄鐜板熀纭€鐗堬級锛屾坊鍔?`finish()` 鏂规硶銆佽€楁椂缁熻銆乣trace_type` 瀛楁锛堝尯鍒?query/ingestion锛夈€乣to_dict()` 搴忓垪鍖栧姛鑳姐€?
- **淇敼鏂囦欢**锛?
  - `src/core/trace/trace_context.py`锛堝寮猴細娣诲姞 trace_type/finish/elapsed_ms/to_dict锛?
  - `src/core/trace/trace_collector.py`锛堟柊澧烇細鏀堕泦骞舵寔涔呭寲 trace锛?
  - `tests/unit/test_trace_context.py`锛堣ˉ鍏?finish/to_dict 鐩稿叧娴嬭瘯锛?
- **瀹炵幇绫?鍑芥暟**锛?
  - `TraceContext.__init__(trace_type: str = "query")`锛氭敮鎸?`"query"` 鎴?`"ingestion"` 绫诲瀷
  - `TraceContext.finish() -> None`锛氭爣璁?trace 缁撴潫锛岃绠楁€昏€楁椂
  - `TraceContext.elapsed_ms(stage_name?) -> float`锛氳幏鍙栨寚瀹氶樁娈垫垨鎬昏€楁椂
  - `TraceContext.to_dict() -> dict`锛氬簭鍒楀寲涓哄彲 JSON 杈撳嚭鐨勫瓧鍏革紙鍚?trace_type锛?
  - `TraceCollector.collect(trace: TraceContext) -> None`锛氭敹闆?trace 骞惰Е鍙戞寔涔呭寲
- **楠屾敹鏍囧噯**锛?
  - `record_stage` 杩藉姞闃舵鏁版嵁锛堝凡鏈夛級
  - `finish()` 鍚?`to_dict()` 杈撳嚭鍖呭惈 `trace_id`銆乣trace_type`銆乣started_at`銆乣finished_at`銆乣total_elapsed_ms`銆乣stages`
  - 杈撳嚭 dict 鍙洿鎺?`json.dumps()` 搴忓垪鍖?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_trace_context.py`銆?


### F2锛氱粨鏋勫寲鏃ュ織 logger锛圝SON Lines锛?
- **鐩爣**锛氬寮?`observability/logger.py`锛屾敮鎸?JSON Lines 鏍煎紡杈撳嚭锛屽苟瀹炵幇 trace 鎸佷箙鍖栧埌 `logs/traces.jsonl`銆?
- **淇敼鏂囦欢**锛?
  - `src/observability/logger.py`锛堝寮猴細娣诲姞 JSONFormatter + FileHandler锛?
  - `tests/unit/test_jsonl_logger.py`
- **瀹炵幇绫?鍑芥暟**锛?
  - `JSONFormatter`锛氳嚜瀹氫箟 logging Formatter锛岃緭鍑?JSON 鏍煎紡
  - `get_trace_logger() -> logging.Logger`锛氳幏鍙栭厤缃簡 JSON Lines 杈撳嚭鐨?logger
  - `write_trace(trace_dict: dict) -> None`锛氬皢 trace 瀛楀吀鍐欏叆 `logs/traces.jsonl`
- **涓?F1 鐨勫垎宸?*锛?
  - F1 璐熻矗 TraceContext 鐨勬暟鎹粨鏋勶紙鍚?`trace_type`锛夊拰 `finish()` 鏂规硶
  - F2 璐熻矗灏?`trace.to_dict()` 鐨勭粨鏋滄寔涔呭寲鍒版枃浠?
- **楠屾敹鏍囧噯**锛氬啓鍏ヤ竴鏉?trace 鍚庢枃浠舵柊澧炰竴琛屽悎娉?JSON锛屽寘鍚?`trace_type` 瀛楁銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_jsonl_logger.py`銆?

### F3锛氬湪 Query 閾捐矾鎵撶偣
- **鐩爣**锛氬湪 HybridSearch/Rerank 涓敞鍏?TraceContext锛坄trace_type="query"`锛夛紝鍒╃敤 B 闃舵鎶借薄鎺ュ彛涓鐣欑殑 `trace` 鍙傛暟锛屾樉寮忚皟鐢?`trace.record_stage()` 璁板綍鍚勯樁娈垫暟鎹€?
- **鍓嶇疆渚濊禆**锛欴5锛圚ybridSearch锛夈€丏6锛圧eranker锛夈€丗1锛圱raceContext 澧炲己锛夈€丗2锛堢粨鏋勫寲鏃ュ織锛?
- **淇敼鏂囦欢**锛?
  - `src/core/query_engine/hybrid_search.py`锛堝鍔?trace 璁板綍锛歞ense/sparse/fusion 闃舵锛?
  - `src/core/query_engine/reranker.py`锛堝鍔?trace 璁板綍锛歳erank 闃舵锛?
  - `tests/integration/test_hybrid_search.py`锛堟柇瑷€ trace 涓瓨鍦ㄥ悇闃舵锛?
- **璇存槑**锛欱 闃舵鐨勬帴鍙ｅ凡棰勭暀 `trace: TraceContext | None = None` 鍙傛暟锛屾湰浠诲姟璐熻矗鍦ㄨ皟鐢ㄦ椂浼犲叆瀹為檯鐨?TraceContext 瀹炰緥锛屽苟鍦ㄥ悇闃舵璁板綍 `method`/`provider`/`details` 瀛楁銆?
- **楠屾敹鏍囧噯**锛?
  - 涓€娆℃煡璇㈢敓鎴?trace锛屽寘鍚?`query_processing`/`dense_retrieval`/`sparse_retrieval`/`fusion`/`rerank` 闃舵
  - 姣忎釜闃舵璁板綍 `elapsed_ms` 鑰楁椂瀛楁鍜?`method` 瀛楁
  - `trace.to_dict()` 涓?`trace_type == "query"`
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_hybrid_search.py`銆?

### F4锛氬湪 Ingestion 閾捐矾鎵撶偣
- **鐩爣**锛氬湪 IngestionPipeline 涓敞鍏?TraceContext锛坄trace_type="ingestion"`锛夛紝璁板綍鍚勬憚鍙栭樁娈电殑澶勭悊鏁版嵁銆?
- **鍓嶇疆渚濊禆**锛欳5锛圥ipeline锛夈€丗1锛圱raceContext 澧炲己锛夈€丗2锛堢粨鏋勫寲鏃ュ織锛?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/pipeline.py`锛堝鍔?trace 浼犻€掞細load/split/transform/embed/upsert 闃舵锛?
  - `tests/integration/test_ingestion_pipeline.py`锛堟柇瑷€ trace 涓瓨鍦ㄥ悇闃舵锛?
- **楠屾敹鏍囧噯**锛?
  - 涓€娆℃憚鍙栫敓鎴?trace锛屽寘鍚?`load`/`split`/`transform`/`embed`/`upsert` 闃舵
  - 姣忎釜闃舵璁板綍 `elapsed_ms`銆乣method`锛堝 markitdown/recursive/chroma锛夊拰澶勭悊璇︽儏
  - `trace.to_dict()` 涓?`trace_type == "ingestion"`
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_ingestion_pipeline.py`銆?

### F5锛歅ipeline 杩涘害鍥炶皟 (on_progress)
- **鐩爣**锛氬湪 `IngestionPipeline.run()` 鏂规硶涓柊澧炲彲閫?`on_progress` 鍥炶皟鍙傛暟锛屾敮鎸佸閮ㄥ疄鏃惰幏鍙栧鐞嗚繘搴︺€?
- **鍓嶇疆渚濊禆**锛欶4锛圛ngestion 鎵撶偣锛?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/pipeline.py`锛堝湪鍚勯樁娈佃皟鐢?`on_progress(stage_name, current, total)`锛?
  - `tests/unit/test_pipeline_progress.py`锛堟柊澧烇細楠岃瘉鍥炶皟琚纭皟鐢級
- **瀹炵幇瑕佺偣**锛?
  - 鍥炶皟绛惧悕锛歚on_progress(stage_name: str, current: int, total: int)`
  - `on_progress` 涓?`None` 鏃跺畬鍏ㄤ笉褰卞搷鐜版湁琛屼负
  - 鍚勯樁娈靛湪澶勭悊姣忎釜 batch 鎴栧畬鎴愭椂瑙﹀彂鍥炶皟
- **楠屾敹鏍囧噯**锛歅ipeline 杩愯鏃朵紶鍏?mock 鍥炶皟锛屾柇瑷€鍚勯樁娈靛潎琚皟鐢ㄤ笖鍙傛暟姝ｇ‘銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_pipeline_progress.py`銆?

---

## 闃舵 G锛氬彲瑙嗗寲绠＄悊骞冲彴 Dashboard锛堢洰鏍囷細鍏〉闈㈠畬鏁村彲瑙嗗寲绠＄悊锛?

### G1锛欴ashboard 鍩虹鏋舵瀯涓庣郴缁熸€昏椤?
- **鐩爣**锛氭惌寤?Streamlit 澶氶〉闈㈠簲鐢ㄦ鏋讹紝瀹炵幇绯荤粺鎬昏椤甸潰锛堝睍绀虹粍浠堕厤缃笌鏁版嵁缁熻锛夈€?
- **鍓嶇疆渚濊禆**锛欶1-F2锛圱race 鍩虹璁炬柦锛?
- **淇敼鏂囦欢**锛?
  - `src/observability/dashboard/app.py`锛堥噸鍐欙細澶氶〉闈㈠鑸灦鏋勶級
  - `src/observability/dashboard/pages/overview.py`锛堟柊澧烇細绯荤粺鎬昏椤甸潰锛?
  - `src/observability/dashboard/services/config_service.py`锛堟柊澧烇細閰嶇疆璇诲彇鏈嶅姟锛?
  - `scripts/start_dashboard.py`锛堟柊澧烇細Dashboard 鍚姩鑴氭湰锛?
- **瀹炵幇瑕佺偣**锛?
  - `app.py` 浣跨敤 `st.navigation()` 娉ㄥ唽鍏釜椤甸潰锛堟湭瀹屾垚鐨勯〉闈㈡樉绀哄崰浣嶆彁绀猴級
  - Overview 椤甸潰锛氳鍙?`Settings` 灞曠ず缁勪欢鍗＄墖锛岃皟鐢?`ChromaStore.get_collection_stats()` 灞曠ず鏁版嵁缁熻
  - `ConfigService`锛氬皝瑁?Settings 璇诲彇锛屾牸寮忓寲缁勪欢閰嶇疆淇℃伅
- **楠屾敹鏍囧噯**锛歚streamlit run src/observability/dashboard/app.py` 鍙惎鍔紝鎬昏椤靛睍绀哄綋鍓嶉厤缃俊鎭€?
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄨ繍琛?`python scripts/start_dashboard.py` 骞堕獙璇侀〉闈㈡覆鏌撱€?

### G2锛欴ocumentManager 瀹炵幇
- **鐩爣**锛氬疄鐜?`src/ingestion/document_manager.py`锛氳法瀛樺偍鐨勬枃妗ｇ敓鍛藉懆鏈熺鐞嗭紙list/delete/stats锛夈€?
- **鍓嶇疆渚濊禆**锛欳5锛圥ipeline + 鍚勫瓨鍌ㄦā鍧楀凡灏辩华锛?
- **淇敼鏂囦欢**锛?
  - `src/ingestion/document_manager.py`锛堟柊澧烇級
  - `src/libs/vector_store/chroma_store.py`锛堝寮猴細娣诲姞 `delete_by_metadata`锛?
  - `src/ingestion/storage/bm25_indexer.py`锛堝寮猴細娣诲姞 `remove_document`锛?
  - `src/libs/loader/file_integrity.py`锛堝寮猴細娣诲姞 `remove_record` + `list_processed`锛?
  - `tests/unit/test_document_manager.py`锛堟柊澧烇級
- **瀹炵幇绫?鍑芥暟**锛?
  - `DocumentManager.__init__(chroma_store, bm25_indexer, image_storage, file_integrity)`
  - `DocumentManager.list_documents(collection?) -> List[DocumentInfo]`
  - `DocumentManager.get_document_detail(doc_id) -> DocumentDetail`
  - `DocumentManager.delete_document(source_path, collection) -> DeleteResult`
  - `DocumentManager.get_collection_stats(collection?) -> CollectionStats`
- **楠屾敹鏍囧噯**锛?
  - `list_documents` 杩斿洖宸叉憚鍏ユ枃妗ｅ垪琛紙source銆乧hunk 鏁般€佸浘鐗囨暟锛?
  - `delete_document` 鍗忚皟鍒犻櫎 Chroma + BM25 + ImageStorage + FileIntegrity 鍥涗釜瀛樺偍
  - 鍒犻櫎鍚庡啀娆?list 涓嶅寘鍚凡鍒犻櫎鏂囨。
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_document_manager.py`銆?

### G3锛氭暟鎹祻瑙堝櫒椤甸潰
- **鐩爣**锛氬疄鐜?Dashboard 鏁版嵁娴忚鍣ㄩ〉闈紙鏌ョ湅鏂囨。鍒楄〃銆丆hunk 璇︽儏銆佸浘鐗囬瑙堬級銆?
- **鍓嶇疆渚濊禆**锛欸1锛圖ashboard 鏋舵瀯锛夈€丟2锛圖ocumentManager锛?
- **淇敼鏂囦欢**锛?
  - `src/observability/dashboard/pages/data_browser.py`锛堟柊澧烇級
  - `src/observability/dashboard/services/data_service.py`锛堟柊澧烇細灏佽 ChromaStore/ImageStorage 璇诲彇锛?
- **瀹炵幇瑕佺偣**锛?
  - 鏂囨。鍒楄〃瑙嗗浘锛氬睍绀?source_path銆侀泦鍚堛€乧hunk 鏁般€佹憚鍏ユ椂闂达紱鏀寔闆嗗悎绛涢€?
  - Chunk 璇︽儏瑙嗗浘锛氱偣鍑绘枃妗ｅ睍寮€鎵€鏈?chunk锛屾樉绀哄唴瀹癸紙鍙姌鍙狅級銆乵etadata 瀛楁銆佸叧鑱斿浘鐗?
  - `DataService`锛氬皝瑁?`ChromaStore.get_by_metadata()` 鍜?`ImageStorage.list_images()` 璋冪敤
- **楠屾敹鏍囧噯**锛氬彲鍦?Dashboard 涓祻瑙堝凡鎽勫叆鐨勬枃妗ｅ拰 chunk 璇︽儏銆?
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄩ獙璇侊紙鍏?ingest 鏍蜂緥鏁版嵁锛屽啀鍦?Dashboard 娴忚锛夈€?

### G4锛欼ngestion 绠＄悊椤甸潰
- **鐩爣**锛氬疄鐜?Dashboard Ingestion 绠＄悊椤甸潰锛堟枃浠朵笂浼犺Е鍙戞憚鍙栥€佽繘搴﹀睍绀恒€佹枃妗ｅ垹闄わ級銆?
- **鍓嶇疆渚濊禆**锛欸2锛圖ocumentManager锛夈€丟3锛圖ataService锛夈€丗5锛坥n_progress 鍥炶皟锛?
- **淇敼鏂囦欢**锛?
  - `src/observability/dashboard/pages/ingestion_manager.py`锛堟柊澧烇級
- **瀹炵幇瑕佺偣**锛?
  - 鏂囦欢涓婁紶锛歚st.file_uploader` 閫夋嫨鏂囦欢 + 闆嗗悎閫夋嫨
  - 鎽勫彇瑙﹀彂锛氳皟鐢?`IngestionPipeline.run(on_progress=...)` + `st.progress()` 瀹炴椂杩涘害
  - 鏂囨。鍒犻櫎锛氬湪鏂囨。鍒楄〃涓彁渚涘垹闄ゆ寜閽紝璋冪敤 `DocumentManager.delete_document()`
- **楠屾敹鏍囧噯**锛氬彲鍦?Dashboard 涓笂浼犳枃浠惰Е鍙戞憚鍙栥€佺湅鍒板疄鏃惰繘搴︽潯銆佸垹闄ゅ凡鏈夋枃妗ｃ€?
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄩ獙璇侊紙涓婁紶 PDF 鈫?瑙傚療杩涘害 鈫?鍒犻櫎 鈫?纭宸茬Щ闄わ級銆?

### G5锛欼ngestion 杩借釜椤甸潰
- **鐩爣**锛氬疄鐜?Dashboard Ingestion 杩借釜椤甸潰锛堟憚鍙栧巻鍙插垪琛ㄣ€侀樁娈佃€楁椂鐎戝竷鍥撅級銆?
- **鍓嶇疆渚濊禆**锛欶4锛圛ngestion 鎵撶偣锛夈€丟1锛圖ashboard 鏋舵瀯锛?
- **淇敼鏂囦欢**锛?
  - `src/observability/dashboard/pages/ingestion_traces.py`锛堟柊澧烇級
  - `src/observability/dashboard/services/trace_service.py`锛堟柊澧烇細瑙ｆ瀽 traces.jsonl锛?
- **瀹炵幇瑕佺偣**锛?
  - 鍘嗗彶鍒楄〃锛氭寜鏃堕棿鍊掑簭灞曠ず `trace_type == "ingestion"` 璁板綍
  - 璇︽儏椤碉細妯悜鏉″舰鍥惧睍绀?load/split/transform/embed/upsert 鑰楁椂鍒嗗竷
  - `TraceService`锛氳鍙?`logs/traces.jsonl`锛岃В鏋愪负 Trace 瀵硅薄鍒楄〃
- **楠屾敹鏍囧噯**锛氭墽琛?ingest 鍚庯紝Dashboard 鏄剧ず瀵瑰簲鐨勮拷韪褰曚笌鑰楁椂鐎戝竷鍥俱€?
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄩ獙璇侊紙鍏?ingest 鈫?鎵撳紑 Dashboard 鈫?鏌ョ湅杩借釜锛夈€?

### G6锛歈uery 杩借釜椤甸潰
- **鐩爣**锛氬疄鐜?Dashboard Query 杩借釜椤甸潰锛堟煡璇㈠巻鍙层€丏ense/Sparse 瀵规瘮銆丷erank 鍙樺寲锛夈€?
- **鍓嶇疆渚濊禆**锛欶3锛圦uery 鎵撶偣锛夈€丟1锛圖ashboard 鏋舵瀯锛夈€丟5锛圱raceService 宸插疄鐜帮級
- **淇敼鏂囦欢**锛?
  - `src/observability/dashboard/pages/query_traces.py`锛堟柊澧烇級
- **瀹炵幇瑕佺偣**锛?
  - 鍘嗗彶鍒楄〃锛氭寜鏃堕棿鍊掑簭灞曠ず `trace_type == "query"` 璁板綍锛屾敮鎸佹寜 Query 鍏抽敭璇嶆悳绱?
  - 璇︽儏椤碉細鑰楁椂鐎戝竷鍥?+ Dense vs Sparse 骞跺垪瀵规瘮 + Rerank 鍓嶅悗鎺掑悕鍙樺寲
- **楠屾敹鏍囧噯**锛氭墽琛?query 鍚庯紝Dashboard 鏄剧ず鏌ヨ杩借釜璇︽儏涓庡悇闃舵瀵规瘮銆?
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄩ獙璇侊紙鍏?query 鈫?鎵撳紑 Dashboard 鈫?鏌ョ湅杩借釜锛夈€?

---

## 闃舵 H锛氳瘎浼颁綋绯伙紙鐩爣锛氬彲鎻掓嫈璇勪及 + 鍙噺鍖栧洖褰掞級

### H1锛歊agasEvaluator 瀹炵幇
- **鐩爣**锛氬疄鐜?`ragas_evaluator.py`锛氬皝瑁?Ragas 妗嗘灦锛屽疄鐜?`BaseEvaluator` 鎺ュ彛銆?
- **淇敼鏂囦欢**锛?
  - `src/observability/evaluation/ragas_evaluator.py`锛堟柊澧烇級
  - `src/libs/evaluator/evaluator_factory.py`锛堟敞鍐?ragas provider锛?
  - `tests/unit/test_ragas_evaluator.py`锛堟柊澧烇級
- **瀹炵幇绫?鍑芥暟**锛?
  - `RagasEvaluator(BaseEvaluator)`锛氬疄鐜?`evaluate()` 鏂规硶
  - 鏀寔鎸囨爣锛欶aithfulness, Answer Relevancy, Context Precision
  - 浼橀泤闄嶇骇锛歊agas 鏈畨瑁呮椂鎶涘嚭鏄庣‘鐨?`ImportError` 鎻愮ず
- **楠屾敹鏍囧噯**锛歮ock LLM 鐜涓嬶紝`evaluate()` 杩斿洖鍖呭惈 faithfulness/answer_relevancy 鐨?metrics 瀛楀吀銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_ragas_evaluator.py`銆?

### H2锛欳ompositeEvaluator 瀹炵幇
- **鐩爣**锛氬疄鐜?`composite_evaluator.py`锛氱粍鍚堝涓?Evaluator 骞惰鎵ц锛屾眹鎬荤粨鏋溿€?
- **淇敼鏂囦欢**锛?
  - `src/observability/evaluation/composite_evaluator.py`锛堟柊澧烇級
  - `tests/unit/test_composite_evaluator.py`锛堟柊澧烇級
- **瀹炵幇绫?鍑芥暟**锛?
  - `CompositeEvaluator.__init__(evaluators: List[BaseEvaluator])`
  - `CompositeEvaluator.evaluate() -> dict`锛氬苟琛屾墽琛屾墍鏈?evaluator锛屽悎骞?metrics
  - 閰嶇疆椹卞姩锛歚evaluation.backends: [ragas, custom]` 鈫?宸ュ巶鑷姩缁勫悎
- **楠屾敹鏍囧噯**锛氶厤缃袱涓?evaluator 鏃讹紝杩斿洖鐨?metrics 鍖呭惈涓よ€呯殑鎸囨爣銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/unit/test_composite_evaluator.py`銆?

### H3锛欵valRunner + Golden Test Set
- **鐩爣**锛氬疄鐜?`eval_runner.py`锛氳鍙?`tests/fixtures/golden_test_set.json`锛岃窇 retrieval 骞朵骇鍑?metrics銆?
- **鍓嶇疆渚濊禆**锛欴5锛圚ybridSearch锛夈€丠1-H2锛堣瘎浼板櫒锛?
- **淇敼鏂囦欢**锛?
  - `src/observability/evaluation/eval_runner.py`锛堟柊澧烇級
  - `tests/fixtures/golden_test_set.json`锛堟柊澧烇細榛勯噾娴嬭瘯闆嗭級
  - `scripts/evaluate.py`锛堟柊澧烇細璇勪及杩愯鑴氭湰锛?
- **瀹炵幇绫?鍑芥暟**锛?
  - `EvalRunner.__init__(settings, hybrid_search, evaluator)`
  - `EvalRunner.run(test_set_path) -> EvalReport`锛氳繍琛岃瘎浼板苟杩斿洖鎶ュ憡
  - `EvalReport`锛氬寘鍚?hit_rate, mrr, 鍚?query 缁撴灉璇︽儏
- **golden_test_set.json 鏍煎紡**锛?
  ```json
  {
    "test_cases": [
      {
        "query": "濡備綍閰嶇疆 Azure OpenAI锛?,
        "expected_chunk_ids": ["chunk_abc_001", "chunk_abc_002"],
        "expected_sources": ["config_guide.pdf"]
      }
    ]
  }
  ```
- **楠屾敹鏍囧噯**锛歚python scripts/evaluate.py` 鍙繍琛岋紝杈撳嚭 metrics銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/integration/test_hybrid_search.py` 鎴?`python scripts/evaluate.py`銆?

### H4锛氳瘎浼伴潰鏉块〉闈?
- **鐩爣**锛氬疄鐜?Dashboard 璇勪及闈㈡澘椤甸潰锛堣繍琛岃瘎浼般€佹煡鐪嬫寚鏍囥€佸巻鍙插姣旓級銆?
- **鍓嶇疆渚濊禆**锛欻3锛圗valRunner锛夈€丟1锛圖ashboard 鏋舵瀯锛?
- **淇敼鏂囦欢**锛?
  - `src/observability/dashboard/pages/evaluation_panel.py`锛堝疄鐜帮細鏇挎崲鍗犱綅鎻愮ず锛?
- **瀹炵幇瑕佺偣**锛?
  - 閫夋嫨璇勪及鍚庣涓?golden test set
  - 鐐瑰嚮杩愯锛屽睍绀鸿瘎浼扮粨鏋滐紙hit_rate銆乵rr銆佸悇 query 鏄庣粏锛?
  - 鍙€夛細鍘嗗彶璇勪及缁撴灉瀵规瘮鍥?
- **楠屾敹鏍囧噯**锛氬彲鍦?Dashboard 涓繍琛岃瘎浼板苟鏌ョ湅鎸囨爣銆?
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄩ獙璇併€?

### H5锛歊ecall 鍥炲綊娴嬭瘯锛圗2E锛?
- **鐩爣**锛氬疄鐜?`tests/e2e/test_recall.py`锛氬熀浜?golden set 鍋氭渶灏忓彫鍥為槇鍊硷紙渚嬪 hit@k锛夈€?
- **鍓嶇疆渚濊禆**锛欻3锛圗valRunner + golden_test_set锛?
- **淇敼鏂囦欢**锛?
  - `tests/e2e/test_recall.py`锛堟柊澧烇級
  - `tests/fixtures/golden_test_set.json`锛堣ˉ榻愯嫢骞叉潯锛?
- **楠屾敹鏍囧噯**锛歨it@k 杈惧埌闃堝€硷紙闃堝€煎啓姝诲湪娴嬭瘯閲岋紝渚夸簬鍥炲綊锛夈€?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/e2e/test_recall.py`銆?

---

## 闃舵 I锛氱鍒扮楠屾敹涓庢枃妗ｆ敹鍙ｏ紙鐩爣锛氬紑绠卞嵆鐢ㄧ殑"鍙鐜?宸ョ▼锛?

### I1锛欵2E锛歁CP Client 渚ц皟鐢ㄦā鎷?
- **鐩爣**锛氬疄鐜?`tests/e2e/test_mcp_client.py`锛氫互瀛愯繘绋嬪惎鍔?server锛屾ā鎷?tools/list + tools/call銆?
- **淇敼鏂囦欢**锛?
  - `tests/e2e/test_mcp_client.py`
- **楠屾敹鏍囧噯**锛氬畬鏁磋蛋閫?query_knowledge_hub 骞惰繑鍥?citations銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/e2e/test_mcp_client.py`銆?

### I2锛欵2E锛欴ashboard 鍐掔儫娴嬭瘯
- **鐩爣**锛氶獙璇?Dashboard 鍚勯〉闈㈠湪鏈夋暟鎹椂鍙甯告覆鏌撱€佹棤 Python 寮傚父銆?
- **淇敼鏂囦欢**锛?
  - `tests/e2e/test_dashboard_smoke.py`锛堟柊澧烇級
- **瀹炵幇瑕佺偣**锛?
  - 浣跨敤 Streamlit 鐨?`AppTest` 妗嗘灦杩涜鑷姩鍖栧啋鐑熸祴璇?
  - 楠岃瘉 6 涓〉闈㈠潎鍙姞杞姐€佷笉鎶涘紓甯?
- **楠屾敹鏍囧噯**锛氭墍鏈夐〉闈㈠啋鐑熸祴璇曢€氳繃銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q tests/e2e/test_dashboard_smoke.py`銆?

### I3锛氬畬鍠?README锛堣繍琛岃鏄?+ 娴嬭瘯璇存槑 + MCP 閰嶇疆 + Dashboard 浣跨敤锛?
- **鐩爣**锛氳鏂扮敤鎴疯兘鍦?10 鍒嗛挓鍐呰窇閫?ingest + query + dashboard + tests锛屽苟鑳藉湪 Copilot/Claude 涓娇鐢ㄣ€?
- **淇敼鏂囦欢**锛?
  - `README.md`
- **楠屾敹鏍囧噯**锛歊EADME 鍖呭惈浠ヤ笅绔犺妭锛?
  - **蹇€熷紑濮?*锛氬畨瑁呬緷璧栥€侀厤缃?API Key銆佽繍琛岄娆℃憚鍙?
  - **閰嶇疆璇存槑**锛歚settings.yaml` 鍚勫瓧娈靛惈涔?
  - **MCP 閰嶇疆绀轰緥**锛欸itHub Copilot `mcp.json` 涓?Claude Desktop `claude_desktop_config.json`
  - **Dashboard 浣跨敤鎸囧崡**锛氬惎鍔ㄥ懡浠ゃ€佸悇椤甸潰鍔熻兘璇存槑銆佹埅鍥剧ず渚?
  - **杩愯娴嬭瘯**锛氬崟鍏冩祴璇曘€侀泦鎴愭祴璇曘€丒2E 娴嬭瘯鍛戒护
  - **甯歌闂**锛欰PI Key 閰嶇疆銆佷緷璧栧畨瑁呫€佽繛鎺ラ棶棰樻帓鏌?
- **娴嬭瘯鏂规硶**锛氭寜 README 鎵嬪姩璧颁竴閬嶃€?

### I4锛氭竻鐞嗘帴鍙ｄ竴鑷存€э紙濂戠害娴嬭瘯琛ラ綈锛?
- **鐩爣**锛氫负鍏抽敭鎶借薄锛圴ectorStore / Reranker / Evaluator / DocumentManager锛夎ˉ榻愬绾︽祴璇曘€?
- **淇敼鏂囦欢**锛?
  - `tests/unit/test_vector_store_contract.py`锛堣ˉ榻?delete_by_metadata 杈圭晫锛?
  - `tests/unit/test_reranker_factory.py`锛堣ˉ榻愯竟鐣岋級
  - `tests/unit/test_custom_evaluator.py`锛堣ˉ榻愯竟鐣岋級
- **楠屾敹鏍囧噯**锛歚pytest -q` 鍏ㄧ豢锛屼笖 contract tests 瑕嗙洊涓昏杈撳叆杈撳嚭褰㈢姸銆?
- **娴嬭瘯鏂规硶**锛歚pytest -q`銆?

### I5锛氬叏閾捐矾 E2E 楠屾敹
- **鐩爣**锛氭墽琛屽畬鏁寸殑绔埌绔獙鏀舵祦绋嬶細ingest 鈫?query via MCP 鈫?Dashboard 鍙鍖?鈫?evaluate銆?
- **淇敼鏂囦欢**锛氭棤鏂版枃浠讹紝楠屾敹宸叉湁鍔熻兘
- **楠屾敹鏍囧噯**锛?
  - `python scripts/ingest.py --path tests/fixtures/sample_documents/ --collection test` 鎴愬姛
  - `python scripts/query.py --query "娴嬭瘯鏌ヨ" --verbose` 杩斿洖缁撴灉
  - Dashboard 鍙睍绀烘憚鍙栦笌鏌ヨ杩借釜
  - `python scripts/evaluate.py` 杈撳嚭璇勪及鎸囨爣
- **娴嬭瘯鏂规硶**锛氭墜鍔ㄥ叏閾捐矾璧伴€?+ `pytest -q` 鍏ㄩ噺娴嬭瘯銆?

---

### 浜や粯閲岀▼纰戯紙寤鸿锛?

- **M1锛堝畬鎴愰樁娈?A+B锛?*锛氬伐绋嬪彲娴?+ 鍙彃鎷旀娊璞″眰灏辩华锛屽悗缁疄鐜板彲骞惰鎺ㄨ繘銆?
- **M2锛堝畬鎴愰樁娈?C锛?*锛氱绾挎憚鍙栭摼璺彲鐢紝鑳芥瀯寤烘湰鍦扮储寮曘€?
- **M3锛堝畬鎴愰樁娈?D+E锛?*锛氬湪绾挎煡璇?+ MCP tools 鍙敤锛屽彲鍦?Copilot/Claude 涓皟鐢ㄣ€?
- **M4锛堝畬鎴愰樁娈?F锛?*锛欼ngestion + Query 鍙岄摼璺彲杩借釜锛孞SON Lines 鎸佷箙鍖栥€?
- **M5锛堝畬鎴愰樁娈?G锛?*锛氬叚椤甸潰鍙鍖栫鐞嗗钩鍙板氨缁紙璇勪及闈㈡澘涓哄崰浣嶏級锛屾暟鎹彲娴忚銆佸彲绠＄悊銆侀摼璺彲杩借釜銆?
- **M6锛堝畬鎴愰樁娈?H+I锛?*锛氳瘎浼颁綋绯诲畬鏁?+ E2E 楠屾敹閫氳繃 + 鏂囨。瀹屽杽锛屽舰鎴?闈㈣瘯/鏁欏/婕旂ず"鍙鐜伴」鐩€?



