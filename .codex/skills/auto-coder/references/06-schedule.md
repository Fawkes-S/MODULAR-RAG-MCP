## 6. 妞ゅ湱娲伴幒鎺撴埂

> **閹烘帗婀￠崢鐔峰灟閿涘牅寮楅弽鐓庮嚠姒绘劖婀?DEV_SPEC 閻ㄥ嫭鐏﹂弸鍕瀻鐏炲倷绗岄惄顔肩秿缂佹挻鐎敍?*
> 
> - **閸欘亝瀵滈張顒佹瀮濡楋綀顔曠拋陇鎯ら崷?*閿涙矮浜掔粭?5.2 閼哄倻娲拌ぐ鏇熺埐娑撹　鈧粈姘︽禒妯荤閸楁洍鈧繐绱濆В蹇庣濮濄儵鍏樼憰浣告躬閺傚洣娆㈢化鑽ょ埠娑撳﹣楠囬悽鐔峰讲鐟欎礁褰夐崠鏍モ偓?
> - **1 鐏忓繑妞傛稉鈧稉顏勫讲妤犲本鏁规晶鐐哄櫤**閿涙碍鐦℃稉顏勭毈闂冭埖顔岄敍鍫氬1h閿涘鍏樿箛鍛淬€忛崥灞炬缂佹瑥鍤垾婊堢崣閺€鑸电垼閸?+ 濞村鐦弬瑙勭《閳ユ繐绱濈亸浠嬪櫤閸嬫艾鍩?TDD閵?
> - **閸忓牊澧﹂柅姘瘜闂傤厾骞嗛敍灞藉晙鐞涖儵缍堟妯款吇鐎圭偟骞?*閿涙矮绱崗鍫濅粵閳ユ粌褰茬捄鎴︹偓姘辨畱缁旑垰鍩岀粩顖濈熅瀵板嫸绱橧ngestion 閳?Retrieval 閳?MCP Tool閿涘鈧繐绱濋獮璺烘躬 Libs 鐏炲倽藟姒绘劕褰叉潻鎰攽閻ㄥ嫰绮拋銈呮倵缁旑垰鐤勯悳甯礉闁灝鍘ら崙铏瑰箛閳ユ粌褰ч張澶嬪复閸欙絾鐥呴張澶婄杽閻滄壋鈧繄娈戠粚楦挎祮閵?
> - **婢舵牠鍎存笟婵婄閸欘垱娴涢幑?閸?Mock**閿涙瓈LM/Embedding/Vision/VectorStore 閻ㄥ嫮婀＄€圭偠鐨熼悽銊ユ躬閸楁洖鍘撳ù瀣槸娑擃厺绔村瀣暏 Fake/Mock閿涘矂娉﹂幋鎰ゴ鐠囨洖鍟€瀵偓閻喎鐤勯崥搴ｎ伂閿涘牆褰查柅澶涚礆閵?

### 闂冭埖顔岄幀鏄忣潔閿涘牆銇囬梼鑸殿唽 閳?閻╊喚娈戦敍?

1. **闂冭埖顔?A閿涙艾浼愮粙瀣€囬弸鏈电瑢濞村鐦崺鍝勯獓**
   - 閻╊喚娈戦敍姘紦缁斿褰叉潻鎰攽閵嗕礁褰查柊宥囩枂閵嗕礁褰插ù瀣槸閻ㄥ嫬浼愮粙瀣€囬弸璁圭幢閸氬海鐢婚幍鈧張澶嬆侀崸妤呭厴閼虫垝浜?TDD 閺傜懓绱￠拃钘夋勾閵?
2. **闂冭埖顔?B閿涙瓈ibs 閸欘垱褰冮幏鏂跨湴閿涘湗actory + Base 閹恒儱褰?+ 姒涙顓婚崣顖濈箥鐞涘苯鐤勯悳甯礆**
  - 閻╊喚娈戦敍姘Ω閳ユ粌褰查弴鎸庡床閳ユ繂褰夐幋鎰敩閻椒绨ㄧ€圭儑绱遍獮鎯八夋鎰讲鏉╂劘顢戦惃鍕帛鐠併倕鎮楃粩顖氱杽閻滃府绱濈涵顔荤箽 Core / Ingestion 娑撳秳绮庨垾婊冨讲缂傛牞鐦ч垾婵撶礉鏉╂ê褰查崷銊ф埂鐎圭偟骞嗘晶鍐獓闁哎鈧?
3. **闂冭埖顔?C閿涙ngestion Pipeline閿涘湧DF閳墷D閳墫hunk閳墮mbedding閳壏psert閿?*
  - 閻╊喚娈戦敍姘鳖瀲缁炬寧鎲氶崣鏍懠鐠侯垵绐囬柅姘剧礉閼宠姤濡搁弽铚傜伐閺傚洦銆傞崘娆忓弳閸氭垿鍣烘惔?BM25 缁便垹绱╅獮鑸垫暜閹镐礁顤冮柌蹇嬧偓?
4. **闂冭埖顔?D閿涙瓓etrieval閿涘湒ense + Sparse + RRF + 閸欘垶鈧?Rerank閿?*
  - 閻╊喚娈戦敍姘躬缁炬寧鐓＄拠銏ゆ懠鐠侯垵绐囬柅姘剧礉瀵版鍩?Top-K chunks閿涘牆鎯堝鏇犳暏娣団剝浼呴敍澶涚礉楠炶泛鍙挎径鍥┣旂€规艾娲栭柅鈧粵鏍殣閵?
5. **闂冭埖顔?E閿涙瓉CP Server 鐏炲倷绗?Tools 閽€钘夋勾**
   - 閻╊喚娈戦敍姘瘻 MCP 閺嶅洤鍣弳鎾苟 tools閿涘矁顔€ Copilot/Claude 閸欘垳娲块幒銉ㄧ殶閻劍鐓＄拠銏ｅ厴閸旀稏鈧?
6. **闂冭埖顔?F閿涙瓖race 閸╄櫣顢呯拋鐐煢娑撳孩澧﹂悙?*
   - 閻╊喚娈戦敍姘杻瀵?TraceContext閿涘苯鐤勯悳鎵波閺嬪嫬瀵查弮銉ョ箶閹镐椒绠欓崠鏍电礉閸?Ingestion + Query 閸欏矂鎽肩捄顖涘ⅵ閻愮櫢绱濆ǎ璇插 Pipeline 鏉╂稑瀹抽崶鐐剁殶閵?
7. **闂冭埖顔?G閿涙艾褰茬憴鍡楀缁狅紕鎮婇獮鍐插酱 Dashboard**
   - 閻╊喚娈戦敍姘儗瀵?Streamlit 閸忣參銆夐棃銏㈩吀閻炲棗閽╅崣甯礄缁崵绮洪幀鏄忣潔 / 閺佺増宓佸ù蹇氼潔 / Ingestion 缁狅紕鎮?/ Ingestion 鏉╁€熼嚋 / Query 鏉╁€熼嚋 / 鐠囧嫪鍙婇崡鐘辩秴閿涘绱濈€圭偟骞?DocumentManager 鐠恒劌鐡ㄩ崒銊ュ礂鐠嬪啨鈧?
8. **闂冭埖顔?H閿涙俺鐦庢导棰佺秼缁?*
   - 閻╊喚娈戦敍姘杽閻?RagasEvaluator + CompositeEvaluator + EvalRunner閿涘苯鎯庨悽銊ㄧ槑娴间即娼伴弶鍧椼€夐棃顫礉瀵よ櫣鐝?golden test set 閸ョ偛缍婇崺铏瑰殠閵?
9. **闂冭埖顔?I閿涙氨顏崚鎵伂妤犲本鏁规稉搴㈡瀮濡楋絾鏁归崣?*
   - 閻╊喚娈戦敍姘乘夋?E2E 濞村鐦敍鍦P Client 濡剝瀚?+ Dashboard 閸愭帞鍎敍澶涚礉鐎瑰苯鏉?README閿涘苯鍙忛柧鎹愮熅妤犲本鏁归敍宀€鈥樻穱婵冣偓婊冪磻缁犲崬宓嗛悽?+ 閸欘垰顦查悳鎵斥偓婵勨偓?


---

### 棣冩惓 鏉╂稑瀹崇捄鐔婚嚋鐞?(Progress Tracking)

> **閻樿埖鈧浇顕╅弰?*閿涙瓪[ ]` 閺堫亜绱戞慨?| `[~]` 鏉╂稖顢戞稉?| `[x]` 瀹告彃鐣幋?
> 
> **閺囧瓨鏌婇弮鍫曟？**閿涙碍鐦＄€瑰本鍨氭稉鈧稉顏勭摍娴犺濮熼崥搴㈡纯閺傛澘顕惔鏃傚Ц閹?

#### 闂冭埖顔?A閿涙艾浼愮粙瀣€囬弸鏈电瑢濞村鐦崺鍝勯獓

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| A1 | 閸掓繂顫愰崠鏍窗瑜版洘鐖叉稉搴㈡付鐏忓繐褰叉潻鎰攽閸忋儱褰?| [x] | 2026-03-20 | compileall/import checks passed |
| A2 | 瀵洖鍙?pytest 楠炶泛缂撶粩瀣ゴ鐠囨洜娲拌ぐ鏇犲鐎?| [x] | 2026-03-20 | pytest smoke and full run passed |
| A3 | 闁板秶鐤嗛崝鐘烘祰娑撳孩鐗庢宀嬬礄Settings閿?| [x] | 2026-03-20 | settings loader/validation + tests passed |

#### 闂冭埖顔?B閿涙瓈ibs 閸欘垱褰冮幏鏂跨湴

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| B1 | LLM 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?| [x] | 2026-03-20 | BaseLLM + LLMFactory + fake-provider tests passed |
| B2 | Embedding 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?| [x] | 2026-03-20 | BaseEmbedding + EmbeddingFactory + stable fake-vector tests passed |
| B3 | Splitter 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?| [x] | 2026-03-20 | BaseSplitter + SplitterFactory + provider routing tests passed |
| B4 | VectorStore 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?| [x] | 2026-03-20 | BaseVectorStore + VectorStoreFactory + contract tests passed |
| B5 | Reranker 閹跺€熻杽閹恒儱褰涙稉搴′紣閸樺偊绱欓崥?None 閸ョ偤鈧偓閿?| [x] | 2026-03-20 | BaseReranker + NoneReranker + RerankerFactory + tests passed |
| B6 | Evaluator 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?| [x] | 2026-03-20 | BaseEvaluator + EvaluatorFactory + CustomEvaluator + tests passed |
| B7.1 | OpenAI-Compatible LLM 鐎圭偟骞?| [x] | 2026-03-22 | OpenAI/Azure/DeepSeek providers + mock-http smoke tests passed |
| B7.2 | Ollama LLM 鐎圭偟骞?| [x] | 2026-03-22 | OllamaLLM + factory routing + mock-http tests passed |
| B7.3 | OpenAI & Azure Embedding 鐎圭偟骞?| [x] | 2026-03-22 | OpenAIEmbedding/AzureEmbedding + factory routing + mock-http tests passed |
| B7.4 | Ollama Embedding 鐎圭偟骞?| [x] | 2026-03-24 | OllamaEmbedding + factory routing + mock-http tests passed |
| B7.5 | Recursive Splitter 姒涙顓荤€圭偟骞?| [x] | 2026-03-24 | RecursiveSplitter + factory routing + markdown-structure tests passed |
| B7.6 | ChromaStore 姒涙顓荤€圭偟骞?| [x] | 2026-03-24 | ChromaStore + factory routing + roundtrip integration tests passed閿涘牆鎯堥崣妤呮閻滎垰顣ㄩ懛顏勫З闂勫秶楠囬敍?|
| B7.7 | LLM Reranker 鐎圭偟骞?| [x] | 2026-03-24 | LLMReranker + prompt loading + fallback signal + schema validation + tests passed |
| B7.8 | Cross-Encoder Reranker 鐎圭偟骞?| [x] | 2026-03-25 | CrossEncoderReranker + fallback signal + factory routing + mock-scorer tests passed |
| B8 | Vision LLM 閹跺€熻杽閹恒儱褰涙稉搴′紣閸樺倿娉﹂幋?| [x] | 2026-03-25 | BaseVisionLLM + LLMFactory.create_vision_llm + routing tests passed |
| B9 | Azure Vision LLM 鐎圭偟骞?| [x] | 2026-03-25 | AzureVisionLLM + image path/base64 + compression hook + error-code tests passed |
| B9.1 | DashScope Vision LLM閿涘湨wen3.5-Plus閿涘鐤勯悳?| [x] | 2026-03-25 | DashScopeVisionLLM + factory routing + image path/base64 + compression/error tests passed |

#### 闂冭埖顔?C閿涙ngestion Pipeline MVP

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| C1 | 鐎规矮绠熼弽绋跨妇閺佺増宓佺猾璇茬€?婵傛垹瀹抽敍鍦杘cument/Chunk/ChunkRecord閿?| [x] | 2026-03-26 | core.types contracts + metadata/images validation + serialization tests passed |
| C2 | 閺傚洣娆㈢€瑰本鏆ｉ幀褎顥呴弻銉礄SHA256閿?| [x] | 2026-03-26 | SQLiteIntegrityChecker + WAL + skip閸掋倕鐣?+ 楠炶泛褰傞崘娆忓弳 tests passed |
| C3 | Loader 閹跺€熻杽閸╄櫣琚稉?PDF Loader | [x] | 2026-03-26 | BaseLoader + PdfLoader + image extraction/placeholder + degrade path tests passed |
| C4 | Splitter 闂嗗棙鍨氶敍鍫ｇ殶閻?Libs閿?| [x] | 2026-03-27 | DocumentChunker 闁倿鍘ょ仦?+ 閸ュ墽澧栭幐澶愭付閸掑棗褰?+ 闁板秶鐤嗘す鍗炲З閸掑洤鍨?+ 閸氬牆鎮撳ù瀣槸闁俺绻?|
| C5 | Transform 閸╄櫣琚?+ ChunkRefiner | [x] | 2026-03-29 | BaseTransform + ChunkRefiner(rule+LLM+fallback) + TraceContext(min) + 27 unit tests passed; real-LLM integration tests added (env key required) |
| C6 | MetadataEnricher | [x] | 2026-03-30 | MetadataEnricher(rule+LLM+fallback) + trace缂佺喕顓?+ contract tests(閸氼偆婀＄€规看LM閻劋绶? |
| C7 | ImageCaptioner | [x] | 2026-03-30 | ImageCaptioner + fallback + prompt + tests passed |
| C8 | DenseEncoder | [x] | 2026-03-30 | DenseEncoder(batch encode + contract checks + tests passed) |
| C9 | SparseEncoder | [x] | 2026-03-31 | SparseEncoder(BM25 term weights + empty-text contract + tests passed) |
| C10 | BatchProcessor | [x] | 2026-04-03 | BatchProcessor(batch split + dense/sparse orchestration + per-batch timing + tests passed) |
| C11 | BM25Indexer閿涘牆鈧帗甯撶槐銏犵穿+IDF鐠侊紕鐣婚敍?| [x] | 2026-04-03 | BM25Indexer(build/load/query + IDF formula + incremental/rebuild + tests passed) |
| C12 | VectorUpserter閿涘牆绠撶粵濉絧sert閿?| [x] | 2026-04-03 | VectorUpserter(stable id + idempotent upsert + trace stage) + tests passed |
| C13 | ImageStorage閿涘牆娴橀悧鍥х摠閸?SQLite缁便垹绱╅敍?| [x] | 2026-04-04 | ImageStorage(file save + SQLite index + WAL + collection/doc_hash filters) + tests passed |
| C14 | Pipeline 缂傛牗甯撻敍鍦P 娑撹尪鎹ｉ弶銉礆 | [x] | 2026-04-04 | IngestionPipeline(end-to-end orchestration + stage error wrapping + incremental skip/force) + integration tests passed |
| C15 | 閼存碍婀伴崗銉ュ經 ingest.py | [x] | 2026-04-04 | scripts/ingest.py(cli path/collection/force + dir batch pdf) + tests/e2e/test_data_ingestion.py passed |

#### 闂冭埖顔?D閿涙瓓etrieval MVP

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| D1 | QueryProcessor閿涘牆鍙ч柨顔跨槤閹绘劕褰?+ filters閿?| [x] | 2026-04-04 | QueryProcessor(鐟欏嫬鍨崚鍡氱槤+閸嬫粎鏁ょ拠?閸愬懓浠坒ilters鐟欙絾鐎? + tests/unit/test_query_processor.py passed |
| D2 | DenseRetriever閿涘牐鐨熼悽?VectorStore.query閿?| [x] | 2026-04-05 | RetrievalResult + DenseRetriever(embed->query缂傛牗甯? + tests/unit/test_dense_retriever.py passed |
| D3 | SparseRetriever閿涘湐M25 閺屻儴顕楅敍?| [x] | 2026-05-27 | Base/Chroma get_by_ids + SparseRetriever(BM25->濮濓絾鏋冮崶鐐诧綖) + tests/unit/test_sparse_retriever.py passed |
| D4 | RRF Fusion | [x] | 2026-05-29 | RRFFusion(deterministic + configurable k) + tests/unit/test_fusion_rrf.py passed |
| D5 | HybridSearch 缂傛牗甯?| [x] | 2026-05-30 | HybridSearch(query->dense/sparse->RRF->post-filter) + tests/integration/test_hybrid_search.py passed |
| D6 | Reranker閿涘湑ore 鐏炲倻绱幒?+ Fallback閿?| [x] | 2026-05-31 | Core Reranker(fallback=true + reason) + tests/unit/test_reranker_fallback.py passed |
| D7 | 閼存碍婀伴崗銉ュ經 query.py閿涘牊鐓＄拠銏犲讲閻㈩煉绱?| [x] | 2026-05-31 | scripts/query.py(cli + verbose + no-rerank + friendly-empty) verified |

#### 闂冭埖顔?E閿涙瓉CP Server 鐏炲倷绗?Tools

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| E1 | MCP Server 閸忋儱褰涙稉?Stdio 缁撅附娼?| [x] | 2026-06-05 | minimal stdio JSON-RPC server + initialize integration test passed |
| E2 | Protocol Handler 閸楀繗顔呯憴锝嗙€芥稉搴ゅ厴閸旀稑宕楅崯?| [x] | 2026-06-06 | ProtocolHandler(initialize/tools/list/tools/call + JSON-RPC errors) + tests/unit/test_protocol_handler.py passed |
| E3 | query_knowledge_hub Tool | [x] | 2026-06-06 | query tool + response builder + citations + mcp integration tests passed |
| E4 | list_collections Tool | [x] | 2026-06-06 | list_collections directory scan tool + unit tests passed |
| E5 | get_document_summary Tool | [x] | 2026-06-06 | cache-backed summary tool + MCP integration tests passed |
| E6 | 婢舵碍膩閹浇绻戦崶鐐电矋鐟佸拑绱橳ext + Image閿?| [x] | 2026-06-07 | multimodal assembler + MCP image content integration test passed |

#### 闂冭埖顔?F閿涙瓖race 閸╄櫣顢呯拋鐐煢娑撳孩澧﹂悙?

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| F1 | TraceContext 婢х偛宸遍敍鍧抜nish + 閼版妞傜紒鐔活吀 + trace_type閿?| [x] | 2026-06-07 | TraceContext(finish/elapsed/trace_type/to_dict) + tests/unit/test_trace_context.py passed |
| F2 | 缂佹挻鐎崠鏍ㄦ）韫?logger閿涘湞SON Lines閿?| [x] | 2026-06-07 | JSONL logger + TraceCollector + tests/unit/test_jsonl_logger.py passed |
| F3 | 閸?Query 闁炬崘鐭鹃幍鎾跺仯 | [x] | 2026-06-07 | query trace stages/method-provider fields + integration/unit tests passed |
| F4 | 閸?Ingestion 闁炬崘鐭鹃幍鎾跺仯 | [x] | 2026-06-08 | ingestion trace stages/method-provider fields + integration tests passed |
| F5 | Pipeline 鏉╂稑瀹抽崶鐐剁殶 (on_progress) | [x] | 2026-06-09 | pipeline on_progress callback + unit tests passed |

#### 闂冭埖顔?G閿涙艾褰茬憴鍡楀缁狅紕鎮婇獮鍐插酱 Dashboard

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| G1 | Dashboard 閸╄櫣顢呴弸鑸电€稉搴ｉ兇缂佺喐鈧槒顫嶆い?| [x] | 2026-06-09 | Streamlit婢舵岸銆夐棃銏ゎ€囬弸?+ Overview闁板秶鐤?缂佺喕顓告い?+ start_dashboard閼存碍婀?+ tests passed |
| G2 | DocumentManager 鐎圭偟骞?| [x] | 2026-06-09 | DocumentManager(list/detail/delete/stats) + Chroma metadata read/delete + tests passed |
| G3 | 閺佺増宓佸ù蹇氼潔閸ｃ劑銆夐棃?| [x] | 2026-06-10 | data_browser 妞ょ敻娼?+ DataService 閺傚洦銆?chunk/閸ュ墽澧栧ù蹇氼潔 + dashboard tests passed |
| G4 | Ingestion 缁狅紕鎮婃い鐢告桨 | [x] | 2026-06-10 | ingestion_manager 妞ょ敻娼?+ PDF 娑撳﹣绱堕幗鍕絿 + on_progress 鐎圭偞妞傛潻娑樺 + 閺傚洦銆傞崚鐘绘珟 + dashboard tests passed |
| G5 | Ingestion 鏉╁€熼嚋妞ょ敻娼?| [x] | 2026-06-11 | ingestion_traces 妞ょ敻娼?+ TraceService(JSONL鐟欙絾鐎?闂冭埖顔岄懕姘値) + dashboard tests passed |
| G6 | Query 鏉╁€熼嚋妞ょ敻娼?| [x] | 2026-06-12 | query_traces 妞ょ敻娼?+ query trace閹镐椒绠欓崠?閸婃瑩鈧顣╃憴?+ dashboard tests passed |

#### 闂冭埖顔?H閿涙俺鐦庢导棰佺秼缁?

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| H1 | RagasEvaluator 鐎圭偟骞?| [x] | 2026-06-14 | RagasEvaluator(lazy import + standardized metrics) + tests/unit/test_ragas_evaluator.py passed |
| H2 | CompositeEvaluator 鐎圭偟骞?| [x] | 2026-06-14 | CompositeEvaluator(parallel merge + evaluation.backends routing) + tests/unit/test_composite_evaluator.py passed |
| H3 | EvalRunner + Golden Test Set | [x] | 2026-06-15 | EvalRunner(golden set + retrieval metrics + evaluator adaptation) + scripts/evaluate.py + unit tests passed |
| H4 | 鐠囧嫪鍙婇棃銏℃緲妞ょ敻娼?| [x] | 2026-06-15 | evaluation_panel 妞ょ敻娼?+ Dashboard 閹恒儱鍙?+ unit tests passed |
| H5 | Recall 閸ョ偛缍婂ù瀣槸閿涘湕2E閿?| [x] | 2026-06-23 | tests/e2e/test_recall.py + H5 evaluation regression suite passed |

#### 闂冭埖顔?I閿涙氨顏崚鎵伂妤犲本鏁规稉搴㈡瀮濡楋絾鏁归崣?

| 娴犺濮熺紓鏍у娇 | 娴犺濮熼崥宥囆?| 閻樿埖鈧?| 鐎瑰本鍨氶弮銉︽埂 | 婢跺洦鏁?|
|---------|---------|------|---------|------|
| I1 | E2E閿涙瓉CP Client 娓氀嗙殶閻劍膩閹?| [x] | 2026-06-23 | tests/e2e/test_mcp_client.py + real ingest + stdio MCP client flow passed |
| I2 | E2E閿涙ashboard 閸愭帞鍎ù瀣槸 | [x] | 2026-06-23 | tests/e2e/test_dashboard_smoke.py + Streamlit AppTest six-page smoke passed |
| I3 | 鐎瑰苯鏉?README閿涘牐绻嶇悰宀冾嚛閺?+ MCP + Dashboard閿?| [x] | 2026-06-23 | README rewritten as runnable guide for quick start, settings, MCP, Dashboard, evaluation, tests, troubleshooting |
| I4 | 娓呯悊鎺ュ彛涓€鑷存€э紙濂戠害娴嬭瘯琛ラ綈锛?| [x] | 2026-06-23 | contract tests covered delete/filter/provider edges and evaluator input validation |
| I5 | 閸忋劑鎽肩捄?E2E 妤犲本鏁?| [x] | 2026-06-23 | full pytest green + ingest/query/evaluate manual chain verified |

---

### 棣冩惐 閹缍嬫潻娑樺

| 闂冭埖顔?| 閹鎹㈤崝鈩冩殶 | 瀹告彃鐣幋?| 鏉╂稑瀹?|
|------|---------|--------|------|
| 闂冭埖顔?A | 3 | 0 | 0% |
| 闂冭埖顔?B | 16 | 0 | 0% |
| 闂冭埖顔?C | 15 | 0 | 0% |
| 闂冭埖顔?D | 7 | 0 | 0% |
| 闂冭埖顔?E | 6 | 0 | 0% |
| 闂冭埖顔?F | 5 | 0 | 0% |
| 闂冭埖顔?G | 6 | 0 | 0% |
| 闂冭埖顔?H | 5 | 0 | 0% |
| 闂冭埖顔?I | 5 | 0 | 0% |
| **閹槒顓?* | **68** | **0** | **0%** |


---

## 闂冭埖顔?A閿涙艾浼愮粙瀣€囬弸鏈电瑢濞村鐦崺鍝勯獓閿涘牏娲伴弽鍥风窗閸忓牆褰茬€电厧鍙嗛敍灞藉晙閸欘垱绁寸拠鏇礆

### A1閿涙艾鍨垫慨瀣閻╊喖缍嶉弽鎴滅瑢閺堚偓鐏忓繐褰叉潻鎰攽閸忋儱褰?
- **閻╊喗鐖?*閿涙艾婀?repo 閺嶅湱娲拌ぐ鏇炲灡瀵よ櫣顑?5.2 閼哄倹澧嶆潻鎵窗瑜版洟顎囬弸鏈电瑢缁岀儤膩閸ф鏋冩禒璁圭礄閸?import閿涘鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `main.py`
  - `pyproject.toml`
  - `README.md`
  - `.gitignore`閿涘湧ython 妞ゅ湱娲伴弽鍥у櫙韫囩晫鏆愮憴鍕灟閿涙瓪__pycache__`閵嗕梗.venv`閵嗕梗.env`閵嗕梗*.pyc`閵嗕浮DE 闁板秶鐤嗙粵澶涚礆
  - `src/**/__init__.py`閿涘牊瀵滈惄顔肩秿閺嶆垼藟姒绘劧绱?
  - `config/settings.yaml`閿涘牊娓剁亸蹇撳讲鐟欙絾鐎介柊宥囩枂閿?
  - `config/prompts/image_captioning.txt`閿涘牆褰查崗鍫熸杹閸楃姳缍呴崘鍛啇閿涘苯鎮楃紒顓㈡▉濞堜絻藟閸?Prompt閿?
  - `config/prompts/chunk_refinement.txt`閿涘牆褰查崗鍫熸杹閸楃姳缍呴崘鍛啇閿涘苯鎮楃紒顓㈡▉濞堜絻藟閸?Prompt閿?
  - `config/prompts/rerank.txt`閿涘牆褰查崗鍫熸杹閸楃姳缍呴崘鍛啇閿涘苯鎮楃紒顓㈡▉濞堜絻藟閸?Prompt閿?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿涙碍妫ら敍鍫滅矌妤犮劍鐏﹂敍澶堚偓?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿涙碍妫ら敍鍫滅矌妤犮劍鐏﹂敍灞肩瑝鐎圭偟骞囨稉姘闁槒绶敍澶堚偓?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿涙矮璐熻ぐ鎾冲妞ゅ湱娲伴崚娑樼紦娑撯偓娑擃亣娅勯幏鐔哄箚婢у啯膩閸фぜ鈧?
 - **妤犲本鏁归弽鍥у櫙**閿?
  - 閻╊喖缍嶇紒鎾寸€稉?DEV_SPEC 5.2 娑撯偓閼疯揪绱欓懛鍐茬毌閹跺﹤顕惔鏃傛窗瑜版洖鍨卞鍝勫毉閺夈儻绱氶妴?
  - `config/prompts/` 閻╊喖缍嶇€涙ê婀敍灞肩瑬娑撳閲?prompt 閺傚洣娆㈤崣顖濐潶鐠囪褰囬敍鍫濆祮娴ｅ灝褰ч弰顖氬窗娴ｅ秵鏋冮張顒婄礆閵?
  - 閼宠棄顕遍崗銉ュ彠闁款噣銆婄仦鍌氬瘶閿涘牅绗岄惄顔肩秿缂佹挻鐎稉鈧稉鈧€电懓绨查敍澶涚窗
    - `python -c "import mcp_server; import core; import ingestion; import libs; import observability"`
  - 閸欘垯浜掗崥顖氬З閾忔碍瀚欓悳顖氼暔濡€虫健
- **濞村鐦弬瑙勭《**閿涙俺绻嶇悰?`python -m compileall src`閿涘牅绮庨崑姘愁嚔濞?閸欘垰顕遍崗銉︹偓褎顥呴弻銉幢pytest 閸╁搫楠囬崷?A2 瀵よ櫣鐝涢敍澶堚偓?

### A2閿涙艾绱╅崗?pytest 楠炶泛缂撶粩瀣ゴ鐠囨洜娲拌ぐ鏇犲鐎?
- **閻╊喗鐖?*閿涙艾缂撶粩?`tests/unit|integration|e2e|fixtures` 閻╊喖缍嶆稉?pytest 鏉╂劘顢戦崺鍝勯獓閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `pyproject.toml`閿涘牊鍧婇崝?pytest 闁板秶鐤嗛敍姝礶stpaths閵嗕沟arkers 缁涘绱?
  - `tests/unit/test_smoke_imports.py`
  - `tests/fixtures/sample_documents/`閿涘牊鏂?1 娑擃亝娓剁亸蹇旂壉娓氬鏋冨锝呭窗娴ｅ稄绱?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿涙碍妫ら妴?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿涙碍妫ら敍鍫熸煀婢х偟娈戦弰顖涚ゴ鐠囨洘鏋冩禒鏈电瑢 pytest 闁板秶鐤嗛敍澶堚偓?
- **妤犲本鏁归弽鍥у櫙**閿?
  - `pytest -q` 閸欘垵绻嶇悰灞借嫙闁俺绻冮妴?
  - 閼峰啿鐨?1 娑擃亜鍟嬮悜鐔哥ゴ鐠囨洩绱欐笟瀣洤 `tests/unit/test_smoke_imports.py` 閸欘亜浠涢崗鎶芥暛閸?import 閺嶏繝鐛欓敍澶堚偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_smoke_imports.py`閵?

