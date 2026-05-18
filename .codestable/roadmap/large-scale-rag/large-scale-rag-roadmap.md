---
doc_type: roadmap
slug: large-scale-rag
status: active
created: 2026-05-15
last_reviewed: 2026-05-15
tags: [rag, qdrant, retrieval, evaluation, resume]
related_requirements: []
related_architecture: [ARCHITECTURE]
---

# 大规模 RAG 后端升级

## 1. 背景

当前项目已经具备基础 RAG 能力：文档加载、分块、Embedding、FAISS/InMemory 向量库、索引管理、API 查询和学习工作流检索节点。问题在于它仍偏教学 demo：默认是本地 FAISS dense-only 检索，没有服务化向量库、没有混合召回、没有 rerank，也没有离线评测集支撑“召回率提升”的简历数字。

本 roadmap 的目标是把 RAG 后端升级成可复习、可解释、可量化的工程模块：能讲清楚每个算法术语，能用公式解释指标，能用 BEIR/SciFact 等公开数据集跑出 Recall@K/MRR/nDCG 基线与优化结果。

## 2. 范围与明确不做

### 本 roadmap 覆盖
- 离线检索评测闭环：BEIR 格式加载、Recall@K、Precision@K、MRR@K、nDCG@K。
- 向量库后端升级：在现有 FAISS/InMemory 之外接入 Qdrant。
- 混合召回方案：dense retrieval + sparse/BM25 retrieval + RRF 融合。
- Rerank 方案：先召回候选，再用更强排序模型重排 top K。
- 面向复习和简历的完整文档：术语、公式、接口、数据集、实验口径。

### 明确不做
- 不直接虚构 Recall/MRR 提升数字；所有 X% -> Y% 必须由评测脚本跑出。
- 不在第一阶段引入线上大规模分布式部署、K8s、分片压测；这些属于后续生产化 roadmap。
- 不把 Qdrant 替换成唯一后端；FAISS 保留为 baseline 和本地 fallback。
- 不把生成答案质量评估混入检索评测；本阶段只评估检索层。

## 3. 模块拆分（概设）

```
large-scale-rag
├── retrieval-evaluation：离线数据集和指标计算
├── vector-store-backends：FAISS/Qdrant 后端适配
├── hybrid-retrieval：dense+sparse 多路召回与 RRF 融合
├── reranking：候选集重排
└── rag-docs：复习与简历文档
```

### retrieval-evaluation · 检索评测
- **职责**：加载 BEIR 格式数据，计算 Recall@K、Precision@K、MRR@K、nDCG@K，输出可比较的实验报告。
- **承载的子 feature**：rag-evaluation-baseline
- **触碰的现有代码 / 模块**：新增 `backend/rag/evaluation.py`，新增 `backend/tests/rag/test_evaluation.py`。

### vector-store-backends · 向量库后端
- **职责**：在 `create_vector_store` / `load_vector_store` / `save_vector_store` 的现有抽象内扩展 Qdrant，保留 FAISS baseline。
- **承载的子 feature**：qdrant-vector-store
- **触碰的现有代码 / 模块**：`backend/rag/vector_stores.py`、`backend/config/setting.py`、`backend/pyproject.toml`。

### hybrid-retrieval · 混合召回
- **职责**：定义多路检索器的 RRF 融合入口，为 dense、sparse/BM25 的统一编排提供组合层。
- **承载的子 feature**：hybrid-rrf-retrieval
- **触碰的现有代码 / 模块**：`backend/rag/retrievers.py`、`backend/api/routers/rag.py`、Qdrant collection schema。

### reranking · 重排
- **职责**：对候选文档执行可插拔 reranker 排序，提升 top K 精度；当前提供词项覆盖率基线，后续可替换为 cross-encoder。
- **承载的子 feature**：retrieval-reranker
- **触碰的现有代码 / 模块**：新增 rerank 模块，接入 API 查询参数。

### rag-docs · 复习与简历文档
- **职责**：提供完整术语解释、公式、数据集选择、实验流程、简历表达。
- **承载的子 feature**：rag-study-guide
- **触碰的现有代码 / 模块**：`backend/docs/dev/large-scale-rag.md`。

## 4. 模块间接口契约 / 共享协议（架构层详设）

### 4.1 评测数据协议

**方向**：BEIR dataset -> `backend.rag.evaluation`

**形式**：文件协议

**契约**：

```text
{dataset}/corpus.jsonl
  每行 JSON: { "_id": str, "title": str, "text": str }

{dataset}/queries.jsonl
  每行 JSON: { "_id": str, "text": str }

{dataset}/qrels/{split}.tsv
  表头: query-id<TAB>corpus-id<TAB>score
  score > 0 表示相关
```

**约束**：
- `Document.metadata["doc_id"]` 必须等于 corpus `_id`。
- 评测默认 split 为 `test`。
- 没有 qrels 的自建数据不能声称有公开 benchmark 指标。

### 4.2 检索评测接口

**方向**：评测模块 -> 任意 retriever
**形式**：函数调用