### A3閿涙岸鍘ょ純顔煎鏉炴垝绗岄弽锟犵崣閿涘湯ettings閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳鎷岊嚢閸?`config/settings.yaml` 閻ㄥ嫰鍘ょ純顔煎鏉炶棄娅掗敍灞借嫙閸︺劌鎯庨崝銊︽閺嶏繝鐛欓崗鎶芥暛鐎涙顔岀€涙ê婀妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `main.py`閿涘牆鎯庨崝銊︽鐠嬪啰鏁?`load_settings()`閿涘瞼宸辩€涙顔岄惄瀛樺复 fail-fast 闁偓閸戠尨绱?
  - `src/observability/logger.py`閿涘牆鍘涢崡鐘辩秴閿涙碍褰佹笟?get_logger閿涘tderr 鏉堟挸鍤敍?
  - `src/core/settings.py`閿涘牊鏌婃晶鐑囩窗闂嗗棔鑵戦弨?Settings 閺佺増宓佺紒鎾寸€稉搴″鏉?閺嶏繝鐛欓柅鏄忕帆閿?
  - `config/settings.yaml`閿涘牐藟姒绘劕鐡у▓纰夌窗llm/embedding/vector_store/retrieval/rerank/evaluation/observability閿?
  - `tests/unit/test_config_loading.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `Settings`閿涘潐ataclass閿涙艾褰ч崑姘辩波閺嬪嫪绗岄張鈧亸蹇旂墡妤犲矉绱辨稉宥呮躬鏉╂瑩鍣烽崑姘崲娴ｆ洜缍夌紒?IO 閻ㄥ嫧鈧粈绗熼崝鈥冲灥婵瀵查垾婵撶礆
  - `load_settings(path: str) -> Settings`閿涘牐顕伴崣?YAML -> 鐟欙絾鐎芥稉?Settings -> 閺嶏繝鐛欒箛鍛綖鐎涙顔岄敍?
  - `validate_settings(settings: Settings) -> None`閿涘牊濡搁垾婊冪箑婵夘偄鐡у▓鍨梾閺屻儮鈧繈娉︽稉顓炲閿涘矂鏁婄拠顖欎繆閹垰瀵橀崥顐㈢摟濞堜絻鐭惧鍕剁礉娓氬顩?`embedding.provider`閿?
- **妤犲本鏁归弽鍥у櫙**閿?
  - `main.py` 閸氼垰濮╅弮鎯板厴閹存劕濮涢崝鐘烘祰 `config/settings.yaml` 楠炶埖瀣侀崚?`Settings` 鐎电钖勯妴?
  - 閸掔娀娅?缂傚搫銇戦崗鎶芥暛鐎涙顔岄弮璁圭礄娓氬顩?`embedding.provider`閿涘绱濋崥顖氬З閹?`load_settings()` 閹舵稑鍤垾婊冨讲鐠囧鏁婄拠顖椻偓婵撶礄閺勫海鈥橀幐鍥у毉缂傝櫣娈戦弰顖氭憿娑擃亜鐡у▓纰夌礆閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_config_loading.py`閵?

---

## 闂冭埖顔?B閿涙瓈ibs 閸欘垱褰冮幏鏂跨湴閿涘牏娲伴弽鍥风窗Factory 閸欘垰浼愭担婊愮礉娑撴棁鍤︾亸鎴炴箒閳ユ粓绮拋銈呮倵缁旑垪鈧繂褰茬捄鎴︹偓姘鳖伂閸掓壆顏敍?

### B1閿涙瓈LM 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?
- **閻╊喗鐖?*閿涙艾鐣炬稊?`BaseLLM` 娑?`LLMFactory`閿涘本鏁幐浣瑰瘻闁板秶鐤嗛柅澶嬪 provider閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/llm/base_llm.py`
  - `src/libs/llm/llm_factory.py`
  - `tests/unit/test_llm_factory.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseLLM.chat(messages) -> str`閿涘牊鍨ㄧ紒鐔剁 response 鐎电钖勯敍?
  - `LLMFactory.create(settings) -> BaseLLM`
- **妤犲本鏁归弽鍥у櫙**閿涙艾婀ù瀣槸闁插瞼鏁?Fake provider閿涘牊绁寸拠鏇炲敶 stub閿涘鐛欑拠浣镐紣閸樺倽鐭鹃悽閬嶁偓鏄忕帆閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_llm_factory.py`閵?

### B2閿涙mbedding 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?
- **閻╊喗鐖?*閿涙艾鐣炬稊?`BaseEmbedding` 娑?`EmbeddingFactory`閿涘本鏁幐浣瑰闁?embed閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/embedding/base_embedding.py`
  - `src/libs/embedding/embedding_factory.py`
  - `tests/unit/test_embedding_factory.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseEmbedding.embed(texts: list[str], trace: TraceContext | None = None) -> list[list[float]]`
  - `EmbeddingFactory.create(settings) -> BaseEmbedding`
- **妤犲本鏁归弽鍥у櫙**閿涙ake embedding 鏉╂柨娲栫粙鍐茬暰閸氭垿鍣洪敍灞戒紣閸樺倹瀵?provider 閸掑棙绁﹂妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_embedding_factory.py`閵?

### B3閿涙瓔plitter 閹跺€熻杽閹恒儱褰涙稉搴′紣閸?
- **閻╊喗鐖?*閿涙艾鐣炬稊?`BaseSplitter` 娑?`SplitterFactory`閿涘本鏁幐浣风瑝閸氬苯鍨忛崚鍡欑摜閻ｃ儻绱橰ecursive/Semantic/Fixed閿涘鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/splitter/base_splitter.py`
  - `src/libs/splitter/splitter_factory.py`
  - `tests/unit/test_splitter_factory.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseSplitter.split_text(text: str, trace: TraceContext | None = None) -> List[str]`
  - `SplitterFactory.create(settings) -> BaseSplitter`
- **妤犲本鏁归弽鍥у櫙**閿涙actory 閼宠姤鐗撮幑顕€鍘ょ純顔跨箲閸ョ偘绗夐崥宀€琚崹瀣畱 Splitter 鐎圭偘绶ラ敍鍫熺ゴ鐠囨洑鑵戦崣顖滄暏 Fake 鐎圭偟骞囬敍澶堚偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_splitter_factory.py`閵?

### B4閿涙瓘ectorStore 閹跺€熻杽閹恒儱褰涙稉搴′紣閸樺偊绱欓崗鍫濈暰娑斿顨栫痪锔肩礆
- **閻╊喗鐖?*閿涙艾鐣炬稊?`BaseVectorStore` 娑?`VectorStoreFactory`閿涘苯鍘涙稉宥嗗复閻喎鐤?DB閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/vector_store/base_vector_store.py`
  - `src/libs/vector_store/vector_store_factory.py`
  - `tests/unit/test_vector_store_contract.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseVectorStore.upsert(records, trace: TraceContext | None = None)`
  - `BaseVectorStore.query(vector, top_k, filters, trace: TraceContext | None = None)`
- **妤犲本鏁归弽鍥у櫙**閿涙艾顨栫痪锔界ゴ鐠囨洩绱檆ontract test閿涘瀹抽弶鐔荤翻閸忋儴绶崙?shape閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_vector_store_contract.py`閵?

### B5閿涙瓓eranker 閹跺€熻杽閹恒儱褰涙稉搴′紣閸樺偊绱欓崥?None 閸ョ偤鈧偓閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`BaseReranker`閵嗕梗RerankerFactory`閿涘本褰佹笟?`NoneReranker` 娴ｆ粈璐熸妯款吇閸ョ偤鈧偓閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/reranker/base_reranker.py`
  - `src/libs/reranker/reranker_factory.py`
  - `tests/unit/test_reranker_factory.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseReranker.rerank(query, candidates, trace: TraceContext | None = None) -> ranked_candidates`
  - `NoneReranker`閿涘牅绻氶幐浣稿斧妞ゅ搫绨敍?
- **妤犲本鏁归弽鍥у櫙**閿涙瓬ackend=none 閺冩湹绗夋导姘暭閸欐ɑ甯撴惔蹇ョ幢閺堫亞鐓?backend 閺勫海鈥橀幎銉╂晩閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_reranker_factory.py`閵?

### B6閿涙valuator 閹跺€熻杽閹恒儱褰涙稉搴′紣閸樺偊绱欓崗鍫濅粵閼奉亜鐣炬稊澶庝氦闁插繑瀵氶弽鍥风礆
- **閻╊喗鐖?*閿涙艾鐣炬稊?`BaseEvaluator`閵嗕梗EvaluatorFactory`閿涘苯鐤勯悳鐗堟付鐏?`CustomEvaluator`閿涘牅绶ユ俊?hit_rate/mrr閿涘鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/evaluator/base_evaluator.py`
  - `src/libs/evaluator/evaluator_factory.py`
  - `src/libs/evaluator/custom_evaluator.py`
  - `tests/unit/test_custom_evaluator.py`
- **妤犲本鏁归弽鍥у櫙**閿涙俺绶崗?query + retrieved_ids + golden_ids 閼冲€熺翻閸戣櫣菙鐎?metrics閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_custom_evaluator.py`閵?

### B7閿涙俺藟姒?Libs 姒涙顓荤€圭偟骞囬敍鍫熷閸掑棔璐熼埉?h閸欘垶鐛欓弨璺侯杻闁插骏绱?

> 鐠囧瓨妲戦敍娆? 閸欘亣藟姒绘劒绗岀粩顖氬煂缁旑垯瀵岄柧鎹愮熅瀵櫣娴夐崗宕囨畱姒涙顓荤€圭偟骞囬敍鍦燣M/Embedding/Splitter/VectorStore/Reranker閿涘鈧倸鍙炬担娆忓讲闁澧跨仦鏇礄娓氬顩ф０婵嗩樆 splitter 缁涙牜鏆愰妴浣规纯婢?vector store 閸氬海顏妴浣规纯婢?evaluator 閸氬海顏粵澶涚礆娣囨繃瀵旈崢鐔稿笓閺堢喍绗夐幓鎰閵?

### B7.1閿涙瓌penAI-Compatible LLM閿涘湦penAI/Azure/DeepSeek閿?
- **閻╊喗鐖?*閿涙俺藟姒?OpenAI-compatible 閻?LLM 鐎圭偟骞囬敍宀€鈥樻穱婵嬧偓姘崇箖 `LLMFactory` 閸欘垰鍨卞鍝勮嫙閸欘垵顫?mock 濞村鐦妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/llm/openai_llm.py`
  - `src/libs/llm/azure_llm.py`
  - `src/libs/llm/deepseek_llm.py`
  - `tests/unit/test_llm_providers_smoke.py`閿涘潰ock HTTP閿涘奔绗夌挧鎵埂鐎圭偟缍夌紒婊愮礆
- **妤犲本鏁归弽鍥у櫙**閿?
  - 闁板秶鐤嗘稉宥呮倱 `provider` 閺冭泛浼愰崢鍌濈熅閻㈣鲸顒滅涵顔衡偓?
  - `chat(messages)` 鐎电绶崗?shape 閺嶏繝鐛欏〒鍛珰閿涘苯绱撶敮闀愪繆閹垰褰茬拠浼欑礄閸栧懎鎯?provider 娑撳酣鏁婄拠顖滆閸ㄥ绱氶妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_llm_providers_smoke.py`閵?

### B7.2閿涙瓌llama LLM閿涘牊婀伴崷鏉挎倵缁旑垽绱?
- **閻╊喗鐖?*閿涙俺藟姒?`ollama_llm.py`閿涘本鏁幐浣规拱閸?HTTP endpoint閿涘牓绮拋?`base_url` + `model`閿涘绱濋獮璺哄讲鐞?mock 濞村鐦妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/llm/ollama_llm.py`
  - `tests/unit/test_ollama_llm.py`閿涘潰ock HTTP閿?
- **妤犲本鏁归弽鍥у櫙**閿?
  - provider=ollama 閺冭泛褰查悽?`LLMFactory` 閸掓稑缂撻妴?
  - 閸︺劏绻涢幒銉ャ亼鐠?鐡掑懏妞傜粵澶婃簚閺咁垯绗呴敍灞惧閸戝搫褰茬拠濠氭晩鐠囶垯绗栨稉宥嗙闂囧弶鏅遍幇鐔煎帳缂冾喓鈧?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_ollama_llm.py`閵?