**契约**：

```python
class QueryJudgement:
    query_id: str
    query: str
    relevant_doc_ids: set[str]

def evaluate_retriever(
    retriever: RetrieverProtocol,
    judgements: Iterable[QueryJudgement],
    k: int = 5,
    doc_id_metadata_key: str = "doc_id",
) -> EvaluationReport
```

**约束**：
- retriever 必须实现 `invoke(query: str) -> list[Document]`。
- 每个返回文档必须在 metadata 中提供 `doc_id` 或 `source`。
- 指标只评价检索，不评价最终 LLM 回答。

### 4.3 向量库后端接口

**方向**：`IndexManager` -> `vector_stores`
**形式**：函数调用

**契约**：

```python
def create_vector_store(
    documents: list[Document],
    embeddings: Embeddings,
    store_type: str | None = None,
    **kwargs,
) -> VectorStore

def load_vector_store(
    load_path: str | Path,
    embeddings: Embeddings,
    store_type: str | None = None,
    **kwargs,
) -> VectorStore
```

**约束**：
- `store_type="faiss"` 保持本地 baseline。
- `store_type="qdrant"` 使用 `langchain_qdrant.QdrantVectorStore`。
- Qdrant 未安装时必须抛出清晰 ImportError，不能影响 FAISS 路径。
- `collection_name` 可由调用方传入；未传时使用 settings 或索引名。

### 4.4 指标公式协议

**Recall@K**：

```text
Recall@K = |Relevant ∩ Retrieved@K| / |Relevant|
```

**Precision@K**：

```text
Precision@K = |Relevant ∩ Retrieved@K| / K
```

**MRR@K**：

```text
MRR@K = (1 / |Q|) * Σ 1 / rank_i
```

**nDCG@K**：

```text
DCG@K = Σ rel_i / log2(i + 1)
nDCG@K = DCG@K / IDCG@K
```

**RRF**：

```text
score(d) = Σ_i weight_i / (k + rank_i(d))
```

## 5. 子 feature 清单

1. **rag-evaluation-baseline** — 增加 BEIR 数据加载和检索指标计算，作为所有优化的最小闭环。
   - 所属模块：retrieval-evaluation
   - 依赖：无
   - 状态：done
   - 对应 feature：未启动
   - 备注：本轮已实现 `backend/rag/evaluation.py` 和单元测试。

2. **qdrant-vector-store** — 在现有向量库抽象中接入 Qdrant，保留 FAISS baseline。
   - 所属模块：vector-store-backends
   - 依赖：rag-evaluation-baseline
   - 状态：done
   - 对应 feature：未启动
   - 备注：本轮已新增 Qdrant 配置和懒加载接入点。

3. **hybrid-rrf-retrieval** — 支持 dense+sparse 双路召回和 RRF 融合，API 可选择 hybrid 模式。
   - 所属模块：hybrid-retrieval
   - 依赖：qdrant-vector-store
   - 状态：done
   - 对应 feature：未启动
   - 备注：本轮已实现 `create_rrf_retriever` 多路融合；sparse embedding/index schema 仍是后续增强点。

4. **retrieval-reranker** — 对候选文档引入 rerank，输出重排后的 top K。
   - 所属模块：reranking
   - 依赖：hybrid-rrf-retrieval
   - 状态：done
   - 对应 feature：未启动
   - 备注：本轮已实现 `create_rerank_retriever` 和 `TermOverlapReranker`；cross-encoder reranker 仍是后续增强点。

5. **rag-study-guide** — 写完整开发者复习文档，覆盖术语、公式、数据集、实验和简历表达。
   - 所属模块：rag-docs
   - 依赖：rag-evaluation-baseline
   - 状态：done
   - 对应 feature：未启动
   - 备注：本轮写入 `backend/docs/dev/large-scale-rag.md`。

**最小闭环**：第 1 条 `rag-evaluation-baseline` 做完后，可以用 BEIR/SciFact 或本地 BEIR 格式样例跑出 Recall@K/MRR/nDCG，为后续优化建立 baseline。

## 6. 排期思路

先做评测闭环，因为没有 qrels 和指标就无法证明“召回率提高”。第二步接 Qdrant，因为服务化向量库是大规模 RAG 的后端底座。第三步做 hybrid/RRF，因为它直接改善 dense-only 对关键词、术语、编号的召回短板。第四步做 rerank，因为 rerank 更偏 precision/top K 排序优化，需要先有候选召回。文档贯穿全过程，避免最后只剩“用了很多名词”但讲不清公式。

## 7. 观察项

- `ARCHITECTURE.md` 仍是骨架，后续功能验收后应补 `architecture/rag-retrieval.md`。
- 当前 `backend/pyproject.toml` 要求 Python `>=3.14`，生态依赖安装可能受限；如依赖解析失败，应单独评估 Python 版本约束。
- `hybrid-rrf-retrieval` 的组合层已落地；真正 dense+sparse hybrid 还需要明确 sparse embedding 选择和 Qdrant collection schema。