### B7.3閿涙瓌penAI & Azure Embedding 鐎圭偟骞?
- **閻╊喗鐖?*閿涙俺藟姒?`openai_embedding.py` 閸?`azure_embedding.py`閿涘本鏁幐?OpenAI 鐎规ɑ鏌?API 閸?Azure OpenAI 閺堝秴濮熼惃?Embedding 鐠嬪啰鏁ら敍灞炬暜閹镐焦澹掗柌?`embed(texts)`閿涘苯鑻熼崣顖濐潶 mock 濞村鐦妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/embedding/openai_embedding.py`
  - `src/libs/embedding/azure_embedding.py`
  - `tests/unit/test_embedding_providers_smoke.py`閿涘潰ock HTTP閿涘苯瀵橀崥?OpenAI 閸?Azure 濞村鐦悽銊ょ伐閿?
- **妤犲本鏁归弽鍥у櫙**閿?
  - provider=openai 閺?`EmbeddingFactory` 閸欘垰鍨卞鐚寸礉閺€顖涘瘮 OpenAI 鐎规ɑ鏌?API 閻?text-embedding-3-small/large 缁涘膩閸ㄥ鈧?
  - provider=azure 閺?`EmbeddingFactory` 閸欘垰鍨卞鐚寸礉濮濓絿鈥樻径鍕倞 Azure 閻楄婀侀惃?endpoint閵嗕工pi-version閵嗕工pi-key 闁板秶鐤嗛敍灞炬暜閹?Azure 闁劎璁查惃?text-embedding-ada-002 缁涘膩閸ㄥ鈧?
  - 缁岄缚绶崗銉ｂ偓浣界Т闂€鑳翻閸忋儲婀侀弰搴ｂ€樼悰灞艰礋閿涘牊濮ら柨娆愬灗閹搭亝鏌囩粵鏍殣閻㈤亶鍘ょ純顔煎枀鐎规熬绱氶妴?
  - Azure 鐎圭偟骞囨径宥囨暏 OpenAI Embedding 閻ㄥ嫭鐗宠箛鍐偓鏄忕帆閿涘奔绻氶幐浣筋攽娑撹桨绔撮懛瀛樷偓褋鈧?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_embedding_providers_smoke.py`閵?

### B7.4閿涙瓌llama Embedding 鐎圭偟骞?
- **閻╊喗鐖?*閿涙俺藟姒?`ollama_embedding.py`閿涘本鏁幐渚€鈧俺绻?Ollama HTTP API 鐠嬪啰鏁ら張顒€婀撮柈銊ц閻?Embedding 濡€崇€烽敍鍫濐洤 `nomic-embed-text`閵嗕梗mxbai-embed-large` 缁涘绱氶敍灞界杽閻?`embed(texts)` 閹靛綊鍣洪崥鎴﹀櫤閸栨牕濮涢懗濮愨偓?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/embedding/ollama_embedding.py`
  - `tests/unit/test_ollama_embedding.py`閿涘牆瀵橀崥?mock HTTP 濞村鐦敍?
- **妤犲本鏁归弽鍥у櫙**閿?
  - provider=ollama 閺?`EmbeddingFactory` 閸欘垰鍨卞鎭掆偓?
  - 閺€顖涘瘮闁板秶鐤?Ollama 閺堝秴濮熼崷鏉挎絻閿涘牓绮拋?http://localhost:11434閿涘鎷板Ο鈥崇€烽崥宥囆為妴?
  - 鏉堟挸鍤崥鎴﹀櫤缂佹潙瀹抽悽杈侀崹瀣枀鐎规熬绱欐俊?nomic-embed-text 娑?768 缂佽揪绱氶敍灞惧姬鐡?ingestion/retrieval 閻ㄥ嫭甯撮崣锝咁殩缁撅负鈧?
  - 閺€顖涘瘮閹靛綊鍣?`embed(texts)` 鐠嬪啰鏁ら敍灞藉敶闁劌顦╅悶鍡楀礋閺?閹靛綊鍣虹拠閿嬬湴闁槒绶妴?
  - 缁岄缚绶崗銉ｂ偓浣界Т闂€鑳翻閸忋儲婀侀弰搴ｂ€樼悰灞艰礋閿涘牊濮ら柨娆愬灗閹搭亝鏌囩粵鏍殣閿涘鈧?
  - mock 濞村鐦憰鍡欐磰濮濓絽鐖堕崫宥呯安閵嗕浇绻涢幒銉ャ亼鐠愩儯鈧浇绉撮弮鍓佺搼閸︾儤娅欓妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_ollama_embedding.py`閵?

### B7.5閿涙瓓ecursive Splitter 姒涙顓荤€圭偟骞?
- **閻╊喗鐖?*閿涙俺藟姒?`recursive_splitter.py`閿涘苯鐨濈憗?LangChain 閻ㄥ嫬鍨忛崚鍡涒偓鏄忕帆閿涘奔缍旀稉娲帛鐠併倕鍨忛崚鍡楁珤閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/splitter/recursive_splitter.py`
  - `tests/unit/test_recursive_splitter_lib.py`
- **妤犲本鏁归弽鍥у櫙**閿?
  - provider=recursive 閺?`SplitterFactory` 閸欘垰鍨卞鎭掆偓?
  - `split_text` 閼宠姤顒滅涵顔碱槱閻?Markdown 缂佹挻鐎敍鍫熺垼妫?娴狅絿鐖滈崸妞剧瑝鐞氼偅澧﹂弬顓ㄧ礆閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_recursive_splitter_lib.py`閵?

### B7.6閿涙hromaStore閿涘湸ectorStore 姒涙顓婚崥搴ｎ伂閿?
- **閻╊喗鐖?*閿涙俺藟姒?`chroma_store.py`閿涘本鏁幐浣规付鐏?`upsert(records)` 娑?`query(vector, top_k, filters)`閿涘苯鑻熼弨顖涘瘮閺堫剙婀撮幐浣风畽閸栨牜娲拌ぐ鏇礄娓氬顩?`data/db/chroma/`閿涘鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/vector_store/chroma_store.py`
  - `tests/integration/test_chroma_store_roundtrip.py`
- **妤犲本鏁归弽鍥у櫙**閿?
  - provider=chroma 閺?`VectorStoreFactory` 閸欘垰鍨卞鎭掆偓?
  - **韫囧懘銆忕€瑰本鍨氱€瑰本鏆ｉ惃?upsert閳姯uery roundtrip 濞村鐦?*閿涙矮濞囬悽?mock 閺佺増宓佺€瑰本鍨氶惇鐔风杽閻ㄥ嫬鐡ㄩ崒銊ユ嫲濡偓缁便垺绁︾粙瀣剁礉妤犲矁鐦夋潻鏂挎礀缂佹挻鐏夐惃鍕€樼€规碍鈧冩嫲濮濓絿鈥橀幀褋鈧?
  - 濞村鐦惔鏃囶洬閻╂牭绱伴崺鐑樻拱 upsert閵嗕礁鎮滈柌蹇旂叀鐠囶潿鈧辜op_k 閸欏倹鏆熼妴涔礶tadata filters閿涘牆顩ч弨顖涘瘮閿涘鈧?
  - 娴ｈ法鏁ゆ稉瀛樻閻╊喖缍嶆潻娑滎攽閹镐椒绠欓崠鏍ㄧゴ鐠囨洩绱濆ù瀣槸缂佹挻娼崥搴㈢閻炲棎鈧?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_chroma_store_roundtrip.py`

### B7.7閿涙瓈LM Reranker閿涘牐顕伴崣?rerank prompt閿?
- **閻╊喗鐖?*閿涙俺藟姒?`llm_reranker.py`閿涘矁顕伴崣?`config/prompts/rerank.txt` 閺嬪嫰鈧?prompt閿涘牊绁寸拠鏇氳厬閸欘垱鏁為崗銉︽禌娴狅絾鏋冮張顒婄礆閿涘苯鑻熼崣顖氭躬婢惰精瑙﹂弮鎯扮箲閸ョ偛褰查崶鐐衡偓鈧穱鈥冲娇閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/reranker/llm_reranker.py`
  - `tests/unit/test_llm_reranker.py`閿涘潰ock LLM閿?
- **妤犲本鏁归弽鍥у櫙**閿?
  - backend=llm 閺?`RerankerFactory` 閸欘垰鍨卞鎭掆偓?
  - 鏉堟挸鍤稉銉︾壐缂佹挻鐎崠鏍电礄娓氬顩?ranked ids閿涘绱濇稉宥嗗姬鐡?schema 閺冭埖濮忛崙鍝勫讲鐠囧鏁婄拠顖樷偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_llm_reranker.py`閵?

### B7.8閿涙ross-Encoder Reranker閿涘牊婀伴崷?閹垫顓稿Ο鈥崇€烽敍灞藉窗娴ｅ秴褰茬捄鎴礆
- **閻╊喗鐖?*閿涙俺藟姒?`cross_encoder_reranker.py`閿涘本鏁幐浣割嚠 Top-M candidates 閹垫挸鍨庨幒鎺戠碍閿涙稒绁寸拠鏇氳厬閻?mock scorer 娣囨繆鐦?deterministic閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/reranker/cross_encoder_reranker.py`
  - `tests/unit/test_cross_encoder_reranker.py`閿涘潰ock scorer閿?
- **妤犲本鏁归弽鍥у櫙**閿?
  - backend=cross_encoder 閺?`RerankerFactory` 閸欘垰鍨卞鎭掆偓?
  - 閹绘劒绶电搾鍛/婢惰精瑙﹂崶鐐衡偓鈧穱鈥冲娇閿涘牅绶?Core 鐏?`D6` fallback 娴ｈ法鏁ら敍澶堚偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_cross_encoder_reranker.py`閵?

### B8閿涙瓘ision LLM 閹跺€熻杽閹恒儱褰涙稉搴′紣閸樺倿娉﹂幋?
- **閻╊喗鐖?*閿涙艾鐣炬稊?`BaseVisionLLM` 閹跺€熻杽閹恒儱褰涢敍灞惧⒖鐏?`LLMFactory` 閺€顖涘瘮 Vision LLM 閸掓稑缂撻敍灞艰礋 C7 閻?ImageCaptioner 閹绘劒绶垫惔鏇炵湴閹跺€熻杽閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/llm/base_vision_llm.py`
  - `src/libs/llm/llm_factory.py`閿涘牊澧跨仦?`create_vision_llm` 閺傝纭堕敍?
  - `tests/unit/test_vision_llm_factory.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseVisionLLM.chat_with_image(text: str, image_path: str | bytes, trace: TraceContext | None = None) -> ChatResponse`
  - `LLMFactory.create_vision_llm(settings) -> BaseVisionLLM`
- **妤犲本鏁归弽鍥у櫙**閿?
  - 閹跺€熻杽閹恒儱褰涘〒鍛珰鐎规矮绠熸径姘侀幀浣界翻閸忋儻绱欓弬鍥ㄦ拱+閸ュ墽澧栫捄顖氱窞/base64閿涘鈧?
  - 瀹搞儱宸堕弬瑙勭《 `create_vision_llm` 閼宠姤鐗撮幑顕€鍘ょ純顔跨熅閻㈠崬鍩屾稉宥呮倱 provider閿涘牊绁寸拠鏇氳厬閻?Fake Vision LLM 妤犲矁鐦夐敍澶堚偓?
  - 閹恒儱褰涚拋鎹愵吀閺€顖涘瘮閸ュ墽澧栨０鍕槱閻炲棴绱欓崢瀣級閵嗕焦鐗稿蹇氭祮閹诡澁绱氶惃鍕⒖鐏炴洜鍋ｉ妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_vision_llm_factory.py`閵?

### B9閿涙zure Vision LLM 鐎圭偟骞?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`AzureVisionLLM`閿涘本鏁幐渚€鈧俺绻?Azure OpenAI 鐠嬪啰鏁?GPT-4o/GPT-4-Vision-Preview 鏉╂稖顢戦崶鎯у剼閻炲棜袙閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/llm/azure_vision_llm.py`
  - `tests/unit/test_azure_vision_llm.py`閿涘潰ock HTTP閿涘奔绗夌挧鎵埂鐎?API閿?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `AzureVisionLLM(BaseVisionLLM)`閿涙艾鐤勯悳?`chat_with_image` 閺傝纭?
  - 閺€顖涘瘮 Azure 閻楄婀侀柊宥囩枂閿涙瓪azure_endpoint`, `api_version`, `deployment_name`, `api_key`
- **妤犲本鏁归弽鍥у櫙**閿?
  - provider=azure 娑撴棃鍘ょ純?vision_llm 閺冭绱漙LLMFactory.create_vision_llm()` 閸欘垰鍨卞?Azure Vision LLM 鐎圭偘绶ラ妴?
  - 閺€顖涘瘮閸ュ墽澧栫捄顖氱窞閸?base64 娑撱倗顫掓潏鎾冲弳閺傜懓绱￠妴?
  - 閸ュ墽澧栨潻鍥с亣閺冩儼鍤滈崝銊ュ竾缂傗晞鍤?`max_image_size` 闁板秶鐤嗛惃鍕槀鐎甸潻绱欐妯款吇2048px閿涘鈧?
  - API 鐠嬪啰鏁ゆ径杈Е閺冭埖濮忛崙鐑樼閺呬即鏁婄拠顖ょ礉閸栧懎鎯?Azure 閻楄婀侀柨娆掝嚖閻降鈧?
  - mock 濞村鐦憰鍡欐磰閿涙碍顒滅敮姝岀殶閻劊鈧礁娴橀悧鍥у竾缂傗斂鈧浇绉撮弮韬测偓浣筋吇鐠囦礁銇戠拹銉х搼閸︾儤娅欓妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_azure_vision_llm.py`閵?

### B9.1閿涙ashScope Vision LLM閿涘湨wen3.5-Plus閿涘鐤勯悳?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`DashScopeVisionLLM`閿涘本鏁幐渚€鈧俺绻冮梼鍧楀櫡娴滄垹娅ㄩ悙纭风礄DashScope閿涘鐨熼悽?`qwen3.5-plus` 鏉╂稖顢戦崶鎯у剼閻炲棜袙閿涘矁藟姒绘劏鈧粌娴楅崘?+ 閸ヨ棄顦婚崣灞灸侀崹瀣р偓婵囨煙濡楀牅鑵戦惃鍕禇閸愬懘绮拋銈呯杽閻滆埇鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/llm/dashscope_vision_llm.py`
  - `src/libs/llm/llm_factory.py`閿涘澊ision provider 濞夈劌鍞?`dashscope`閿?
  - `config/settings.yaml`閿涘牊鏌婃晶?閺囧瓨鏌?`vision_llm.provider: dashscope` 缁€杞扮伐闁板秶鐤嗛敍?
  - `tests/unit/test_dashscope_vision_llm.py`閿涘潰ock HTTP閿涘奔绗夌挧鎵埂鐎?API閿?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `DashScopeVisionLLM(BaseVisionLLM)`閿涙艾鐤勯悳?`chat_with_image` 閺傝纭?
  - 閺€顖涘瘮 DashScope 闁板秶鐤嗛敍姝歜ase_url`, `api_key`, `model`, `timeout`, `max_image_size`
- **妤犲本鏁归弽鍥у櫙**閿?
  - provider=dashscope 娑撴棃鍘ょ純?vision_llm 閺冭绱漙LLMFactory.create_vision_llm()` 閸欘垰鍨卞?DashScope Vision LLM 鐎圭偘绶ラ妴?
  - 閺€顖涘瘮閸ュ墽澧栫捄顖氱窞閸?base64 娑撱倗顫掓潏鎾冲弳閺傜懓绱￠妴?
  - 閸ュ墽澧栨潻鍥с亣閺冩儼鍤滈崝銊ュ竾缂傗晞鍤?`max_image_size` 闁板秶鐤嗛惃鍕槀鐎甸潻绱欐妯款吇2048px閿涘鈧?
  - API 鐠嬪啰鏁ゆ径杈Е閺冭埖濮忛崙鐑樼閺呬即鏁婄拠顖ょ礄閸栧懎鎯?provider 娑撳酣鏁婄拠顖滆閸?閻樿埖鈧胶鐖滈敍澶堚偓?
  - mock 濞村鐦憰鍡欐磰閿涙碍顒滅敮姝岀殶閻劊鈧礁娴橀悧鍥у竾缂傗斂鈧浇绉撮弮韬测偓浣筋吇鐠囦礁銇戠拹銉х搼閸︾儤娅欓妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_dashscope_vision_llm.py`閵?

---

## 闂冭埖顔?C閿涙ngestion Pipeline MVP閿涘牏娲伴弽鍥风窗閼宠姤濡?PDF 閺嶈渹绶ラ幗鍕絿閸掔増婀伴崷鏉跨摠閸岊煉绱?

> 濞夘煉绱伴張顒勬▉濞堝吀寮楅弽鍏煎瘻 5.4.1 閻ㄥ嫮顬囩痪鎸庢殶閹诡喗绁﹂拃钘夋勾閿涘苯鑻熸导妯哄帥鐎圭偟骞囬垾婊冾杻闁插繗鐑︽潻鍥风礄SHA256閿涘鈧縿鈧?

### C1閿涙艾鐣炬稊澶嬬壋韫囧啯鏆熼幑顔捐閸?婵傛垹瀹抽敍鍦杘cument/Chunk/ChunkRecord閿?
- **閻╊喗鐖?*閿涙艾鐣炬稊澶婂弿闁炬崘鐭鹃敍鍧昻gestion 閳?retrieval 閳?mcp tools閿涘鍙￠悽銊ф畱閺佺増宓佺紒鎾寸€?婵傛垹瀹抽敍宀勪缉閸忓秵鏆庨拃钘夋躬閸氬嫬鐡欏Ο鈥虫健閸愬懎顕遍懛瀵告畱閼帮箑鎮庢稉搴ㄥ櫢婢跺秲鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/types.py`
  - `src/core/__init__.py`閿涘牆褰查柅澶涚窗缂佺喍绔?re-export 娴犮儳鐣濋崠鏍ь嚤閸忋儴鐭惧鍕剁礆
  - `tests/unit/test_core_types.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿涘牆缂撶拋顕嗙礆閿?
  - `Document(id, text, metadata)`
  - `Chunk(id, text, metadata, start_offset, end_offset, source_ref?)`
  - `ChunkRecord(id, text, metadata, dense_vector?, sparse_vector?)`閿涘牏鏁ゆ禍搴＄摠閸?濡偓缁便垼娴囨担鎿勭幢鐎涙顔岄幐澶婃倵缂?C8~C12 濠曟棁绻橀敍?
- **妤犲本鏁归弽鍥у櫙**閿?
  - 缁鐎烽崣顖氱碍閸掓瀵查敍鍧塱ct/json閿涘绗栫€涙顔岀粙鍐茬暰閿涘牆宕熼崗鍐╃ゴ鐠囨洘鏌囩懛鈧敍澶堚偓?
  - `metadata` 缁撅箑鐣鹃張鈧亸鎴濆瘶閸?`source_path`閿涘苯鍙炬担娆忕摟濞堥潧鍘戠拋绋款杻闁插繑澧跨仦鏇氱稻娑撳秴绶遍惍鏉戞綎閸忕厧顔愰妴?
  - **`metadata.images` 鐎涙顔岀憴鍕瘱**閿涘牏鏁ゆ禍搴☆樋濡剝鈧焦鏁幐渚婄礆閿?
    - 缂佹挻鐎敍姝歀ist[{"id": str, "path": str, "page": int, "text_offset": int, "text_length": int, "position": dict}]`
    - `id`閿涙艾鍙忕仦鈧崬顖欑閸ュ墽澧栭弽鍥槕缁楋讣绱欏楦款唴閺嶇厧绱￠敍姝歿doc_hash}_{page}_{seq}`閿?
    - `path`閿涙艾娴橀悧鍥ㄦ瀮娴犺泛鐡ㄩ崒銊ㄧ熅瀵板嫸绱欑痪锕€鐣鹃敍姝歞ata/images/{collection}/{image_id}.png`閿?
    - `page`閿涙艾娴橀悧鍥ф躬閸樼喐鏋冨锝勮厬閻ㄥ嫰銆夐惍渚婄礄閸欘垶鈧绱濋柅鍌滄暏娴滃侗DF缁涘鍨庢い鍨瀮濡楋綇绱?
    - `text_offset`閿涙艾宕版担宥囶儊閸?`Document.text` 娑擃厾娈戠挧宄邦潗鐎涙顑佹担宥囩枂閿涘牅绮?瀵偓婵顓搁弫甯礆
    - `text_length`閿涙艾宕版担宥囶儊閻ㄥ嫬鐡х粭锕傛毐鎼达讣绱欓柅姘埗娑?`len("[IMAGE: {image_id}]")`閿?
    - `position`閿涙艾娴橀悧鍥ф躬閸樼喐鏋冨锝勮厬閻ㄥ嫮澧块悶鍡曠秴缂冾喕淇婇幁顖ょ礄閸欘垶鈧绱濇俊渚綝F閸ф劖鐖ｉ妴浣稿剼缁辩姳缍呯純顔衡偓浣告槀鐎靛摜鐡戦敍?
    - 鐠囧瓨妲戦敍姘垛偓姘崇箖 `text_offset` 閸?`text_length` 閸欘垳绨跨涵顔肩暰娴ｅ秴娴橀悧鍥ф躬閺傚洦婀版稉顓犳畱娴ｅ秶鐤嗛敍灞炬暜閹镐礁鎮撴稉鈧崶鍓у婢舵碍顐奸崙铏瑰箛閻ㄥ嫬婧€閺?
  - **閺傚洦婀版稉顓炴禈閻楀洤宕版担宥囶儊鐟欏嫯瀵?*閿涙艾婀?`Document.text` 娑擃叏绱濋崶鍓у娴ｅ秶鐤嗘担璺ㄦ暏 `[IMAGE: {image_id}]` 閺嶇厧绱￠弽鍥唶閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_core_types.py`閵?

### C2閿涙碍鏋冩禒璺虹暚閺佸瓨鈧勵梾閺屻儻绱橲HA256閿?
- **閻╊喗鐖?*閿涙艾婀狶ibs娑擃厼鐤勯悳?`file_integrity.py`閿涙俺顓哥粻妤佹瀮娴?hash閿涘苯鑻熼幓鎰返閳ユ粍妲搁崥锕佺儲鏉╁洠鈧繄娈戦崚銈呯暰閹恒儱褰涢敍鍫滃▏閻?SQLite 娴ｆ粈璐熸妯款吇鐎涙ê鍋嶉敍灞炬暜閹镐礁鎮楃紒顓熸禌閹诡澀璐?Redis/PostgreSQL閿涘鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/loader/file_integrity.py`
  - `tests/unit/test_file_integrity.py`
  - 閺佺増宓佹惔鎾存瀮娴犺绱癭data/db/ingestion_history.db`閿涘牐鍤滈崝銊ュ灡瀵ょ尨绱?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `FileIntegrityChecker` 缁紮绱欓幎鍊熻杽閹恒儱褰涢敍?
  - `SQLiteIntegrityChecker(FileIntegrityChecker)` 缁紮绱欐妯款吇鐎圭偟骞囬敍?
    - `compute_sha256(path: str) -> str`
    - `should_skip(file_hash: str) -> bool`
    - `mark_success(file_hash: str, file_path: str, ...)`
    - `mark_failed(file_hash: str, error_msg: str)`
- **妤犲本鏁归弽鍥у櫙**閿?
  - 閸氬奔绔撮弬鍥︽婢舵碍顐肩拋锛勭暬hash缂佹挻鐏夋稉鈧懛?
  - 閺嶅洩顔?success 閸氬函绱漙should_skip` 鏉╂柨娲?`True`
  - 閺佺増宓佹惔鎾存瀮娴犺埖顒滅涵顔煎灡瀵ゅ搫婀?`data/db/ingestion_history.db`
  - 閺€顖涘瘮楠炶泛褰傞崘娆忓弳閿涘湯QLite WAL濡€崇础閿?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_file_integrity.py`閵?

### C3閿涙瓈oader 閹跺€熻杽閸╄櫣琚稉?PDF Loader 婢瑰啿鐡?
- **閻╊喗鐖?*閿涙艾婀狶ibs娑擃厼鐣炬稊?`BaseLoader`閿涘苯鑻熺€圭偟骞?`PdfLoader` 閻ㄥ嫭娓剁亸蹇氼攽娑撴亽鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/loader/base_loader.py`
  - `src/libs/loader/pdf_loader.py`
  - `tests/unit/test_loader_pdf_contract.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseLoader.load(path) -> Document`
  - `PdfLoader.load(path)`
- **妤犲本鏁归弽鍥у櫙**閿?
  - **閸╄櫣顢呯憰浣圭湴**閿涙艾顕?sample PDF閿涘潚ixtures閿涘鍏樻禍褍鍤?Document閿涘etadata 閼峰啿鐨崥?`source_path`閵?
  - **閸ュ墽澧栨径鍕倞鐟曚焦鐪?*閿涘牓浼掑?C1 鐎规矮绠熼惃鍕殩缁撅讣绱氶敍?
    - 閼?PDF 閸栧懎鎯堥崶鍓у閿涘苯绨查幓鎰絿閸ュ墽澧栭獮鏈电箽鐎涙ê鍩?`data/images/{doc_hash}/` 閻╊喖缍?
    - 閸?`Document.text` 娑擃叏绱濋崶鍓у娴ｅ秶鐤嗛幓鎺戝弳閸楃姳缍呯粭锔肩窗`[IMAGE: {image_id}]`
    - 閸?`metadata.images` 娑擃叀顔囪ぐ鏇炴禈閻楀洣淇婇幁顖ょ礄閺嶇厧绱＄憴?C1 鐟欏嫯瀵栭敍?
    - 閼?PDF 閺冪姴娴橀悧鍥风礉`metadata.images` 閸欘垯璐熺粚鍝勫灙鐞涖劍鍨ㄩ惇浣烘殣鐠囥儱鐡у▓?
  - **闂勫秶楠囩悰灞艰礋**閿涙艾娴橀悧鍥ㄥ絹閸欐牕銇戠拹銉ょ瑝鎼存棃妯嗘繅鐐存瀮閺堫剝袙閺嬫劧绱濋崣顖氭躬閺冦儱绻旀稉顓☆唶瑜版洝顒熼崨濞库偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_loader_pdf_contract.py`閵?
- **濞村鐦楦款唴**閿?
  - 閸戝棗顦稉銈勯嚋濞村鐦弬鍥︽閿涙瓪simple.pdf`閿涘牏鍑介弬鍥ㄦ拱閿涘鎷?`with_images.pdf`閿涘牆瀵橀崥顐㈡禈閻楀浄绱?
  - 妤犲矁鐦夌痪顖涙瀮閺堢悕DF閼宠姤顒滅敮姝屝掗弸?
  - 妤犲矁鐦夌敮锕€娴橀悧鍢滵F閼宠姤褰侀崣鏍ф禈閻楀洤鑻熷锝団€橀幓鎺戝弳閸楃姳缍呯粭?

### C4閿涙瓔plitter 闂嗗棙鍨氶敍鍫ｇ殶閻?Libs閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳?Chunking 濡€虫健娴ｆ粈璐?`libs.splitter` 閸?Ingestion Pipeline 娑斿妫块惃?*闁倿鍘ら崳銊ョ湴**閿涘苯鐣幋?Document閳墫hunks 閻ㄥ嫪绗熼崝鈥愁嚠鐠灺ゆ祮閹诡潿鈧?
- **閺嶇绺鹃懕宀冪煑閿涘湒ocumentChunker 閻╁憡鐦?libs.splitter 閻ㄥ嫬顤冮崐纭风礆**閿?
  - **閼卞矁鐭楁潏鍦櫕鐠囧瓨妲?*閿?
    - `libs.splitter`閿涙氨鍑介弬鍥ㄦ拱閸掑洤鍨庡銉ュ徔閿涘潉str 閳?List[str]`閿涘绱濇稉宥嗙Ч閸欏﹣绗熼崝鈥愁嚠鐠?
    - `DocumentChunker`閿涙矮绗熼崝锟犫偓鍌炲帳閸ｎ煉绱檂Document鐎电钖?閳?List[Chunk鐎电钖刔`閿涘绱濆ǎ璇插娑撴艾濮熼柅鏄忕帆
  - **6 娑擃亜顤冮崐鐓庡閼?*閿?
    1. **Chunk ID 閻㈢喐鍨?*閿涙矮璐熷В蹇庨嚋閺傚洦婀伴悧鍥唽閻㈢喐鍨氶崬顖欑娑撴梻鈥樼€规碍鈧呮畱 ID閿涘牊鐗稿蹇ョ窗`{doc_id}_{index:04d}_{hash_8chars}`閿?
    2. **閸忓啯鏆熼幑顔炬埛閹?*閿涙艾鐨?Document.metadata 婢跺秴鍩楅崚鐗堢槨娑?Chunk.metadata閿涘澃ource_path, doc_type, title 缁涘绱?
    3. **濞ｈ濮?chunk_index**閿涙俺顔囪ぐ?chunk 閸︺劍鏋冨锝勮厬閻ㄥ嫬绨崣鍑ょ礄娴?0 瀵偓婵绱氶敍宀€鏁ゆ禍搴㈠笓鎼村繐鎷扮€规矮缍?
    4. **瀵よ櫣鐝?source_ref**閿涙俺顔囪ぐ?Chunk.source_ref 閹稿洤鎮滈悥?Document.id閿涘本鏁幐浣瑰嚱濠?
    5. **閸ュ墽澧栧鏇犳暏閹稿娓堕崚鍡楀絺**閿涙碍澹傞幓蹇旂槨娑?chunk 閺傚洦婀版稉顓犳畱 `[IMAGE: {id}]` 閸楃姳缍呯粭锔肩礉娴?`Document.metadata["images"]` 娑擃厽褰侀崣鏍嚉 chunk 鐎圭偤妾鏇犳暏閻?ImageRef閿涘苯鍟撻崗?`chunk.metadata["images"]`閿涘牅绮庨崥顐ヮ嚉 chunk 瀵洜鏁ら惃鍕摍闂嗗棴绱氶崪?`chunk.metadata["image_refs"]`閿涘潟mage_id 閸掓銆冮敍澶堚偓鍌涙￥閸楃姳缍呯粭锔炬畱 chunk 娑撳秴鎯?`images` 鐎涙顔岄妴鍌楁閿?娑撳秴褰茬粻鈧崡鏇熸殻娴ｆ挾鎴烽幍鎸庡灗娑撱垹绱旈弬鍥ㄣ€傜痪?`images`閿涘苯鎯侀崚娆庣瑓濞?C7 ImageCaptioner 鐏忓棙妫ゅ▔鏇炵暰娴ｅ秴娴橀悧鍥熅瀵板嫨鈧?
    6. **缁鐎锋潪顒佸床**閿涙艾鐨?libs.splitter 閻?`List[str]` 鏉烆剚宕叉稉铏诡儊閸?core.types 婵傛垹瀹抽惃?`List[Chunk]` 鐎电钖?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/chunking/document_chunker.py`
  - `src/ingestion/chunking/__init__.py`
  - `tests/unit/test_document_chunker.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `DocumentChunker` 缁?
  - `__init__(settings: Settings)`閿涙岸鈧俺绻?SplitterFactory 閼惧嘲褰囬柊宥囩枂閻?splitter 鐎圭偘绶?
  - `split_document(document: Document) -> List[Chunk]`閿涙艾鐣弫瀵告畱鏉烆剚宕插ù浣衡柤
  - `_generate_chunk_id(doc_id: str, index: int, text: str) -> str`閿涙氨鏁撻幋鎰旂€?Chunk ID
  - `_inherit_metadata(document: Document, chunk_index: int, chunk_text: str) -> dict`閿涙艾鍘撻弫鐗堝祦缂佈勫 + 閸ュ墽澧栧鏇犳暏閹稿娓堕崚鍡楀絺闁槒绶敍鍫ユ付鐟?chunk_text 閺夈儲澹傞幓?`[IMAGE: id]` 閸楃姳缍呯粭锔肩礆
- **妤犲本鏁归弽鍥у櫙**閿?
  - **闁板秶鐤嗘す鍗炲З**閿涙岸鈧俺绻冩穱顔芥暭 settings.yaml 娑擃厾娈?splitter 闁板秶鐤嗛敍鍫濐洤 chunk_size閿涘绱濇禍褍鍤惃?chunk 閺佷即鍣洪崪宀勬毐鎼达箑褰傞悽鐔烘祲鎼存柨褰夐崠?
  - **ID 閸烆垯绔撮幀?*閿涙碍鐦℃稉?Chunk 閻?ID 閸︺劍鏆ｆ稉顏呮瀮濡楋絼鑵戦崬顖欑
  - **ID 绾喖鐣鹃幀?*閿涙艾鎮撴稉鈧?Document 鐎电钖勯柌宥咁槻閸掑洤鍨庢禍褏鏁撻惄绋挎倱閻?Chunk ID 鎼村繐鍨?
  - **閸忓啯鏆熼幑顔肩暚閺佸瓨鈧?*閿涙hunk.metadata 閸栧懎鎯堥幍鈧張?Document.metadata 鐎涙顔?+ chunk_index 鐎涙顔?
  - **閸ュ墽澧栭崚鍡楀絺濮濓絿鈥橀幀?*閿涙艾鎯?`[IMAGE: id]` 閸楃姳缍呯粭锔炬畱 chunk 閸?`metadata["images"]` 娴犲懎瀵橀崥顐ヮ嚉 chunk 瀵洜鏁ら惃鍕禈閻楀洤鐡欓梿鍡幢娑撳秴鎯堥崡鐘辩秴缁楋妇娈?chunk 閺?`images` 鐎涙顔岄敍娌梞etadata["image_refs"]` 閸掓銆冩稉搴″窗娴ｅ秶顑佹稉鈧懛?
  - **濠ь垱绨柧鐐复**閿涙碍澧嶉張?Chunk.source_ref 濮濓絿鈥橀幐鍥ф倻閻?Document.id
  - **缁鐎锋總鎴犲**閿涙俺绶崙铏规畱 Chunk 鐎电钖勭粭锕€鎮?`core/types.py` 娑擃厾娈?Chunk 鐎规矮绠熼敍鍫濆讲鎼村繐鍨崠鏍モ偓浣哥摟濞堥潧鐣弫杈剧礆
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_document_chunker.py`閿涘牅濞囬悽?FakeSplitter 闂呮梻顬囧ù瀣槸閿涘本妫ら棁鈧惇鐔风杽 LLM/婢舵牠鍎存笟婵婄閿涘鈧?

### C5閿涙瓖ransform 閹跺€熻杽閸╄櫣琚?+ ChunkRefiner閿涘牐顫夐崚娆忓箵閸?+ LLM 婢х偛宸遍敍?
- **閻╊喗鐖?*閿涙艾鐣炬稊?`BaseTransform`閿涙稑鐤勯悳?`ChunkRefiner`閿涙艾鍘涢崑姘愁潐閸掓瑥骞撻崳顏庣礉閸愬秹鈧俺绻僉LM鏉╂稖顢戦弲楦垮厴婢х偛宸遍敍灞借嫙閹绘劒绶垫径杈Е闂勫秶楠囬張鍝勫煑閿涘湢LM瀵倸鐖堕弮璺烘礀闁偓閸掓媽顫夐崚娆戠波閺嬫粣绱濇稉宥夋▎婵?ingestion閿涘鈧?
- **閸撳秶鐤嗛弶鈥叉**閿涘牆绻€妞よ鍣径鍥风礆閿?
  - **韫囧懘銆忛柊宥囩枂LLM**閿涙艾婀?`config/settings.yaml` 娑擃參鍘ょ純顔煎讲閻劎娈慙LM閿涘潷rovider/model/api_key閿?
  - **閻滎垰顣ㄩ崣姗€鍣?*閿涙俺顔曠純顔碱嚠鎼存梻娈慉PI key閻滎垰顣ㄩ崣姗€鍣洪敍鍧凮PENAI_API_KEY`/`OLLAMA_BASE_URL`缁涘绱?
  - **妤犲矁鐦夐惄顔炬畱**閿涙岸鈧俺绻冮惇鐔风杽LLM濞村鐦宀冪槈闁板秶鐤嗗锝団€橀幀褍鎷皉efinement閺佸牊鐏?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/transform/base_transform.py`閿涘牊鏌婃晶鐑囩礆
  - `src/ingestion/transform/chunk_refiner.py`閿涘牊鏌婃晶鐑囩礆
  - `src/core/trace/trace_context.py`閿涘牊鏌婃晶鐑囩窗閺堚偓鐏忓繐鐤勯悳甯礉Phase F 鐎瑰苯鏉介敍?
  - `config/prompts/chunk_refinement.txt`閿涘牆鍑＄€涙ê婀敍宀勬付妤犲矁鐦夐崘鍛啇楠炴儼藟閸?{text} 閸楃姳缍呯粭锔肩礆
  - `tests/fixtures/noisy_chunks.json`閿涘牊鏌婃晶鐑囩窗8娑擃亜鍚€閸ㄥ娅旀竟鏉挎簚閺咁垽绱?
  - `tests/unit/test_chunk_refiner.py`閿涘牊鏌婃晶鐑囩窗27娑擃亜宕熼崗鍐╃ゴ鐠囨洩绱?
  - `tests/integration/test_chunk_refiner_llm.py`閿涘牊鏌婃晶鐑囩窗閻喎鐤凩LM闂嗗棙鍨氬ù瀣槸閿?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseTransform.transform(chunks, trace) -> List[Chunk]`
  - `ChunkRefiner.__init__(settings, llm?, prompt_path?)`
  - `ChunkRefiner.transform(chunks, trace) -> List[Chunk]`
  - `ChunkRefiner._rule_based_refine(text) -> str`閿涘牆骞撶粚铏规/妞ょ數婀佹い浣冨壖/閺嶇厧绱￠弽鍥唶/HTML濞夈劑鍣撮敍?
  - `ChunkRefiner._llm_refine(text, trace) -> str | None`閿涘牆褰查柅?LLM 闁插秴鍟撻敍灞姐亼鐠愩儴绻戦崶?None閿?
  - `ChunkRefiner._load_prompt(prompt_path?)`閿涘牅绮犻弬鍥︽閸旂姾娴噋rompt濡剝婢橀敍灞炬暜閹镐線绮拋顦宎llback閿?
- **鐎圭偟骞囧ù浣衡柤瀵ら缚顔?*閿?
  1. 閸忓牆鍨卞?`tests/fixtures/noisy_chunks.json`閿涘苯瀵橀崥?娑擃亜鍚€閸ㄥ娅旀竟鏉挎簚閺咁垽绱?
     - typical_noise_scenario: 缂佺厧鎮庨崳顏勶紣閿涘牓銆夐惇?妞や絻鍓?缁岃櫣娅ч敍?
     - ocr_errors: OCR闁挎瑨顕ら弬鍥ㄦ拱
     - page_header_footer: 妞ょ數婀佹い浣冨壖濡€崇础
     - excessive_whitespace: 婢舵矮缍戠粚铏规
     - format_markers: HTML/Markdown閺嶅洩顔?
     - clean_text: 楠炴彃鍣ｉ弬鍥ㄦ拱閿涘牓鐛欑拠浣风瑝鏉╁洤瀹冲〒鍛倞閿?
     - code_blocks: 娴狅絿鐖滈崸妤嬬礄妤犲矁鐦夋穱婵堟殌閸愬懘鍎撮弽鐓庣础閿?
     - mixed_noise: 閻喎鐤勫ǎ宄版値閸︾儤娅?
  2. 閸掓稑缂?`TraceContext` 閸楃姳缍呯€圭偟骞囬敍鍧瞮id閻㈢喐鍨歵race_id閿涘ecord_stage鐎涙ê鍋嶉梼鑸殿唽閺佺増宓侀敍?
  3. 鐎圭偟骞?`BaseTransform` 閹跺€熻杽閹恒儱褰?
  4. 鐎圭偟骞?`ChunkRefiner._rule_based_refine` 鐟欏嫬鍨崢璇叉珨闁槒绶敍鍫燁劀閸掓瑥灏柊?閸掑棙顔屾径鍕倞閿?
  5. 缂傛牕鍟撶憴鍕灟濡€崇础閸楁洖鍘撳ù瀣槸閿涘牅濞囬悽?fixtures 閺傤叀鈻堝〒鍛閺佸牊鐏夐敍?
  6. 鐎圭偟骞?`_llm_refine` 閸欘垶鈧顤冨鐚寸礄鐠囪褰?prompt閵嗕浇鐨熼悽?LLM閵嗕線鏁婄拠顖氼槱閻炲棴绱?
  7. 缂傛牕鍟?LLM 濡€崇础閸楁洖鍘撳ù瀣槸閿涘潰ock LLM 閺傤叀鈻堢拫鍐暏娑撳氦绶崙鐚寸礆
  8. 缂傛牕鍟撻梽宥囬獓閸︾儤娅欏ù瀣槸閿涘湢LM 婢惰精瑙﹂弮璺烘礀闁偓閸掓媽顫夐崚娆戠波閺嬫粣绱濋弽鍥唶 metadata閿?
  9. **缂傛牕鍟撻惇鐔风杽LLM闂嗗棙鍨氬ù瀣槸楠炶埖澧界悰宀勭崣鐠?*閿涘牆绻€妞ょ粯澧界悰宀嬬礉妤犲矁鐦塋LM闁板秶鐤嗛敍?
- **妤犲本鏁归弽鍥у櫙**閿?
  - **閸楁洖鍘撳ù瀣槸閿涘牆鎻╅柅鐔峰冀妫ｅ牆鎯婇悳顖ょ礆**閿?
    - 鐟欏嫬鍨Ο鈥崇础閿涙艾顕?fixtures 閸ｎ亜锛愰弽铚傜伐閼宠姤顒滅涵顔煎箵閸ｎ亷绱欐潻鐐电敾缁岃櫣娅?妞ょ數婀佹い浣冨壖/閺嶇厧绱￠弽鍥唶/閸掑棝娈х痪鍖＄礆
    - 娣囨繄鏆€閼宠棄濮忛敍姘敩閻礁娼￠崘鍛村劥閺嶇厧绱℃稉宥堫潶閻潙娼栭敍瀛rkdown缂佹挻鐎€瑰本鏆ｆ穱婵堟殌
    - LLM 濡€崇础閿涙ock LLM 閺冩儼鍏樺锝団€樼拫鍐暏楠炴儼绻戦崶鐐哄櫢閸愭瑧绮ㄩ弸婊愮礉metadata 閺嶅洩顔?`refined_by: "llm"`
    - 闂勫秶楠囩悰灞艰礋閿涙瓈LM 婢惰精瑙﹂弮璺烘礀闁偓閸掓媽顫夐崚娆戠波閺嬫粣绱漨etadata 閺嶅洩顔?`refined_by: "rule"` 閸?fallback 閸樼喎娲?
    - 闁板秶鐤嗗鈧崗绛圭窗闁俺绻?`settings.yaml` 閻?`ingestion.chunk_refiner.use_llm` 閹貉冨煑鐞涘奔璐?
    - 瀵倸鐖舵径鍕倞閿涙艾宕熸稉鐚歨unk婢跺嫮鎮婂鍌氱埗娑撳秴濂栭崫宥呭従娴犳溈hunk閿涘奔绻氶悾娆忓斧閺?
  - **闂嗗棙鍨氬ù瀣槸閿涘牓鐛欓弨璺虹箑妞ゅ銆嶉敍?*閿?
    - 閴?**韫囧懘銆忔宀冪槈閻喎鐤凩LM鐠嬪啰鏁ら幋鎰**閿涙矮濞囬悽銊ュ缂冾喗娼禒鏈佃厬闁板秶鐤嗛惃鍑㎜M鏉╂稖顢戦惇鐔风杽refinement
    - 閴?**韫囧懘銆忔宀冪槈鏉堟挸鍤拹銊╁櫤**閿涙瓈LM refined閺傚洦婀扮涵顔肩杽閺囨潙鍏遍崙鈧敍鍫濇珨婢规澘鍣虹亸鎴欌偓浣稿敶鐎归€涚箽閻ｆ瑱绱?
    - 閴?**韫囧懘銆忔宀冪槈闂勫秶楠囬張鍝勫煑**閿涙碍妫ら弫鍫熌侀崹瀣倳缁夌増妞傛导姗€娉ら梽宥囬獓閸掔殙ule-based閿涘奔绗夊畷鈺傜皾
    - 鐠囧瓨妲戦敍姘崇箹閺勵垶鐛欑拠?閸撳秶鐤嗛弶鈥叉娑擃厼鍣径鍥╂畱LLM闁板秶鐤嗛弰顖氭儊濮濓絿鈥?閻ㄥ嫬绻€鐟曚焦顒炴?
- **濞村鐦弬瑙勭《**閿?
  - **闂冭埖顔?-閸楁洖鍘撳ù瀣槸閿涘牆绱戦崣鎴滆厬韫囶偊鈧喕鍑禒锝忕礆**閿?
    ```bash
    pytest tests/unit/test_chunk_refiner.py -v
    # 閴?27娑擃亝绁寸拠鏇炲弿闁劑鈧俺绻冮敍灞煎▏閻⑩垥ock闂呮梻顬囬敍灞炬￥闂団偓閻喎鐤凙PI
    ```
  - **闂冭埖顔?-闂嗗棙鍨氬ù瀣槸閿涘牓鐛欓弨璺虹箑妞ょ粯澧界悰宀嬬礆**閿?
    ```bash
    # 1. 鏉╂劘顢戦惇鐔风杽LLM闂嗗棙鍨氬ù瀣槸閿涘牆绻€妞や紮绱?
    pytest tests/integration/test_chunk_refiner_llm.py -v -s
    # 閴?妤犲矁鐦塋LM闁板秶鐤嗗锝団€橀敍瀹篹finement閺佸牊鐏夌粭锕€鎮庢０鍕埂
    # 閳跨媴绗?娴兼矮楠囬悽鐔烘埂鐎规咖PI鐠嬪啰鏁ゆ稉搴ゅ瀭閻?
    
    # 2. Review閹垫挸宓冩潏鎾冲毉閿涘瞼鈥樼拋銈囩翱閻愯壈宸濋柌?
    # - 閸ｎ亜锛愰弰顖氭儊鐞氼偅婀侀弫鍫濆箵闂勩倧绱?
    # - 閺堝鏅ラ崘鍛啇閺勵垰鎯佺€瑰本鏆ｆ穱婵堟殌閿?
    # - 闂勫秶楠囬張鍝勫煑閺勵垰鎯佸锝呯埗瀹搞儰缍旈敍?
    ```
  - **濞村鐦崚鍡楃湴闁槒绶?*閿?
    - 閸楁洖鍘撳ù瀣槸閿涙岸鐛欑拠浣峰敩閻線鈧槒绶锝団€?
    - 闂嗗棙鍨氬ù瀣槸閿涙岸鐛欑拠浣洪兇缂佺喎褰查悽銊︹偓?
    - 娑撱倛鈧懍绨扮悰銉礉缂傝桨绔存稉宥呭讲

### C6閿涙瓉etadataEnricher閿涘牐顫夐崚娆忣杻瀵?+ 閸欘垶鈧?LLM 婢х偛宸?+ 闂勫秶楠囬敍?
- **閻╊喗鐖?*閿涙艾鐤勯悳鏉垮帗閺佺増宓佹晶鐐插繁濡€虫健閿涙碍褰佹笟娑滎潐閸掓瑥顤冨铏规畱姒涙顓荤€圭偟骞囬敍灞借嫙闁插秶鍋ｉ弨顖涘瘮 LLM 婢х偛宸遍敍鍫ュ帳缂冾喖鍑＄亸杈╁崕閿涘LM 瀵偓閸忚櫕澧﹀鈧敍澶堚偓鍌氬焺閻?LLM 鐎?chunk 鏉╂稖顢戞妯垮窛闁插繒娈?title 閻㈢喐鍨氶妴涔籾mmary 閹芥顩﹂崪?tags 閹绘劕褰囬妴鍌氭倱閺冩湹绻氶悾娆忋亼鐠愩儵妾风痪褎婧€閸掕绱濈涵顔荤箽娑撳秹妯嗘繅?ingestion閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/transform/metadata_enricher.py`
  - `tests/unit/test_metadata_enricher_contract.py`
- **妤犲本鏁归弽鍥у櫙**閿?
  - 鐟欏嫬鍨Ο鈥崇础閿涙矮缍旀稉鍝勫幑鎼存洟鈧槒绶敍宀冪翻閸?metadata 韫囧懘銆忛崠鍛儓 `title/summary/tags`閿涘牐鍤︾亸鎴︽姜缁岀尨绱氶妴?
  - **LLM 濡€崇础閿涘牊鐗宠箛鍐跨礆**閿涙艾婀?LLM 閹垫挸绱戦惃鍕剰閸愬吀绗呴敍宀€鈥樻穱婵堟埂鐎圭偠鐨熼悽?LLM閿涘牊鍨ㄦ妯垮窛闁?Mock閿涘鑻熼悽鐔稿灇鐠囶厺绠熸稉鏉跨槣閻?metadata閵嗗倿娓舵宀冪槈閸︺劍婀侀惇鐔风杽 LLM 闁板秶鐤嗘稉瀣畱鏉╃偤鈧碍鈧傜瑢閺佸牊鐏夐妴?
  - 闂勫秶楠囩悰灞艰礋閿涙瓈LM 鐠嬪啰鏁ゆ径杈Е閺冭泛娲栭柅鈧崚鎷岊潐閸掓瑦膩瀵繒绮ㄩ弸婊愮礄閸欘垰婀?metadata 閺嶅洩顔囬梽宥囬獓閸樼喎娲滈敍灞肩稻娑撳秵濮忛崙楦垮毀閸涜棄绱撶敮闈╃礆閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_metadata_enricher_contract.py`閿涘苯鑻熺涵顔荤箽閸栧懎鎯堝鈧崥?LLM 閻ㄥ嫰娉﹂幋鎰ゴ鐠囨洜鏁ゆ笟瀣ㄢ偓?

### C7閿涙mageCaptioner閿涘牆褰查柅澶屾晸閹?caption + 闂勫秶楠囨稉宥夋▎婵夌儑绱?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`image_captioner.py`閿涙艾缍嬮崥顖滄暏 Vision LLM 娑撴柨鐡ㄩ崷?image_refs 閺冨墎鏁撻幋?caption 楠炶泛鍟撻崶?chunk metadata閿涙稑缍嬬粋浣烘暏/娑撳秴褰查悽?瀵倸鐖堕弮鎯拌泲闂勫秶楠囩捄顖氱窞閿涘奔绗夐梼璇差敚 ingestion閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/transform/image_captioner.py`
  - `config/prompts/image_captioning.txt`閿涘牅缍旀稉娲帛鐠?prompt 閺夈儲绨敍娑樺讲閸︺劍绁寸拠鏇氳厬濞夈劌鍙嗛弴澶稿敩閺傚洦婀伴敍?
  - `tests/unit/test_image_captioner_fallback.py`
- **妤犲本鏁归弽鍥у櫙**閿?
  - 閸氼垳鏁ゅΟ鈥崇础閿涙艾鐡ㄩ崷?image_refs 閺冩湹绱伴悽鐔稿灇 caption 楠炶泛鍟撻崗?metadata閿涘牊绁寸拠鏇氳厬閻?mock Vision LLM 閺傤叀鈻堢拫鍐暏娑撳氦绶崙鐚寸礆閵?
  - 闂勫秶楠囧Ο鈥崇础閿涙艾缍嬮柊宥囩枂缁備胶鏁ら幋鏍х磽鐢憡妞傞敍瀹慼unk 娣囨繄鏆€ image_refs閿涘奔绲炬稉宥囨晸閹?caption 娑撴梹鐖ｇ拋?`has_unprocessed_images`閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_image_captioner_fallback.py`閵?

### C8閿涙enseEncoder閿涘牅绶风挧?libs.embedding閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`dense_encoder.py`閿涘本濡?chunks.text 閹靛綊鍣洪柅浣稿弳 `BaseEmbedding`閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/embedding/dense_encoder.py`
  - `tests/unit/test_dense_encoder.py`
- **妤犲本鏁归弽鍥у櫙**閿涙瓱ncoder 鏉堟挸鍤崥鎴﹀櫤閺佷即鍣烘稉?chunks 閺佷即鍣烘稉鈧懛杈剧礉缂佹潙瀹虫稉鈧懛娣偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_dense_encoder.py`閵?

### C9閿涙瓔parseEncoder閿涘湐M25 缂佺喕顓告稉搴ょ翻閸戝搫顨栫痪锔肩礆
- **閻╊喗鐖?*閿涙艾鐤勯悳?`sparse_encoder.py`閿涙艾顕?chunks 瀵よ櫣鐝?BM25 閹碘偓闂団偓缂佺喕顓搁敍鍫濆讲閸忓牅绮庢潏鎾冲毉 term weights 缂佹挻鐎敍宀€鍌ㄥ鏇℃儰閸﹂绗呮稉鈧銉ヤ粵閿涘鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/embedding/sparse_encoder.py`
  - `tests/unit/test_sparse_encoder.py`
- **妤犲本鏁归弽鍥у櫙**閿涙俺绶崙铏圭波閺嬪嫬褰查悽銊ょ艾 bm25_indexer閿涙稑顕粚鐑樻瀮閺堫剚婀侀弰搴ｂ€樼悰灞艰礋閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_sparse_encoder.py`閵?

### C10閿涙atchProcessor閿涘牊澹掓径鍕倞缂傛牗甯撻敍?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`batch_processor.py`閿涙艾鐨?chunks 閸?batch閿涘矂鈹嶉崝?dense/sparse 缂傛牜鐖滈敍宀冾唶瑜版洘澹掑▎陇鈧妞傞敍鍫滆礋 trace 妫板嫮鏆€閿涘鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/embedding/batch_processor.py`
  - `tests/unit/test_batch_processor.py`
- **妤犲本鏁归弽鍥у櫙**閿涙瓬atch_size=2 閺冭泛顕?5 chunks 閸掑棙鍨?3 閹电櫢绱濇稉鏃堛€庢惔蹇暻旂€规哎鈧?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_batch_processor.py`閵?

---

**閳逛讲鏀ｉ埞浣叉敚 鐎涙ê鍋嶉梼鑸殿唽閸掑棛鏅痪鍖＄窗娴犮儰绗呮禒璇插鐠愮喕鐭楃亸鍡欑椽閻胶绮ㄩ弸婊勫瘮娑斿懎瀵?閳逛讲鏀ｉ埞浣叉敚**

> **鐠囧瓨妲?*閿涙8-C10鐎瑰本鍨氭禍鍜瞖nse閸滃parse閻ㄥ嫮绱惍浣镐紣娴ｆ粣绱滳11-C13鐠愮喕鐭楃亸鍡欑椽閻胶绮ㄩ弸婊冪摠閸屻劌鍩屾稉宥呮倱閻ㄥ嫬鎮楃粩顖樷偓?
> - **C11 (BM25Indexer)**閿涙艾顦╅悶鍝爌arse缂傛牜鐖滅紒鎾寸亯 閳?閺嬪嫬缂撻崐鎺撳笓缁便垹绱?閳?鐎涙ê鍋嶉崚鐗堟瀮娴犲墎閮寸紒?
> - **C12 (VectorUpserter)**閿涙艾顦╅悶鍜瞖nse缂傛牜鐖滅紒鎾寸亯 閳?閻㈢喐鍨氱粙鍐茬暰ID 閳?鐎涙ê鍋嶉崚鏉挎倻闁插繑鏆熼幑顔肩氨
> - **C13 (ImageStorage)**閿涙艾顦╅悶鍡楁禈閻楀洦鏆熼幑?閳?閺傚洣娆㈢€涙ê鍋?+ 缁便垹绱╅弰鐘茬殸

---

### C11閿涙M25Indexer閿涘牆鈧帗甯撶槐銏犵穿閺嬪嫬缂撴稉搴㈠瘮娑斿懎瀵查敍?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`bm25_indexer.py`閿涙碍甯撮弨?SparseEncoder 閻ㄥ墖erm statistics鏉堟挸鍤敍宀冾吀缁犳“DF閿涘本鐎鍝勨偓鎺撳笓缁便垹绱╅敍灞借嫙閹镐椒绠欓崠鏍у煂 `data/db/bm25/`閵?
- **閺嶇绺鹃崝鐔诲厴**閿?
  - 鐠侊紕鐣?IDF (Inverse Document Frequency)閿涙瓪IDF(term) = log((N - df + 0.5) / (df + 0.5))`
  - 閺嬪嫬缂撻崐鎺撳笓缁便垹绱╃紒鎾寸€敍姝歿term: {idf, postings: [{chunk_id, tf, doc_length}]}}`
  - 缁便垹绱╂惔蹇撳灙閸栨牔绗岄崝鐘烘祰閿涘牊鏁幐浣割杻闁插繑娲块弬棰佺瑢闁插秴缂撻敍?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/storage/bm25_indexer.py`
  - `tests/unit/test_bm25_indexer_roundtrip.py`
- **妤犲本鏁归弽鍥у櫙**閿?
  - build 閸氬氦鍏?load 楠炶泛顕崥灞肩鐠囶厽鏋￠弻銉嚄鏉╂柨娲栫粙鍐茬暰 top ids
  - IDF鐠侊紕鐣婚崙鍡欌€橀敍鍫濆讲閻劌鍑￠惌銉嚔閺傛瑥顕В鏃堢崣鐠囦緤绱?
  - 閺€顖涘瘮缁便垹绱╅柌宥呯紦娑撳骸顤冮柌蹇旀纯閺?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_bm25_indexer_roundtrip.py`閵?
- **婢跺洦鏁?*閿涙碍婀版禒璇插鐎瑰本鍨歋parse鐠侯垰绶為惃鍕付閸氬簼绔撮悳顖ょ礉娑撶瘚3 (SparseRetriever) 閹绘劒绶甸崣顖涚叀鐠囥垻娈態M25缁便垹绱╅妴?

### C12閿涙瓘ectorUpserter閿涘牆鎮滈柌蹇撶摠閸屻劋绗岄獮鍌滅搼閹傜箽鐠囦緤绱?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`vector_upserter.py`閿涙碍甯撮弨?DenseEncoder 閻ㄥ嫬鎮滈柌蹇氱翻閸戠尨绱濋悽鐔稿灇缁嬪啿鐣鹃惃?`chunk_id`閿涘苯鑻熺拫鍐暏 VectorStore 鏉╂稖顢戦獮鍌滅搼閸愭瑥鍙嗛妴?
- **閺嶇绺鹃崝鐔诲厴**閿?
  - 閻㈢喐鍨氱涵顔肩暰閹?chunk_id閿涙瓪hash(source_path + chunk_index + content_hash[:8])`
  - 鐠嬪啰鏁?`BaseVectorStore.upsert()` 閸愭瑥鍙嗛崥鎴﹀櫤閺佺増宓佹惔?
  - 娣囨繆鐦夐獮鍌滅搼閹嶇窗閸氬奔绔撮崘鍛啇闁插秴顦查崘娆忓弳娑撳秳楠囬悽鐔煎櫢婢跺秷顔囪ぐ?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/storage/vector_upserter.py`
  - `tests/unit/test_vector_upserter_idempotency.py`
- **妤犲本鏁归弽鍥у櫙**閿?
  - 閸氬奔绔?chunk 娑撱倖顐?upsert 娴溠呮晸閻╃鎮?id
  - 閸愬懎顔愰崣妯绘纯閺?id 閸欐ɑ娲?
  - 閺€顖涘瘮閹靛綊鍣?upsert 娑撴柧绻氶幐渚€銆庢惔?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_vector_upserter_idempotency.py`閵?
- **婢跺洦鏁?*閿涙碍婀版禒璇插鐎瑰本鍨欴ense鐠侯垰绶為惃鍕付閸氬簼绔撮悳顖ょ礉娑撶瘚2 (DenseRetriever) 閹绘劒绶甸崣顖涚叀鐠囥垻娈戦崥鎴﹀櫤閺佺増宓佹惔鎾扁偓?

### C13閿涙mageStorage閿涘牆娴橀悧鍥ㄦ瀮娴犺泛鐡ㄩ崒銊ょ瑢缁便垹绱╃悰銊ヮ殩缁撅讣绱?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`image_storage.py`閿涙矮绻氱€涙ê娴橀悧鍥у煂 `data/images/{collection}/`閿涘苯鑻熸担璺ㄦ暏 **SQLite** 鐠佹澘缍?image_id閳姫ath 閺勭姴鐨犻妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/storage/image_storage.py`
  - `tests/unit/test_image_storage.py`
- **妤犲本鏁归弽鍥у櫙**閿涙矮绻氱€涙ê鎮楅弬鍥︽鐎涙ê婀敍娑欑叀閹?image_id 鏉╂柨娲栧锝団€樼捄顖氱窞閿涙稒妲х亸鍕彠缁粯瀵旀稊鍛閸?`data/db/image_index.db`閵?
- **閹垛偓閺堫垱鏌熷?*閿?
  - 婢跺秶鏁ゆい鍦窗瀹稿弶婀侀惃?SQLite 閺嬭埖鐎Ο鈥崇础閿涘牆寮懓?`file_integrity.py` 閻?`SQLiteIntegrityChecker`閿?
  - 閺佺増宓佹惔鎾广€冪紒鎾寸€敍?
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
  - 閹绘劒绶甸獮璺哄絺鐎瑰鍙忕拋鍧楁６閿涘湹AL 濡€崇础閿?
  - 閺€顖涘瘮閹?collection 閹靛綊鍣洪弻銉嚄
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_image_storage.py`閵?

### C14閿涙瓍ipeline 缂傛牗甯撻敍鍦P 娑撹尪鎹ｉ弶銉礆
- **閻╊喗鐖?*閿涙艾鐤勯悳?`pipeline.py`閿涙矮瑕嗙悰灞惧⒔鐞涘矉绱檌ntegrity閳姡oad閳姱plit閳姲ransform閳姀ncode閳姱tore閿涘绱濋獮璺侯嚠婢惰精瑙﹀銉╊€冮崑姘閺呮澘绱撶敮鎼炩偓?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/pipeline.py`
  - `tests/integration/test_ingestion_pipeline.py`
- **濞村鐦弫鐗堝祦**閿?
  - **娑撶粯绁寸拠鏇熸瀮濡?*閿涙瓪tests/fixtures/sample_documents/complex_technical_doc.pdf`
    - 8缁旂姾濡幎鈧張顖涙瀮濡楋綇绱檦21KB閿?
    - 閸栧懎鎯?瀵姴绁甸崗銉ユ禈閻楀浄绱欓棁鈧ù瀣槸閸ュ墽澧栭幓鎰絿閸滃本寮挎潻甯礆
    - 閸栧懎鎯?娑擃亣銆冮弽纭风礄濞村鐦悰銊︾壐閸愬懎顔愮憴锝嗙€介敍?
    - 婢舵岸銆夋径姘唽閽€鏂ょ礄濞村鐦€瑰本鏆ｉ崚鍡楁健濞翠胶鈻奸敍?
  - **鏉堝懎濮ù瀣槸**閿涙瓪tests/fixtures/sample_documents/simple.pdf`閿涘牏鐣濋崡鏇炴簚閺咁垰娲栬ぐ鎺炵礆
- **妤犲本鏁归弽鍥у櫙**閿?
  - 鐎?`complex_technical_doc.pdf` 鐠烘垵鐣弫?pipeline閿涘本鍨氶崝鐔荤翻閸戠尨绱?
    - 閸氭垿鍣虹槐銏犵穿閺傚洣娆㈤崚?ChromaDB
    - BM25 缁便垹绱╅弬鍥︽閸?`data/db/bm25/`
    - 閹绘劕褰囬惃鍕禈閻楀洤鍩?`data/images/` (SHA256閸涜棄鎮?
  - Pipeline 閺冦儱绻斿〒鍛珰鐏炴洜銇氶崥鍕▉濞堜絻绻樻惔?
  - 婢惰精瑙﹀銉╊€冮幎娑樺毉閺勫海鈥樺鍌氱埗娣団剝浼?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -v tests/integration/test_ingestion_pipeline.py`閵?

### C15閿涙俺鍓奸張顒€鍙嗛崣?ingest.py閿涘牏顬囩痪鍨讲閻㈩煉绱?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`scripts/ingest.py`閿涘本鏁幐?`--collection`閵嗕梗--path`閵嗕梗--force`閿涘苯鑻熺拫鍐暏 pipeline閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `scripts/ingest.py`
  - `tests/e2e/test_data_ingestion.py`
- **妤犲本鏁归弽鍥у櫙**閿涙艾鎳℃禒銈堫攽閸欘垵绻嶇悰灞借嫙閸?`data/db` 娴溠呮晸娴溠呭⒖閿涙盯鍣告径宥堢箥鐞涘苯婀張顏勫綁閺囧瓨妞傜捄瀹犵箖閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/e2e/test_data_ingestion.py`閿涘牆鏁栭柌蹇曟暏娑撳瓨妞傞惄顔肩秿閿涘鈧?

---

## 闂冭埖顔?D閿涙瓓etrieval MVP閿涘牏娲伴弽鍥风窗閼?query 楠炴儼绻戦崶?Top-K chunks閿?

### D1閿涙瓐ueryProcessor閿涘牆鍙ч柨顔跨槤閹绘劕褰?+ filters 缂佹挻鐎敍?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`query_processor.py`閿涙艾鍙ч柨顔跨槤閹绘劕褰囬敍鍫濆帥鐟欏嫬鍨?閸掑棜鐦濋敍澶涚礉楠炴儼袙閺嬫劙鈧氨鏁?filters 缂佹挻鐎敍鍫濆讲缁屽搫鐤勯悳甯礆閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/query_engine/query_processor.py`
  - `tests/unit/test_query_processor.py`
- **妤犲本鏁归弽鍥у櫙**閿涙艾顕潏鎾冲弳 query 鏉堟挸鍤?`keywords` 闂堢偟鈹栭敍鍫濆讲閺嶈宓侀崑婊呮暏鐠囧秶鐡ラ悾銉礆閿涘畺ilters 娑?dict閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_query_processor.py`閵?

### D2閿涙enseRetriever閿涘牐鐨熼悽?VectorStore.query閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`dense_retriever.py`閿涘瞼绮嶉崥?`EmbeddingClient`閿涘潿uery 閸氭垿鍣洪崠鏍电礆+ `VectorStore`閿涘牆鎮滈柌蹇旑梾缁鳖澁绱氶敍灞界暚閹存劘顕㈡稊澶婂将閸ョ偑鈧?
- **閸撳秶鐤嗘禒璇插**閿?
  1. 闂団偓閸忓牆婀?`src/core/types.py` 娑擃厼鐣炬稊?`RetrievalResult` 缁鐎烽敍鍫濆瘶閸?`chunk_id`, `score`, `text`, `metadata` 鐎涙顔岄敍?
  2. 闂団偓绾喛顓?ChromaStore.query() 鏉╂柨娲栫紒鎾寸亯閸栧懎鎯?text閿涘牆缍嬮崜宥呯摠閸屻劌婀?documents 鐎涙顔岄敍宀勬付鐞涖儱鍘栨潻鏂挎礀閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/types.py`閿涘牊鏌婃晶?`RetrievalResult` 缁鐎烽敍?
  - `src/libs/vector_store/chroma_store.py`閿涘牅鎱ㄦ径宥忕窗query 鏉╂柨娲栫紒鎾寸亯闂団偓閸栧懎鎯?text 鐎涙顔岄敍?
  - `src/core/query_engine/dense_retriever.py`
  - `tests/unit/test_dense_retriever.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `RetrievalResult` dataclass閿涙瓪chunk_id: str`, `score: float`, `text: str`, `metadata: Dict`
  - `DenseRetriever.__init__(settings, embedding_client?, vector_store?)`閿涙碍鏁幐浣风贩鐠ф牗鏁為崗銉ф暏娴滃孩绁寸拠?
  - `DenseRetriever.retrieve(query: str, top_k: int, filters?: dict, trace?) -> List[RetrievalResult]`
  - 閸愬懘鍎村ù浣衡柤閿涙瓪query 閳?embedding_client.embed([query]) 閳?vector_store.query(vector, top_k, filters) 閳?娴犲氦绻戦崶鐐电波閺嬫粍褰侀崣?text 閳?鐟欏嫯瀵栭崠鏍波閺嬫竴
- **妤犲本鏁归弽鍥у櫙**閿?
  - `RetrievalResult` 缁鐎峰鎻掔暰娑斿鑻熼崣顖氱碍閸掓瀵?
  - ChromaStore.query() 鏉╂柨娲栫紒鎾寸亯閸栧懎鎯?`text` 鐎涙顔?
  - 鐎电绶崗?query 閼崇晫鏁撻幋?embedding 楠炴儼鐨熼悽?VectorStore 濡偓缁?
  - 鏉╂柨娲栫紒鎾寸亯閸栧懎鎯?`chunk_id`閵嗕梗score`閵嗕梗text`閵嗕梗metadata`
  - mock EmbeddingClient 閸?VectorStore 閺冩儼鍏樺锝団€樼紓鏍ㄥ笓鐠嬪啰鏁?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_dense_retriever.py`閿涘潰ock embedding + vector store閿涘鈧?

### D3閿涙瓔parseRetriever閿涘湐M25 閺屻儴顕楅敍?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`sparse_retriever.py`閿涙矮绮?`data/db/bm25/` 鏉炶棄鍙嗙槐銏犵穿楠炶埖鐓＄拠顫偓?
- **閸撳秶鐤嗘禒璇插**閿涙岸娓堕崷?`BaseVectorStore` 閸?`ChromaStore` 娑擃厽鍧婇崝?`get_by_ids()` 閺傝纭堕敍宀€鏁ゆ禍搴㈢壌閹?chunk_id 閹靛綊鍣洪懢宄板絿 text 閸?metadata
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/libs/vector_store/base_vector_store.py`閿涘牊鏌婃晶?`get_by_ids()` 閹跺€熻杽閺傝纭堕敍?
  - `src/libs/vector_store/chroma_store.py`閿涘牆鐤勯悳?`get_by_ids()` 閺傝纭堕敍?
  - `src/core/query_engine/sparse_retriever.py`
  - `tests/unit/test_sparse_retriever.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `BaseVectorStore.get_by_ids(ids: List[str]) -> List[Dict]`閿涙碍鐗撮幑?ID 閹靛綊鍣洪懢宄板絿鐠佹澘缍?
  - `ChromaStore.get_by_ids(ids: List[str]) -> List[Dict]`閿涙俺鐨熼悽?ChromaDB 閻?get 閺傝纭?
  - `SparseRetriever.__init__(settings, bm25_indexer?, vector_store?)`閿涙碍鏁幐浣风贩鐠ф牗鏁為崗銉ф暏娴滃孩绁寸拠?
  - `SparseRetriever.retrieve(keywords: List[str], top_k: int, trace?) -> List[RetrievalResult]`
  - 閸愬懘鍎村ù浣衡柤閿?
    1. `keywords 閳?bm25_indexer.query(keywords, top_k) 閳?[{chunk_id, score}]`
    2. `chunk_ids 閳?vector_store.get_by_ids(chunk_ids) 閳?[{id, text, metadata}]`
    3. 閸氬牆鑻?score 娑?text/metadata閿涘瞼绮嶇憗鍛礋 `RetrievalResult` 閸掓銆?
  - 濞夈劍鍓伴敍姝琫ywords 閺夈儴鍤?`QueryProcessor.process()` 閻?`ProcessedQuery.keywords`
- **妤犲本鏁归弽鍥у櫙**閿?
  - `BaseVectorStore.get_by_ids()` 閸?`ChromaStore.get_by_ids()` 瀹告彃鐤勯悳?
  - 鐎电懓鍑￠弸鍕紦缁便垹绱╅惃?fixtures 鐠囶厽鏋￠敍灞藉彠闁款喛鐦濆Λ鈧槐銏犳嚒娑擃參顣╅張?chunk_id
  - 鏉╂柨娲栫紒鎾寸亯閸栧懎鎯堢€瑰本鏆ｉ惃?text 閸?metadata
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_sparse_retriever.py`閵?

### D4閿涙usion閿涘湩RF 鐎圭偟骞囬敍?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`fusion.py`閿涙瓓RF 閾诲秴鎮?dense/sparse 閹烘帒鎮曢獮鎯扮翻閸戣櫣绮烘稉鈧幒鎺戠碍閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/query_engine/fusion.py`
  - `tests/unit/test_fusion_rrf.py`
- **妤犲本鏁归弽鍥у櫙**閿涙艾顕弸鍕偓鐘垫畱閹烘帒鎮曟潏鎾冲弳鏉堟挸鍤?deterministic閿涙舶 閸欏倹鏆熼崣顖炲帳缂冾喓鈧?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_fusion_rrf.py`閵?

### D5閿涙ybridSearch 缂傛牗甯?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`hybrid_search.py`閿涙氨绱幒?Dense + Sparse + Fusion 閻ㄥ嫬鐣弫瀛樿穿閸氬牊顥呯槐銏＄ウ缁嬪绱濋獮鍫曟肠閹?Metadata 鏉╁洦鎶ら柅鏄忕帆閵?
- **閸撳秶鐤嗘笟婵婄**閿涙1閿涘湨ueryProcessor閿涘鈧笍2閿涘湒enseRetriever閿涘鈧笍3閿涘湯parseRetriever閿涘鈧笍4閿涘湗usion閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/query_engine/hybrid_search.py`
  - `tests/integration/test_hybrid_search.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `HybridSearch.__init__(settings, query_processor, dense_retriever, sparse_retriever, fusion)`
  - `HybridSearch.search(query: str, top_k: int, filters?: dict, trace?) -> List[RetrievalResult]`
  - `HybridSearch._apply_metadata_filters(candidates, filters) -> List[RetrievalResult]`閿涙艾鎮楃純顔跨箖濠娿倕鍘规惔?
  - 閸愬懘鍎村ù浣衡柤閿涙瓪query_processor.process() 閳?楠炴儼顢?dense.retrieve + sparse.retrieve) 閳?fusion.fuse() 閳?metadata_filter 閳?Top-K`
- **妤犲本鏁归弽鍥у櫙**閿?
  - 鐎?fixtures 閺佺増宓侀敍宀冨厴鏉╂柨娲?Top-K閿涘牆瀵橀崥?chunk 閺傚洦婀版稉?metadata閿?
  - 閺€顖涘瘮 filters 閸欏倹鏆熼敍鍫濐洤 `collection`閵嗕梗doc_type`閿涘绻樼悰宀冪箖濠?
  - Dense/Sparse 娴犺绔寸捄顖氱窞婢惰精瑙﹂弮鎯板厴闂勫秶楠囬崚鏉垮礋鐠侯垳绮ㄩ弸?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_hybrid_search.py`閵?

### D6閿涙瓓eranker閿涘湑ore 鐏炲倻绱幒?+ fallback閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`core/query_engine/reranker.py`閿涙碍甯撮崗?`libs.reranker` 閸氬海顏敍灞姐亼鐠?鐡掑懏妞傞崶鐐衡偓鈧?fusion 閹烘帒鎮曢妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/query_engine/reranker.py`
  - `config/prompts/rerank.txt`閿涘牅绮庤ぐ鎾虫儙閻?LLM Rerank 閸氬海顏弮鏈靛▏閻㈩煉绱?
  - `tests/unit/test_reranker_fallback.py`
- **妤犲本鏁归弽鍥у櫙**閿涙碍膩閹风喎鎮楃粩顖氱磽鐢憡妞傛稉宥呭閸濆秵娓剁紒鍫ｇ箲閸ョ儑绱濇稉鏃€鐖ｇ拋?fallback=true閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_reranker_fallback.py`閵?

### D7閿涙俺鍓奸張顒€鍙嗛崣?query.py閿涘牊鐓＄拠銏犲讲閻㈩煉绱?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`scripts/query.py`閿涘奔缍旀稉鍝勬躬缁炬寧鐓＄拠銏㈡畱閸涙垝鎶ょ悰灞藉弳閸欙綇绱濈拫鍐暏鐎瑰本鏆ｉ惃?HybridSearch + Reranker 濞翠胶鈻奸獮鎯扮翻閸戠儤顥呯槐銏㈢波閺嬫嚎鈧?
- **閸撳秶鐤嗘笟婵婄**閿涙5閿涘湚ybridSearch閿涘鈧笍6閿涘湩eranker閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `scripts/query.py`
- **鐎圭偟骞囬崝鐔诲厴**閿?
  - **閸欏倹鏆熼弨顖涘瘮**閿?
    - `--query "闂傤噣顣?`閿涙艾绻€婵夘偓绱濋弻銉嚄閺傚洦婀?
    - `--top-k 10`閿涙艾褰查柅澶涚礉鏉╂柨娲栫紒鎾寸亯閺佷即鍣洪敍鍫ョ帛鐠?10閿?
    - `--collection xxx`閿涙艾褰查柅澶涚礉闂勬劕鐣惧Λ鈧槐銏ゆ肠閸?
    - `--verbose`閿涙艾褰查柅澶涚礉閺勫墽銇氶崥鍕▉濞堝吀鑵戦梻瀵哥波閺?
    - `--no-rerank`閿涙艾褰查柅澶涚礉鐠哄疇绻?Reranker 闂冭埖顔?
  - **鏉堟挸鍤崘鍛啇**閿?
    - 姒涙顓诲Ο鈥崇础閿涙瓖op-K 缂佹挻鐏夐敍鍫濈碍閸欐灚鈧够core閵嗕焦鏋冮張顒佹喅鐟曚降鈧焦娼靛┃鎰瀮娴犺翰鈧線銆夐惍渚婄礆
    - Verbose 濡€崇础閿涙岸顤傛径鏍ㄦ▔缁€?Dense 閸欘剙娲栫紒鎾寸亯閵嗕讣parse 閸欘剙娲栫紒鎾寸亯閵嗕笚usion 缂佹挻鐏夐妴涓積rank 缂佹挻鐏?
  - **閸愬懘鍎村ù浣衡柤**閿?
    1. 閸旂姾娴囬柊宥囩枂 `Settings`
    2. 閸掓繂顫愰崠鏍矋娴犺绱橢mbeddingClient閵嗕箓ectorStore閵嗕竻M25Indexer閵嗕阜eranker閿?
    3. 閸掓稑缂?`QueryProcessor`閵嗕梗DenseRetriever`閵嗕梗SparseRetriever`閵嗕梗HybridSearch` 鐎圭偘绶?
    4. 鐠嬪啰鏁?`HybridSearch.search()` 閼惧嘲褰囬崐娆撯偓澶岀波閺?
    5. 鐠嬪啰鏁?`Reranker.rerank()` 鏉╂稖顢戠划鐐笓閿涘牓娅庨棃?`--no-rerank`閿?
    6. 閺嶇厧绱￠崠鏍翻閸戣櫣绮ㄩ弸?
- **妤犲本鏁归弽鍥у櫙**閿?
  - 閸涙垝鎶ょ悰灞藉讲鏉╂劘顢戦敍姝歱ython scripts/query.py --query "婵″倷缍嶉柊宥囩枂 Azure閿?`
  - 鏉╂柨娲栭弽鐓庣础閸栨牜娈?Top-K 濡偓缁便垻绮ㄩ弸?
  - `--verbose` 濡€崇础閺勫墽銇氶崥鍕▉濞堝吀鑵戦梻瀵哥波閺嬫粣绱欐笟澶哥艾鐠嬪啳鐦敍?
  - 閺冪姵鏆熼幑顔芥鏉╂柨娲栭崣瀣偨閹绘劗銇氶敍鍫濐洤"閺堫亝澹橀崚鎵祲閸忚櫕鏋冨锝忕礉鐠囧嘲鍘涙潻鎰攽 ingest.py 閹藉嫬褰囬弫鐗堝祦"閿?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊ㄧ箥鐞?`python scripts/query.py --query "濞村鐦弻銉嚄" --verbose`閿涘牅绶风挧鏍у嚒閹藉嫬褰囬惃鍕殶閹诡噯绱氶妴?
- **娑?MCP Tool 閻ㄥ嫬鍙х化?*閿?
  - `scripts/query.py` 閺勵垰绱戦崣鎴ｇ殶鐠囨洜鏁ら惃鍕嚒娴犮倛顢戝銉ュ徔
  - `E3 query_knowledge_hub` 閺勵垳鏁撴禍褏骞嗘晶鍐畱 MCP Tool
  - 娑撱倛鈧懎鍙℃禍?Core 鐏炲倿鈧槒绶敍鍦歽bridSearch + Reranker閿涘绱濇担鍡楀弳閸欙絽鎷版潏鎾冲毉閺嶇厧绱℃稉宥呮倱

---

## 闂冭埖顔?E閿涙瓉CP Server 鐏炲倷绗?Tools閿涘牏娲伴弽鍥风窗鐎电懓顦婚崣顖滄暏閻?MCP tools閿?

### E1閿涙瓉CP Server 閸忋儱褰涙稉?Stdio 缁撅附娼?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`mcp_server/server.py`閿涙岸浼掑?stdout 閸欘亣绶崙?MCP 濞戝牊浼呴敍灞炬）韫囨鍩?stderr"閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/mcp_server/server.py`
  - `tests/integration/test_mcp_server.py`
- **妤犲本鏁归弽鍥у櫙**閿涙艾鎯庨崝?server 閼宠棄鐣幋?initialize閿涙硞tderr 閺堝妫╄箛妞剧稻 stdout 娑撳秵钖勯弻鎾扁偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_mcp_server.py`閿涘牆鐡欐潻娑氣柤閺傜懓绱￠敍澶堚偓?

### E2閿涙瓍rotocol Handler 閸楀繗顔呯憴锝嗙€芥稉搴ゅ厴閸旀稑宕楅崯?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`mcp_server/protocol_handler.py`閿涙艾鐨濈憗?JSON-RPC 2.0 閸楀繗顔呯憴锝嗙€介敍灞筋槱閻?`initialize`閵嗕梗tools/list`閵嗕梗tools/call` 娑撳琚弽绋跨妇閺傝纭堕敍灞借嫙鐎圭偟骞囩憴鍕瘱閻ㄥ嫰鏁婄拠顖氼槱閻炲棎鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/mcp_server/protocol_handler.py`
  - `tests/unit/test_protocol_handler.py`
- **鐎圭偟骞囩憰浣哄仯**閿?
  - **ProtocolHandler 缁?*閿?
    - `handle_initialize(params)` 閳?鏉╂柨娲?server capabilities閿涘牊鏁幐浣烘畱 tools 閸掓銆冮妴浣哄閺堫兛淇婇幁顖ょ礆
    - `handle_tools_list()` 閳?鏉╂柨娲栧鍙夋暈閸愬瞼娈?tool schema閿涘潱ame, description, inputSchema閿?
    - `handle_tools_call(name, arguments)` 閳?鐠侯垳鏁遍崚鏉垮徔娴?tool 閹笛嗩攽閿涘本宕熼懢宄扮磽鐢鑻熸潪顒佸床娑?JSON-RPC error
  - **闁挎瑨顕ら惍浣筋潐閼?*閿涙岸浼掑?JSON-RPC 2.0閿?32600 Invalid Request, -32601 Method not found, -32602 Invalid params, -32603 Internal error閿?
  - **閼宠棄濮忛崡蹇撴櫌**閿涙艾婀?`initialize` 閸濆秴绨叉稉顓烇紣閺?`capabilities.tools`
- **妤犲本鏁归弽鍥у櫙**閿?
  - 閸欐垿鈧?`initialize` 鐠囬攱鐪伴懗鍊熺箲閸ョ偞顒滅涵顔炬畱 `serverInfo` 閸?`capabilities`
  - 閸欐垿鈧?`tools/list` 閼冲€熺箲閸ョ偛鍑″▔銊ュ斀 tools 閻?schema
  - 閸欐垿鈧?`tools/call` 閼宠姤顒滅涵顔跨熅閻㈠崬鑻熸潻鏂挎礀缂佹挻鐏夐幋鏍潐閼煎啴鏁婄拠?
  - **闁挎瑨顕ゆ径鍕倞**閿涙碍妫ら弫鍫熸煙濞夋洝绻戦崶?-32601閿涘苯寮弫浼存晩鐠囶垵绻戦崶?-32602閿涘苯鍞撮柈銊ョ磽鐢瓕绻戦崶?-32603 娑撴柧绗夊▔鍕苟閸棙鐖?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_protocol_handler.py`閵?

### E3閿涙艾鐤勯悳?tool閿涙uery_knowledge_hub
- **閻╊喗鐖?*閿涙艾鐤勯悳?`tools/query_knowledge_hub.py`閿涙俺鐨熼悽?HybridSearch + Reranker閿涘本鐎鍝勭敨瀵洜鏁ら惃鍕惙鎼存棑绱濇潻鏂挎礀 Markdown + structured citations閵?
- **閸撳秶鐤嗘笟婵婄**閿涙5閿涘湚ybridSearch閿涘鈧笍6閿涘湩eranker閿涘鈧笒1閿涘湯erver閿涘鈧笒2閿涘湧rotocol Handler閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/mcp_server/tools/query_knowledge_hub.py`
  - `src/core/response/response_builder.py`閿涘牊鏌婃晶鐑囩窗閺嬪嫬缂?MCP 閸濆秴绨查弽鐓庣础閿?
  - `src/core/response/citation_generator.py`閿涘牊鏌婃晶鐑囩窗閻㈢喐鍨氬鏇犳暏娣団剝浼呴敍?
  - `tests/unit/test_response_builder.py`閿涘牊鏌婃晶鐑囩礆
  - `tests/integration/test_mcp_server.py`閿涘牐藟閻劋绶ラ敍?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `ResponseBuilder.build(retrieval_results, query) -> MCPResponse`閿涙碍鐎?MCP 閺嶇厧绱￠崫宥呯安
  - `CitationGenerator.generate(retrieval_results) -> List[Citation]`閿涙氨鏁撻幋鎰穿閻劌鍨悰?
  - `query_knowledge_hub(query, top_k?, collection?) -> MCPToolResult`閿涙瓖ool 閸忋儱褰涢崙鑺ユ殶
- **妤犲本鏁归弽鍥у櫙**閿?
  - tool 鏉╂柨娲?`content[0]` 娑撳搫褰茬拠?Markdown閿涘牆鎯?`[1]`閵嗕梗[2]` 缁涘绱╅悽銊︾垼濞夘煉绱?
  - `structuredContent.citations` 閸栧懎鎯?`source`/`page`/`chunk_id`/`score` 鐎涙顔?
  - 閺冪姷绮ㄩ弸婊勬鏉╂柨娲栭崣瀣偨閹绘劗銇氶懓宀勬姜缁岀儤鏆熺紒?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_mcp_server.py -k query_knowledge_hub`閵?

### E4閿涙艾鐤勯悳?tool閿涙ist_collections
- **閻╊喗鐖?*閿涙艾鐤勯悳?`tools/list_collections.py`閿涙艾鍨崙?`data/documents/` 娑撳娉﹂崥鍫濊嫙闂勫嫬鐢紒鐔活吀閿涘牆褰插璺烘倵閸掗绗呮稉鈧銉礆閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/mcp_server/tools/list_collections.py`
  - `tests/unit/test_list_collections.py`
- **妤犲本鏁归弽鍥у櫙**閿涙艾顕?fixtures 娑擃厾娈戦惄顔肩秿缂佹挻鐎懗鍊熺箲閸ョ偤娉﹂崥鍫濇倳閸掓銆冮妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_list_collections.py`閵?

### E5閿涙艾鐤勯悳?tool閿涙et_document_summary
- **閻╊喗鐖?*閿涙艾鐤勯悳?`tools/get_document_summary.py`閿涙碍瀵?doc_id 鏉╂柨娲?title/summary/tags閿涘牆褰查崗鍫滅矤 metadata/缂傛挸鐡ㄩ崣鏍电礆閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/mcp_server/tools/get_document_summary.py`
  - `tests/unit/test_get_document_summary.py`
- **妤犲本鏁归弽鍥у櫙**閿涙艾顕稉宥呯摠閸?doc_id 鏉╂柨娲栫憴鍕瘱闁挎瑨顕ら敍娑樼摠閸︺劍妞傛潻鏂挎礀缂佹挻鐎崠鏍︿繆閹垬鈧?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_get_document_summary.py`閵?

### E6閿涙艾顦垮Ο鈩冣偓浣界箲閸ョ偟绮嶇憗鍜冪礄Text + Image閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`multimodal_assembler.py`閿涙艾鎳℃稉?chunk 閸?image_refs 閺冩儼顕伴崣鏍ф禈閻楀洤鑻?base64 鏉╂柨娲?ImageContent閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/response/multimodal_assembler.py`
  - `tests/integration/test_mcp_server.py`閿涘牐藟閸ユ儳鍎氭潻鏂挎礀閻劋绶ラ敍?
- **妤犲本鏁归弽鍥у櫙**閿涙俺绻戦崶?content 娑擃厼瀵橀崥?image type閿涘imeType 濮濓絿鈥橀敍瀹抋ta 娑?base64 鐎涙顑佹稉灞傗偓?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_mcp_server.py -k image`閵?

---

## 闂冭埖顔?F閿涙瓖race 閸╄櫣顢呯拋鐐煢娑撳孩澧﹂悙鐧哥礄閻╊喗鐖ｉ敍娆糿gestion + Query 閸欏矂鎽肩捄顖氬讲鏉╁€熼嚋閿?

### F1閿涙瓖raceContext 婢х偛宸遍敍鍧抜nish + 閼版妞傜紒鐔活吀 + trace_type閿?
- **閻╊喗鐖?*閿涙艾顤冨鍝勫嚒閺堝娈?`TraceContext`閿涘湑5 瀹告彃鐤勯悳鏉跨唨绾偓閻楀牞绱氶敍灞惧潑閸?`finish()` 閺傝纭堕妴浣解偓妤佹缂佺喕顓搁妴涔race_type` 鐎涙顔岄敍鍫濆隘閸?query/ingestion閿涘鈧梗to_dict()` 鎼村繐鍨崠鏍у閼冲鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/trace/trace_context.py`閿涘牆顤冨鐚寸窗濞ｈ濮?trace_type/finish/elapsed_ms/to_dict閿?
  - `src/core/trace/trace_collector.py`閿涘牊鏌婃晶鐑囩窗閺€鍫曟肠楠炶埖瀵旀稊鍛 trace閿?
  - `tests/unit/test_trace_context.py`閿涘牐藟閸?finish/to_dict 閻╃鍙уù瀣槸閿?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `TraceContext.__init__(trace_type: str = "query")`閿涙碍鏁幐?`"query"` 閹?`"ingestion"` 缁鐎?
  - `TraceContext.finish() -> None`閿涙碍鐖ｇ拋?trace 缂佹挻娼敍宀冾吀缁犳鈧槒鈧妞?
  - `TraceContext.elapsed_ms(stage_name?) -> float`閿涙俺骞忛崣鏍ㄥ瘹鐎规岸妯佸▓鍨灗閹槒鈧妞?
  - `TraceContext.to_dict() -> dict`閿涙艾绨崚妤€瀵叉稉鍝勫讲 JSON 鏉堟挸鍤惃鍕摟閸忛潻绱欓崥?trace_type閿?
  - `TraceCollector.collect(trace: TraceContext) -> None`閿涙碍鏁归梿?trace 楠炴儼袝閸欐垶瀵旀稊鍛
- **妤犲本鏁归弽鍥у櫙**閿?
  - `record_stage` 鏉╄棄濮為梼鑸殿唽閺佺増宓侀敍鍫濆嚒閺堝绱?
  - `finish()` 閸?`to_dict()` 鏉堟挸鍤崠鍛儓 `trace_id`閵嗕梗trace_type`閵嗕梗started_at`閵嗕梗finished_at`閵嗕梗total_elapsed_ms`閵嗕梗stages`
  - 鏉堟挸鍤?dict 閸欘垳娲块幒?`json.dumps()` 鎼村繐鍨崠?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_trace_context.py`閵?


### F2閿涙氨绮ㄩ弸鍕閺冦儱绻?logger閿涘湞SON Lines閿?
- **閻╊喗鐖?*閿涙艾顤冨?`observability/logger.py`閿涘本鏁幐?JSON Lines 閺嶇厧绱℃潏鎾冲毉閿涘苯鑻熺€圭偟骞?trace 閹镐椒绠欓崠鏍у煂 `logs/traces.jsonl`閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/logger.py`閿涘牆顤冨鐚寸窗濞ｈ濮?JSONFormatter + FileHandler閿?
  - `tests/unit/test_jsonl_logger.py`
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `JSONFormatter`閿涙俺鍤滅€规矮绠?logging Formatter閿涘矁绶崙?JSON 閺嶇厧绱?
  - `get_trace_logger() -> logging.Logger`閿涙俺骞忛崣鏍帳缂冾喕绨?JSON Lines 鏉堟挸鍤惃?logger
  - `write_trace(trace_dict: dict) -> None`閿涙艾鐨?trace 鐎涙鍚€閸愭瑥鍙?`logs/traces.jsonl`
- **娑?F1 閻ㄥ嫬鍨庡?*閿?
  - F1 鐠愮喕鐭?TraceContext 閻ㄥ嫭鏆熼幑顔剧波閺嬪嫸绱欓崥?`trace_type`閿涘鎷?`finish()` 閺傝纭?
  - F2 鐠愮喕鐭楃亸?`trace.to_dict()` 閻ㄥ嫮绮ㄩ弸婊勫瘮娑斿懎瀵查崚鐗堟瀮娴?
- **妤犲本鏁归弽鍥у櫙**閿涙艾鍟撻崗銉ょ閺?trace 閸氬孩鏋冩禒鑸垫煀婢х偘绔寸悰灞芥値濞?JSON閿涘苯瀵橀崥?`trace_type` 鐎涙顔岄妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_jsonl_logger.py`閵?

### F3閿涙艾婀?Query 闁炬崘鐭鹃幍鎾跺仯
- **閻╊喗鐖?*閿涙艾婀?HybridSearch/Rerank 娑擃厽鏁為崗?TraceContext閿涘潉trace_type="query"`閿涘绱濋崚鈺冩暏 B 闂冭埖顔岄幎鍊熻杽閹恒儱褰涙稉顓㈩暕閻ｆ瑧娈?`trace` 閸欏倹鏆熼敍灞炬▔瀵繗鐨熼悽?`trace.record_stage()` 鐠佹澘缍嶉崥鍕▉濞堝灚鏆熼幑顔衡偓?
- **閸撳秶鐤嗘笟婵婄**閿涙5閿涘湚ybridSearch閿涘鈧笍6閿涘湩eranker閿涘鈧笚1閿涘湵raceContext 婢х偛宸遍敍澶堚偓涓?閿涘牏绮ㄩ弸鍕閺冦儱绻旈敍?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/core/query_engine/hybrid_search.py`閿涘牆顤冮崝?trace 鐠佹澘缍嶉敍姝瀍nse/sparse/fusion 闂冭埖顔岄敍?
  - `src/core/query_engine/reranker.py`閿涘牆顤冮崝?trace 鐠佹澘缍嶉敍姝砮rank 闂冭埖顔岄敍?
  - `tests/integration/test_hybrid_search.py`閿涘牊鏌囩懛鈧?trace 娑擃厼鐡ㄩ崷銊ユ倗闂冭埖顔岄敍?
- **鐠囧瓨妲?*閿涙 闂冭埖顔岄惃鍕复閸欙絽鍑℃０鍕殌 `trace: TraceContext | None = None` 閸欏倹鏆熼敍灞炬拱娴犺濮熺拹鐔荤煑閸︺劏鐨熼悽銊︽娴肩姴鍙嗙€圭偤妾惃?TraceContext 鐎圭偘绶ラ敍灞借嫙閸︺劌鎮囬梼鑸殿唽鐠佹澘缍?`method`/`provider`/`details` 鐎涙顔岄妴?
- **妤犲本鏁归弽鍥у櫙**閿?
  - 娑撯偓濞嗏剝鐓＄拠銏㈡晸閹?trace閿涘苯瀵橀崥?`query_processing`/`dense_retrieval`/`sparse_retrieval`/`fusion`/`rerank` 闂冭埖顔?
  - 濮ｅ繋閲滈梼鑸殿唽鐠佹澘缍?`elapsed_ms` 閼版妞傜€涙顔岄崪?`method` 鐎涙顔?
  - `trace.to_dict()` 娑?`trace_type == "query"`
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_hybrid_search.py`閵?

### F4閿涙艾婀?Ingestion 闁炬崘鐭鹃幍鎾跺仯
- **閻╊喗鐖?*閿涙艾婀?IngestionPipeline 娑擃厽鏁為崗?TraceContext閿涘潉trace_type="ingestion"`閿涘绱濈拋鏉跨秿閸氬嫭鎲氶崣鏍▉濞堢數娈戞径鍕倞閺佺増宓侀妴?
- **閸撳秶鐤嗘笟婵婄**閿涙5閿涘湧ipeline閿涘鈧笚1閿涘湵raceContext 婢х偛宸遍敍澶堚偓涓?閿涘牏绮ㄩ弸鍕閺冦儱绻旈敍?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/pipeline.py`閿涘牆顤冮崝?trace 娴肩娀鈧帪绱發oad/split/transform/embed/upsert 闂冭埖顔岄敍?
  - `tests/integration/test_ingestion_pipeline.py`閿涘牊鏌囩懛鈧?trace 娑擃厼鐡ㄩ崷銊ユ倗闂冭埖顔岄敍?
- **妤犲本鏁归弽鍥у櫙**閿?
  - 娑撯偓濞嗏剝鎲氶崣鏍晸閹?trace閿涘苯瀵橀崥?`load`/`split`/`transform`/`embed`/`upsert` 闂冭埖顔?
  - 濮ｅ繋閲滈梼鑸殿唽鐠佹澘缍?`elapsed_ms`閵嗕梗method`閿涘牆顩?markitdown/recursive/chroma閿涘鎷版径鍕倞鐠囷附鍎?
  - `trace.to_dict()` 娑?`trace_type == "ingestion"`
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_ingestion_pipeline.py`閵?

### F5閿涙瓍ipeline 鏉╂稑瀹抽崶鐐剁殶 (on_progress)
- **閻╊喗鐖?*閿涙艾婀?`IngestionPipeline.run()` 閺傝纭舵稉顓熸煀婢х偛褰查柅?`on_progress` 閸ョ偠鐨熼崣鍌涙殶閿涘本鏁幐浣割樆闁劌鐤勯弮鎯板箯閸欐牕顦╅悶鍡氱箻鎼达负鈧?
- **閸撳秶鐤嗘笟婵婄**閿涙4閿涘湜ngestion 閹垫挾鍋ｉ敍?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/pipeline.py`閿涘牆婀崥鍕▉濞堜絻鐨熼悽?`on_progress(stage_name, current, total)`閿?
  - `tests/unit/test_pipeline_progress.py`閿涘牊鏌婃晶鐑囩窗妤犲矁鐦夐崶鐐剁殶鐞氼偅顒滅涵顔跨殶閻㈩煉绱?
- **鐎圭偟骞囩憰浣哄仯**閿?
  - 閸ョ偠鐨熺粵鎯ф倳閿涙瓪on_progress(stage_name: str, current: int, total: int)`
  - `on_progress` 娑?`None` 閺冭泛鐣崗銊ょ瑝瑜板崬鎼烽悳鐗堟箒鐞涘奔璐?
  - 閸氬嫰妯佸▓闈涙躬婢跺嫮鎮婂В蹇庨嚋 batch 閹存牕鐣幋鎰鐟欙箑褰傞崶鐐剁殶
- **妤犲本鏁归弽鍥у櫙**閿涙瓍ipeline 鏉╂劘顢戦弮鏈电炊閸?mock 閸ョ偠鐨熼敍灞炬焽鐟封偓閸氬嫰妯佸▓闈涙綆鐞氼偉鐨熼悽銊ょ瑬閸欏倹鏆熷锝団€橀妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_pipeline_progress.py`閵?

---

## 闂冭埖顔?G閿涙艾褰茬憴鍡楀缁狅紕鎮婇獮鍐插酱 Dashboard閿涘牏娲伴弽鍥风窗閸忣參銆夐棃銏犵暚閺佹潙褰茬憴鍡楀缁狅紕鎮婇敍?

### G1閿涙ashboard 閸╄櫣顢呴弸鑸电€稉搴ｉ兇缂佺喐鈧槒顫嶆い?
- **閻╊喗鐖?*閿涙碍鎯屽?Streamlit 婢舵岸銆夐棃銏犵安閻劍顢嬮弸璁圭礉鐎圭偟骞囩化鑽ょ埠閹槒顫嶆い鐢告桨閿涘牆鐫嶇粈铏圭矋娴犲爼鍘ょ純顔荤瑢閺佺増宓佺紒鐔活吀閿涘鈧?
- **閸撳秶鐤嗘笟婵婄**閿涙1-F2閿涘湵race 閸╄櫣顢呯拋鐐煢閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/dashboard/app.py`閿涘牓鍣搁崘娆欑窗婢舵岸銆夐棃銏狀嚤閼割亝鐏﹂弸鍕剁礆
  - `src/observability/dashboard/pages/overview.py`閿涘牊鏌婃晶鐑囩窗缁崵绮洪幀鏄忣潔妞ょ敻娼伴敍?
  - `src/observability/dashboard/services/config_service.py`閿涘牊鏌婃晶鐑囩窗闁板秶鐤嗙拠璇插絿閺堝秴濮熼敍?
  - `scripts/start_dashboard.py`閿涘牊鏌婃晶鐑囩窗Dashboard 閸氼垰濮╅懘姘拱閿?
- **鐎圭偟骞囩憰浣哄仯**閿?
  - `app.py` 娴ｈ法鏁?`st.navigation()` 濞夈劌鍞介崗顓濋嚋妞ょ敻娼伴敍鍫熸弓鐎瑰本鍨氶惃鍕€夐棃銏℃▔缁€鍝勫窗娴ｅ秵褰佺粈鐚寸礆
  - Overview 妞ょ敻娼伴敍姘愁嚢閸?`Settings` 鐏炴洜銇氱紒鍕閸楋紕澧栭敍宀冪殶閻?`ChromaStore.get_collection_stats()` 鐏炴洜銇氶弫鐗堝祦缂佺喕顓?
  - `ConfigService`閿涙艾鐨濈憗?Settings 鐠囪褰囬敍灞剧壐瀵繐瀵茬紒鍕闁板秶鐤嗘穱鈩冧紖
- **妤犲本鏁归弽鍥у櫙**閿涙瓪streamlit run src/observability/dashboard/app.py` 閸欘垰鎯庨崝顭掔礉閹槒顫嶆い闈涚潔缁€鍝勭秼閸撳秹鍘ょ純顔讳繆閹垬鈧?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊ㄧ箥鐞?`python scripts/start_dashboard.py` 楠炲爼鐛欑拠渚€銆夐棃銏¤閺屾挶鈧?

### G2閿涙ocumentManager 鐎圭偟骞?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`src/ingestion/document_manager.py`閿涙俺娉曠€涙ê鍋嶉惃鍕瀮濡楋絿鏁撻崨钘夋噯閺堢喓顓搁悶鍡礄list/delete/stats閿涘鈧?
- **閸撳秶鐤嗘笟婵婄**閿涙5閿涘湧ipeline + 閸氬嫬鐡ㄩ崒銊δ侀崸妤€鍑＄亸杈╁崕閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/ingestion/document_manager.py`閿涘牊鏌婃晶鐑囩礆
  - `src/libs/vector_store/chroma_store.py`閿涘牆顤冨鐚寸窗濞ｈ濮?`delete_by_metadata`閿?
  - `src/ingestion/storage/bm25_indexer.py`閿涘牆顤冨鐚寸窗濞ｈ濮?`remove_document`閿?
  - `src/libs/loader/file_integrity.py`閿涘牆顤冨鐚寸窗濞ｈ濮?`remove_record` + `list_processed`閿?
  - `tests/unit/test_document_manager.py`閿涘牊鏌婃晶鐑囩礆
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `DocumentManager.__init__(chroma_store, bm25_indexer, image_storage, file_integrity)`
  - `DocumentManager.list_documents(collection?) -> List[DocumentInfo]`
  - `DocumentManager.get_document_detail(doc_id) -> DocumentDetail`
  - `DocumentManager.delete_document(source_path, collection) -> DeleteResult`
  - `DocumentManager.get_collection_stats(collection?) -> CollectionStats`
- **妤犲本鏁归弽鍥у櫙**閿?
  - `list_documents` 鏉╂柨娲栧鍙夋啔閸忋儲鏋冨锝呭灙鐞涱煉绱檚ource閵嗕恭hunk 閺佽埇鈧礁娴橀悧鍥ㄦ殶閿?
  - `delete_document` 閸楀繗鐨熼崚鐘绘珟 Chroma + BM25 + ImageStorage + FileIntegrity 閸ユ稐閲滅€涙ê鍋?
  - 閸掔娀娅庨崥搴″晙濞?list 娑撳秴瀵橀崥顐㈠嚒閸掔娀娅庨弬鍥ㄣ€?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_document_manager.py`閵?

### G3閿涙碍鏆熼幑顔界セ鐟欏牆娅掓い鐢告桨
- **閻╊喗鐖?*閿涙艾鐤勯悳?Dashboard 閺佺増宓佸ù蹇氼潔閸ｃ劑銆夐棃顫礄閺屻儳婀呴弬鍥ㄣ€傞崚妤勩€冮妴涓唄unk 鐠囷附鍎忛妴浣告禈閻楀洭顣╃憴鍫礆閵?
- **閸撳秶鐤嗘笟婵婄**閿涙1閿涘湒ashboard 閺嬭埖鐎敍澶堚偓涓?閿涘湒ocumentManager閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/dashboard/pages/data_browser.py`閿涘牊鏌婃晶鐑囩礆
  - `src/observability/dashboard/services/data_service.py`閿涘牊鏌婃晶鐑囩窗鐏忎浇顥?ChromaStore/ImageStorage 鐠囪褰囬敍?
- **鐎圭偟骞囩憰浣哄仯**閿?
  - 閺傚洦銆傞崚妤勩€冪憴鍡楁禈閿涙艾鐫嶇粈?source_path閵嗕線娉﹂崥鍫涒偓涔unk 閺佽埇鈧焦鎲氶崗銉︽闂傝揪绱遍弨顖涘瘮闂嗗棗鎮庣粵娑⑩偓?
  - Chunk 鐠囷附鍎忕憴鍡楁禈閿涙氨鍋ｉ崙缁樻瀮濡楋絽鐫嶅鈧幍鈧張?chunk閿涘本妯夌粈鍝勫敶鐎圭櫢绱欓崣顖涘閸欑媴绱氶妴涔礶tadata 鐎涙顔岄妴浣稿彠閼辨柨娴橀悧?
  - `DataService`閿涙艾鐨濈憗?`ChromaStore.get_by_metadata()` 閸?`ImageStorage.list_images()` 鐠嬪啰鏁?
- **妤犲本鏁归弽鍥у櫙**閿涙艾褰查崷?Dashboard 娑擃厽绁荤憴鍫濆嚒閹藉嫬鍙嗛惃鍕瀮濡楋絽鎷?chunk 鐠囷附鍎忛妴?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊╃崣鐠囦緤绱欓崗?ingest 閺嶈渹绶ラ弫鐗堝祦閿涘苯鍟€閸?Dashboard 濞村繗顫嶉敍澶堚偓?

### G4閿涙ngestion 缁狅紕鎮婃い鐢告桨
- **閻╊喗鐖?*閿涙艾鐤勯悳?Dashboard Ingestion 缁狅紕鎮婃い鐢告桨閿涘牊鏋冩禒鏈电瑐娴肩姾袝閸欐垶鎲氶崣鏍モ偓浣界箻鎼达箑鐫嶇粈鎭掆偓浣规瀮濡楋絽鍨归梽銈忕礆閵?
- **閸撳秶鐤嗘笟婵婄**閿涙2閿涘湒ocumentManager閿涘鈧笩3閿涘湒ataService閿涘鈧笚5閿涘潵n_progress 閸ョ偠鐨熼敍?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/dashboard/pages/ingestion_manager.py`閿涘牊鏌婃晶鐑囩礆
- **鐎圭偟骞囩憰浣哄仯**閿?
  - 閺傚洣娆㈡稉濠佺炊閿涙瓪st.file_uploader` 闁瀚ㄩ弬鍥︽ + 闂嗗棗鎮庨柅澶嬪
  - 閹藉嫬褰囩憴锕€褰傞敍姘崇殶閻?`IngestionPipeline.run(on_progress=...)` + `st.progress()` 鐎圭偞妞傛潻娑樺
  - 閺傚洦銆傞崚鐘绘珟閿涙艾婀弬鍥ㄣ€傞崚妤勩€冩稉顓熷絹娓氭稑鍨归梽銈嗗瘻闁筋噯绱濈拫鍐暏 `DocumentManager.delete_document()`
- **妤犲本鏁归弽鍥у櫙**閿涙艾褰查崷?Dashboard 娑擃厺绗傛导鐘虫瀮娴犳儼袝閸欐垶鎲氶崣鏍モ偓浣烘箙閸掓澘鐤勯弮鎯扮箻鎼达附娼妴浣稿灩闂勩倕鍑￠張澶嬫瀮濡楋絻鈧?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊╃崣鐠囦緤绱欐稉濠佺炊 PDF 閳?鐟欏倸鐧傛潻娑樺 閳?閸掔娀娅?閳?绾喛顓诲鑼╅梽銈忕礆閵?

### G5閿涙ngestion 鏉╁€熼嚋妞ょ敻娼?
- **閻╊喗鐖?*閿涙艾鐤勯悳?Dashboard Ingestion 鏉╁€熼嚋妞ょ敻娼伴敍鍫熸啔閸欐牕宸婚崣鎻掑灙鐞涖劊鈧線妯佸▓浣冣偓妤佹閻庢垵绔烽崶鎾呯礆閵?
- **閸撳秶鐤嗘笟婵婄**閿涙4閿涘湜ngestion 閹垫挾鍋ｉ敍澶堚偓涓?閿涘湒ashboard 閺嬭埖鐎敍?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/dashboard/pages/ingestion_traces.py`閿涘牊鏌婃晶鐑囩礆
  - `src/observability/dashboard/services/trace_service.py`閿涘牊鏌婃晶鐑囩窗鐟欙絾鐎?traces.jsonl閿?
- **鐎圭偟骞囩憰浣哄仯**閿?
  - 閸樺棗褰堕崚妤勩€冮敍姘瘻閺冨爼妫块崐鎺戠碍鐏炴洜銇?`trace_type == "ingestion"` 鐠佹澘缍?
  - 鐠囷附鍎忔い纰夌窗濡亜鎮滈弶鈥宠埌閸ユ儳鐫嶇粈?load/split/transform/embed/upsert 閼版妞傞崚鍡楃
  - `TraceService`閿涙俺顕伴崣?`logs/traces.jsonl`閿涘矁袙閺嬫劒璐?Trace 鐎电钖勯崚妤勩€?
- **妤犲本鏁归弽鍥у櫙**閿涙碍澧界悰?ingest 閸氬函绱滵ashboard 閺勫墽銇氱€电懓绨查惃鍕嫹闊亣顔囪ぐ鏇氱瑢閼版妞傞悗鎴濈閸ヤ勘鈧?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊╃崣鐠囦緤绱欓崗?ingest 閳?閹垫挸绱?Dashboard 閳?閺屻儳婀呮潻鍊熼嚋閿涘鈧?

### G6閿涙瓐uery 鏉╁€熼嚋妞ょ敻娼?
- **閻╊喗鐖?*閿涙艾鐤勯悳?Dashboard Query 鏉╁€熼嚋妞ょ敻娼伴敍鍫熺叀鐠囥垹宸婚崣灞傗偓涓廵nse/Sparse 鐎佃鐦妴涓積rank 閸欐ê瀵查敍澶堚偓?
- **閸撳秶鐤嗘笟婵婄**閿涙3閿涘湨uery 閹垫挾鍋ｉ敍澶堚偓涓?閿涘湒ashboard 閺嬭埖鐎敍澶堚偓涓?閿涘湵raceService 瀹告彃鐤勯悳甯礆
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/dashboard/pages/query_traces.py`閿涘牊鏌婃晶鐑囩礆
- **鐎圭偟骞囩憰浣哄仯**閿?
  - 閸樺棗褰堕崚妤勩€冮敍姘瘻閺冨爼妫块崐鎺戠碍鐏炴洜銇?`trace_type == "query"` 鐠佹澘缍嶉敍灞炬暜閹镐焦瀵?Query 閸忔娊鏁拠宥嗘偝缁?
  - 鐠囷附鍎忔い纰夌窗閼版妞傞悗鎴濈閸?+ Dense vs Sparse 楠炶泛鍨€佃鐦?+ Rerank 閸撳秴鎮楅幒鎺戞倳閸欐ê瀵?
- **妤犲本鏁归弽鍥у櫙**閿涙碍澧界悰?query 閸氬函绱滵ashboard 閺勫墽銇氶弻銉嚄鏉╁€熼嚋鐠囷附鍎忔稉搴℃倗闂冭埖顔岀€佃鐦妴?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊╃崣鐠囦緤绱欓崗?query 閳?閹垫挸绱?Dashboard 閳?閺屻儳婀呮潻鍊熼嚋閿涘鈧?

---

## 闂冭埖顔?H閿涙俺鐦庢导棰佺秼缁紮绱欓惄顔界垼閿涙艾褰查幓鎺撳珗鐠囧嫪鍙?+ 閸欘垶鍣洪崠鏍ф礀瑜版帪绱?

### H1閿涙瓓agasEvaluator 鐎圭偟骞?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`ragas_evaluator.py`閿涙艾鐨濈憗?Ragas 濡楀棙鐏﹂敍灞界杽閻?`BaseEvaluator` 閹恒儱褰涢妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/evaluation/ragas_evaluator.py`閿涘牊鏌婃晶鐑囩礆
  - `src/libs/evaluator/evaluator_factory.py`閿涘牊鏁為崘?ragas provider閿?
  - `tests/unit/test_ragas_evaluator.py`閿涘牊鏌婃晶鐑囩礆
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `RagasEvaluator(BaseEvaluator)`閿涙艾鐤勯悳?`evaluate()` 閺傝纭?
  - 閺€顖涘瘮閹稿洦鐖ｉ敍娆禷ithfulness, Answer Relevancy, Context Precision
  - 娴兼﹢娉ら梽宥囬獓閿涙瓓agas 閺堫亜鐣ㄧ憗鍛閹舵稑鍤弰搴ｂ€橀惃?`ImportError` 閹绘劗銇?
- **妤犲本鏁归弽鍥у櫙**閿涙ock LLM 閻滎垰顣ㄦ稉瀣剁礉`evaluate()` 鏉╂柨娲栭崠鍛儓 faithfulness/answer_relevancy 閻?metrics 鐎涙鍚€閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_ragas_evaluator.py`閵?

### H2閿涙ompositeEvaluator 鐎圭偟骞?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`composite_evaluator.py`閿涙氨绮嶉崥鍫濐樋娑?Evaluator 楠炴儼顢戦幍褑顢戦敍灞剧湽閹崵绮ㄩ弸婧库偓?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/evaluation/composite_evaluator.py`閿涘牊鏌婃晶鐑囩礆
  - `tests/unit/test_composite_evaluator.py`閿涘牊鏌婃晶鐑囩礆
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `CompositeEvaluator.__init__(evaluators: List[BaseEvaluator])`
  - `CompositeEvaluator.evaluate() -> dict`閿涙艾鑻熺悰灞惧⒔鐞涘本澧嶉張?evaluator閿涘苯鎮庨獮?metrics
  - 闁板秶鐤嗘す鍗炲З閿涙瓪evaluation.backends: [ragas, custom]` 閳?瀹搞儱宸堕懛顏勫З缂佸嫬鎮?
- **妤犲本鏁归弽鍥у櫙**閿涙岸鍘ょ純顔昏⒈娑?evaluator 閺冭绱濇潻鏂挎礀閻?metrics 閸栧懎鎯堟稉銈堚偓鍛畱閹稿洦鐖ｉ妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/unit/test_composite_evaluator.py`閵?

### H3閿涙valRunner + Golden Test Set
- **閻╊喗鐖?*閿涙艾鐤勯悳?`eval_runner.py`閿涙俺顕伴崣?`tests/fixtures/golden_test_set.json`閿涘矁绐?retrieval 楠炴湹楠囬崙?metrics閵?
- **閸撳秶鐤嗘笟婵婄**閿涙5閿涘湚ybridSearch閿涘鈧笭1-H2閿涘牐鐦庢导鏉挎珤閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/evaluation/eval_runner.py`閿涘牊鏌婃晶鐑囩礆
  - `tests/fixtures/golden_test_set.json`閿涘牊鏌婃晶鐑囩窗姒涘嫰鍣惧ù瀣槸闂嗗棴绱?
  - `scripts/evaluate.py`閿涘牊鏌婃晶鐑囩窗鐠囧嫪鍙婃潻鎰攽閼存碍婀伴敍?
- **鐎圭偟骞囩猾?閸戣姤鏆?*閿?
  - `EvalRunner.__init__(settings, hybrid_search, evaluator)`
  - `EvalRunner.run(test_set_path) -> EvalReport`閿涙俺绻嶇悰宀冪槑娴兼澘鑻熸潻鏂挎礀閹躲儱鎲?
  - `EvalReport`閿涙艾瀵橀崥?hit_rate, mrr, 閸?query 缂佹挻鐏夌拠锔藉剰
- **golden_test_set.json 閺嶇厧绱?*閿?
  ```json
  {
    "test_cases": [
      {
        "query": "婵″倷缍嶉柊宥囩枂 Azure OpenAI閿?,
        "expected_chunk_ids": ["chunk_abc_001", "chunk_abc_002"],
        "expected_sources": ["config_guide.pdf"]
      }
    ]
  }
  ```
- **妤犲本鏁归弽鍥у櫙**閿涙瓪python scripts/evaluate.py` 閸欘垵绻嶇悰宀嬬礉鏉堟挸鍤?metrics閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/integration/test_hybrid_search.py` 閹?`python scripts/evaluate.py`閵?

### H4閿涙俺鐦庢导浼存桨閺夊潡銆夐棃?
- **閻╊喗鐖?*閿涙艾鐤勯悳?Dashboard 鐠囧嫪鍙婇棃銏℃緲妞ょ敻娼伴敍鍫ｇ箥鐞涘矁鐦庢导鑸偓浣圭叀閻瀵氶弽鍥モ偓浣稿坊閸欐彃顕В鏃撶礆閵?
- **閸撳秶鐤嗘笟婵婄**閿涙3閿涘湕valRunner閿涘鈧笩1閿涘湒ashboard 閺嬭埖鐎敍?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `src/observability/dashboard/pages/evaluation_panel.py`閿涘牆鐤勯悳甯窗閺囨寧宕查崡鐘辩秴閹绘劗銇氶敍?
- **鐎圭偟骞囩憰浣哄仯**閿?
  - 闁瀚ㄧ拠鍕強閸氬海顏稉?golden test set
  - 閻愮懓鍤潻鎰攽閿涘苯鐫嶇粈楦跨槑娴兼壆绮ㄩ弸婊愮礄hit_rate閵嗕沟rr閵嗕礁鎮?query 閺勫海绮忛敍?
  - 閸欘垶鈧绱伴崢鍡楀蕉鐠囧嫪鍙婄紒鎾寸亯鐎佃鐦崶?
- **妤犲本鏁归弽鍥у櫙**閿涙艾褰查崷?Dashboard 娑擃叀绻嶇悰宀冪槑娴兼澘鑻熼弻銉ф箙閹稿洦鐖ｉ妴?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊╃崣鐠囦降鈧?

### H5閿涙瓓ecall 閸ョ偛缍婂ù瀣槸閿涘湕2E閿?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`tests/e2e/test_recall.py`閿涙艾鐔€娴?golden set 閸嬫碍娓剁亸蹇撳将閸ョ偤妲囬崐纭风礄娓氬顩?hit@k閿涘鈧?
- **閸撳秶鐤嗘笟婵婄**閿涙3閿涘湕valRunner + golden_test_set閿?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `tests/e2e/test_recall.py`閿涘牊鏌婃晶鐑囩礆
  - `tests/fixtures/golden_test_set.json`閿涘牐藟姒绘劘瀚㈤獮鍙夋蒋閿?
- **妤犲本鏁归弽鍥у櫙**閿涙it@k 鏉堟儳鍩岄梼鍫濃偓纭风礄闂冨牆鈧厧鍟撳璇叉躬濞村鐦柌宀嬬礉娓氬じ绨崶鐐茬秺閿涘鈧?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/e2e/test_recall.py`閵?

---

## 闂冭埖顔?I閿涙氨顏崚鎵伂妤犲本鏁规稉搴㈡瀮濡楋絾鏁归崣锝忕礄閻╊喗鐖ｉ敍姘磻缁犲崬宓嗛悽銊ф畱"閸欘垰顦查悳?瀹搞儳鈻奸敍?

### I1閿涙2E閿涙瓉CP Client 娓氀嗙殶閻劍膩閹?
- **閻╊喗鐖?*閿涙艾鐤勯悳?`tests/e2e/test_mcp_client.py`閿涙矮浜掔€涙劘绻樼粙瀣儙閸?server閿涘本膩閹?tools/list + tools/call閵?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `tests/e2e/test_mcp_client.py`
- **妤犲本鏁归弽鍥у櫙**閿涙艾鐣弫纾嬭泲闁?query_knowledge_hub 楠炴儼绻戦崶?citations閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/e2e/test_mcp_client.py`閵?

### I2閿涙2E閿涙ashboard 閸愭帞鍎ù瀣槸
- **閻╊喗鐖?*閿涙岸鐛欑拠?Dashboard 閸氬嫰銆夐棃銏犳躬閺堝鏆熼幑顔芥閸欘垱顒滅敮鍛婅閺屾挶鈧焦妫?Python 瀵倸鐖堕妴?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `tests/e2e/test_dashboard_smoke.py`閿涘牊鏌婃晶鐑囩礆
- **鐎圭偟骞囩憰浣哄仯**閿?
  - 娴ｈ法鏁?Streamlit 閻?`AppTest` 濡楀棙鐏︽潻娑滎攽閼奉亜濮╅崠鏍у晪閻戠喐绁寸拠?
  - 妤犲矁鐦?6 娑擃亪銆夐棃銏犳綆閸欘垰濮炴潪濮愨偓浣风瑝閹舵稑绱撶敮?
- **妤犲本鏁归弽鍥у櫙**閿涙碍澧嶉張澶愩€夐棃銏犲晪閻戠喐绁寸拠鏇⑩偓姘崇箖閵?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q tests/e2e/test_dashboard_smoke.py`閵?

### I3閿涙艾鐣崰?README閿涘牐绻嶇悰宀冾嚛閺?+ 濞村鐦拠瀛樻 + MCP 闁板秶鐤?+ Dashboard 娴ｈ法鏁ら敍?
- **閻╊喗鐖?*閿涙俺顔€閺傛壆鏁ら幋鐤厴閸?10 閸掑棝鎸撻崘鍛扮獓闁?ingest + query + dashboard + tests閿涘苯鑻熼懗钘夋躬 Copilot/Claude 娑擃厺濞囬悽銊ｂ偓?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `README.md`
- **妤犲本鏁归弽鍥у櫙**閿涙瓓EADME 閸栧懎鎯堟禒銉ょ瑓缁旂姾濡敍?
  - **韫囶偊鈧喎绱戞慨?*閿涙艾鐣ㄧ憗鍛贩鐠ф牓鈧線鍘ょ純?API Key閵嗕浇绻嶇悰宀勵浕濞嗏剝鎲氶崣?
  - **闁板秶鐤嗙拠瀛樻**閿涙瓪settings.yaml` 閸氬嫬鐡у▓闈涙儓娑?
  - **MCP 闁板秶鐤嗙粈杞扮伐**閿涙itHub Copilot `mcp.json` 娑?Claude Desktop `claude_desktop_config.json`
  - **Dashboard 娴ｈ法鏁ら幐鍥у础**閿涙艾鎯庨崝銊ユ嚒娴犮們鈧礁鎮囨い鐢告桨閸旂喕鍏樼拠瀛樻閵嗕焦鍩呴崶鍓с仛娓?
  - **鏉╂劘顢戝ù瀣槸**閿涙艾宕熼崗鍐╃ゴ鐠囨洏鈧線娉﹂幋鎰ゴ鐠囨洏鈧笒2E 濞村鐦崨鎴掓姢
  - **鐢瓕顫嗛梻顕€顣?*閿涙PI Key 闁板秶鐤嗛妴浣风贩鐠ф牕鐣ㄧ憗鍛偓浣界箾閹恒儵妫舵０妯诲笓閺?
- **濞村鐦弬瑙勭《**閿涙碍瀵?README 閹靛濮╃挧棰佺闁秲鈧?

### I4閿涙碍绔婚悶鍡樺复閸欙絼绔撮懛瀛樷偓褝绱欐總鎴犲濞村鐦悰銉╃秷閿?
- **閻╊喗鐖?*閿涙矮璐熼崗鎶芥暛閹跺€熻杽閿涘湸ectorStore / Reranker / Evaluator / DocumentManager閿涘藟姒绘劕顨栫痪锔界ゴ鐠囨洏鈧?
- **娣囶喗鏁奸弬鍥︽**閿?
  - `tests/unit/test_vector_store_contract.py`閿涘牐藟姒?delete_by_metadata 鏉堝湱鏅敍?
  - `tests/unit/test_reranker_factory.py`閿涘牐藟姒绘劘绔熼悾宀嬬礆
  - `tests/unit/test_custom_evaluator.py`閿涘牐藟姒绘劘绔熼悾宀嬬礆
- **妤犲本鏁归弽鍥у櫙**閿涙瓪pytest -q` 閸忋劎璞㈤敍灞肩瑬 contract tests 鐟曞棛娲婃稉鏄忣洣鏉堟挸鍙嗘潏鎾冲毉瑜般垻濮搁妴?
- **濞村鐦弬瑙勭《**閿涙瓪pytest -q`閵?

### I5閿涙艾鍙忛柧鎹愮熅 E2E 妤犲本鏁?
- **閻╊喗鐖?*閿涙碍澧界悰灞界暚閺佸娈戠粩顖氬煂缁旑垶鐛欓弨鑸电ウ缁嬪绱癷ngest 閳?query via MCP 閳?Dashboard 閸欘垵顫嬮崠?閳?evaluate閵?
- **娣囶喗鏁奸弬鍥︽**閿涙碍妫ら弬鐗堟瀮娴犺绱濇灞炬暪瀹稿弶婀侀崝鐔诲厴
- **妤犲本鏁归弽鍥у櫙**閿?
  - `python scripts/ingest.py --path tests/fixtures/sample_documents/ --collection test` 閹存劕濮?
  - `python scripts/query.py --query "濞村鐦弻銉嚄" --verbose` 鏉╂柨娲栫紒鎾寸亯
  - Dashboard 閸欘垰鐫嶇粈鐑樻啔閸欐牔绗岄弻銉嚄鏉╁€熼嚋
  - `python scripts/evaluate.py` 鏉堟挸鍤拠鍕強閹稿洦鐖?
- **濞村鐦弬瑙勭《**閿涙碍澧滈崝銊ュ弿闁炬崘鐭剧挧浼粹偓?+ `pytest -q` 閸忋劑鍣哄ù瀣槸閵?

---

### 娴溿倓绮柌宀€鈻肩喊鎴礄瀵ら缚顔呴敍?

- **M1閿涘牆鐣幋鎰版▉濞?A+B閿?*閿涙艾浼愮粙瀣讲濞?+ 閸欘垱褰冮幏鏃€濞婄挒鈥崇湴鐏忚京鍗庨敍灞芥倵缂侇厼鐤勯悳鏉垮讲楠炴儼顢戦幒銊ㄧ箻閵?
- **M2閿涘牆鐣幋鎰版▉濞?C閿?*閿涙氨顬囩痪鎸庢啔閸欐牠鎽肩捄顖氬讲閻㈩煉绱濋懗鑺ョ€鐑樻拱閸︽壆鍌ㄥ鏇樷偓?
- **M3閿涘牆鐣幋鎰版▉濞?D+E閿?*閿涙艾婀痪鎸庣叀鐠?+ MCP tools 閸欘垳鏁ら敍灞藉讲閸?Copilot/Claude 娑擃叀鐨熼悽銊ｂ偓?
- **M4閿涘牆鐣幋鎰版▉濞?F閿?*閿涙ngestion + Query 閸欏矂鎽肩捄顖氬讲鏉╁€熼嚋閿涘瓰SON Lines 閹镐椒绠欓崠鏍モ偓?
- **M5閿涘牆鐣幋鎰版▉濞?G閿?*閿涙艾鍙氭い鐢告桨閸欘垵顫嬮崠鏍吀閻炲棗閽╅崣鏉挎皑缂侇亷绱欑拠鍕強闂堛垺婢樻稉鍝勫窗娴ｅ稄绱氶敍灞炬殶閹诡喖褰插ù蹇氼潔閵嗕礁褰茬粻锛勬倞閵嗕線鎽肩捄顖氬讲鏉╁€熼嚋閵?
- **M6閿涘牆鐣幋鎰版▉濞?H+I閿?*閿涙俺鐦庢导棰佺秼缁鐣弫?+ E2E 妤犲本鏁归柅姘崇箖 + 閺傚洦銆傜€瑰苯鏉介敍灞借埌閹?闂堛垼鐦?閺佹瑥顒?濠曟梻銇?閸欘垰顦查悳浼淬€嶉惄顔衡偓?



