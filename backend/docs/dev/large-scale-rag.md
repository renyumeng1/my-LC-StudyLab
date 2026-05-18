---
doc_type: dev-guide
slug: large-scale-rag
component: rag
status: current
summary: 大规模 RAG 后端升级的术语、公式、数据集、评测与简历表达指南
tags: [rag, qdrant, retrieval, evaluation, resume]
last_reviewed: 2026-05-15
---

## 概述

本项目的 RAG 后端升级目标不是简单替换向量库，而是建立一条可解释、可复现、可写进简历的检索工程链路：

```text
公开数据集 -> baseline 检索 -> 指标评测 -> Qdrant 后端 -> hybrid/RRF -> rerank -> 指标对比
```

当前已落地：

- `backend/rag/evaluation.py`：BEIR 格式加载、Recall@K、Precision@K、MRR@K、nDCG@K、RRF。
- `backend/rag/vector_stores.py`：在 FAISS/InMemory 之外增加 Qdrant 可选后端。
- `backend/rag/retrievers.py`：RRF 多路融合检索器、两阶段 rerank 检索器。
- `.codestable/roadmap/large-scale-rag/`：拆分后的 feature roadmap。

## 前置依赖

基础依赖来自 `backend/pyproject.toml`。Qdrant 相关依赖为：

```toml
langchain-qdrant>=1.1.0
qdrant-client>=1.17.0
```

FAISS 仍保留为 baseline：

```toml
faiss-cpu>=1.13.2
```

## 快速上手

用 BEIR 格式数据集评测一个 retriever：

```python
from backend.rag.evaluation import load_beir_queries, evaluate_retriever

judgements = load_beir_queries("data/beir/scifact", split="test")
report = evaluate_retriever(retriever, judgements, k=5)

print(report.recall_at_k)
print(report.mrr_at_k)
print(report.ndcg_at_k)
```

用 Qdrant 创建向量库：

```python
from backend.rag.vector_stores import create_vector_store

vector_store = create_vector_store(
    documents=documents,
    embeddings=embeddings,
    store_type="qdrant",
    collection_name="study_lab_docs",
)
```

未启动 Qdrant 服务时，可以用本地 path 模式；设置 `QDRANT_URL=http://localhost:6333` 后会连接服务端。

## 核心概念

### RAG

RAG 是 Retrieval-Augmented Generation，意思是先检索知识库，再把检索结果交给 LLM 生成答案。

```text
query -> retriever -> relevant documents -> prompt -> LLM answer
```

### Embedding

Embedding 把文本映射为向量：

```text
text -> [0.12, -0.43, 0.88, ...]
```

语义相近的文本，向量距离更近。

### Dense Retrieval

Dense Retrieval 使用稠密向量做语义检索，擅长“意思相近但词不完全一样”的查询。

常见相似度是余弦相似度：

```text
cos(q, d) = (q · d) / (||q|| ||d||)
```

其中：

- `q` 是查询向量
- `d` 是文档向量
- `q · d` 是点积
- `||q||` 和 `||d||` 是向量长度

### Sparse Retrieval / BM25

Sparse Retrieval 使用稀疏向量或词项统计，擅长精确关键词、术语、编号。

BM25 公式：

```text
BM25(q, d) = Σ IDF(t) * ((f(t,d) * (k1 + 1)) / (f(t,d) + k1 * (1 - b + b * |d| / avgdl)))
```

其中：

- `t` 是 query 中的词
- `f(t,d)` 是词 t 在文档 d 中出现的次数
- `IDF(t)` 是逆文档频率
- `|d|` 是文档长度
- `avgdl` 是平均文档长度
- `k1` 和 `b` 是调节参数

### Hybrid Retrieval

Hybrid Retrieval 把 dense 和 sparse 合并：

```text
dense: 语义理解
sparse: 精确词匹配
hybrid: 同时利用两者
```

Dense-only 常漏掉编号、专业术语、精确实体。Sparse-only 又不懂同义表达。Hybrid 的价值是提高召回率。

### RRF

RRF 是 Reciprocal Rank Fusion，用排名融合多个检索列表。

```text
score(d) = Σ_i weight_i / (k + rank_i(d))
```

如果一个文档在 dense 和 sparse 的结果里都靠前，它最终分数会更高。Qdrant Query API 支持用 RRF 融合 dense/sparse prefetch 结果。

### Rerank

Rerank 是两阶段检索：

```text
retriever top 50 -> reranker reorder -> final top 5
```

第一阶段追求召回率，第二阶段追求排序质量。Reranker 通常比向量检索慢，但能更细粒度判断 query-document 是否匹配。

当前代码提供 `TermOverlapReranker` 作为无模型依赖的工程基线，它按查询词项覆盖率重排候选文档：

```text
score(q, d) = |terms(q) ∩ terms(d)| / |terms(q)|
```

它不是最终推荐的生产 reranker，但能先把“候选召回 -> 重排 -> top K 截断”的接口闭环跑通。后续可以把 `reranker` 参数替换为 cross-encoder reranker。

## 评测指标

### Recall@K

衡量标准答案里有多少被 top K 找到。

```text
Recall@K = |Relevant ∩ Retrieved@K| / |Relevant|
```

简历里最适合写这个，因为它直接表达“召回率从多少提高到多少”。

### Precision@K

衡量 top K 里有多少是真的相关。

```text
Precision@K = |Relevant ∩ Retrieved@K| / K
```

Recall 更关心不要漏，Precision 更关心不要混入噪声。

### MRR@K

衡量第一个正确结果排得多靠前。

```text
MRR@K = (1 / |Q|) * Σ 1 / rank_i
```

如果第一个正确答案排第 1，单条得分是 1；排第 2，得分是 0.5。

### nDCG@K

衡量相关文档是否排在靠前位置。

```text
DCG@K = Σ rel_i / log2(i + 1)
nDCG@K = DCG@K / IDCG@K
```

二值相关性下，`rel_i` 为 1 表示相关，为 0 表示不相关。

## 开源数据集

优先使用 BEIR。BEIR 是信息检索 benchmark，天然包含：

- `corpus.jsonl`: 文档库
- `queries.jsonl`: 查询集合
- `qrels/{split}.tsv`: 标准答案

推荐顺序：

| 数据集 | 适合原因 |
| --- | --- |
| SciFact | 科学事实检索，规模适中，适合项目 demo |
| NFCorpus | 医学/健康文本，适合知识问答检索 |
| FiQA2018 | 金融问答，适合专业领域查询 |
| HotpotQA | 多跳问答，适合复杂问题 |
| MSMARCO | 工业级数据，规模较大，适合后期压测 |

不要先用自造小数据写简历指标。自造数据可以做 smoke test，但不能支撑“公开 benchmark 提升”。

## 接口参考

### BEIR 加载

```python
load_beir_corpus(dataset_path: str | Path) -> list[Document]
load_beir_queries(dataset_path: str | Path, split: str = "test") -> list[QueryJudgement]
```

### 检索评测

```python
evaluate_retriever(
    retriever,
    judgements,
    k=5,
    doc_id_metadata_key="doc_id",
) -> EvaluationReport
```

### 单项指标

```python
recall_at_k(retrieved_doc_ids, relevant_doc_ids, k)
precision_at_k(retrieved_doc_ids, relevant_doc_ids, k)
reciprocal_rank_at_k(retrieved_doc_ids, relevant_doc_ids, k)
ndcg_at_k(retrieved_doc_ids, relevant_doc_ids, k)
```

### RRF

```python
reciprocal_rank_fusion(
    ranked_lists=[dense_doc_ids, sparse_doc_ids],
    k=60,
    weights=[1.0, 1.0],
)
```

### 检索器编排

```python
from backend.rag.retrievers import create_rerank_retriever, create_rrf_retriever

hybrid_retriever = create_rrf_retriever(
    retrievers=[dense_retriever, sparse_retriever],
    weights=[0.7, 0.3],
    k=10,
)

rerank_retriever = create_rerank_retriever(
    retriever=hybrid_retriever,
    k=5,
    candidate_k=20,
)
```

`create_rrf_retriever` 现在已经可用；真正的 dense+sparse hybrid 还需要先创建 sparse retriever。当前项目已提供组合层，但还没有落地 sparse vector index schema。

## 实验流程

1. 下载 BEIR/SciFact。
2. 用 `load_beir_corpus` 转成 Document。
3. 用 FAISS 建 baseline index。
4. 用 `evaluate_retriever(..., k=5)` 记录 `Recall@5 / MRR@5 / nDCG@5`。
5. 用 Qdrant 建同样 corpus。
6. 用 `create_rrf_retriever` 组合 dense retriever 和后续 sparse retriever。
7. 用 `create_rerank_retriever` 对候选结果重排。
8. 再跑同一批 queries，对比指标。

实验记录建议表：

| 实验 | 后端 | 策略 | Recall@5 | MRR@10 | nDCG@10 |
| --- | --- | --- | --- | --- | --- |
| baseline | FAISS | dense similarity | 待跑 | 待跑 | 待跑 |
| qdrant-dense | Qdrant | dense similarity | 待跑 | 待跑 | 待跑 |
| qdrant-rrf | Qdrant | multi-retriever+RRF | 待跑 | 待跑 | 待跑 |
| qdrant-rrf-rerank | Qdrant | RRF+rerank | 待跑 | 待跑 | 待跑 |

## 简历表达

不要写：

```text
使用 Qdrant 优化 RAG，提升效果。
```

应该写：

```text
基于 BEIR/SciFact 构建 RAG 检索评测集，将原 FAISS dense-only 检索升级为 Qdrant 可服务化向量检索架构，引入 Recall@K、MRR@K、nDCG@K 指标评估检索质量。
```

等 hybrid 和 rerank 跑出真实数据后再写：

```text
引入 BM25/sparse+dense 双路召回、RRF 融合与 rerank 重排，使 Recall@5 从 X% 提升至 Y%，MRR@10 从 A 提升至 B。
```

`X/Y/A/B` 必须来自评测报告，不能手写。

## 已知限制与注意事项

- 当前已实现评测、Qdrant 接入点、RRF 组合检索器与 rerank 检索器；sparse retriever 和 cross-encoder reranker 仍是后续增强点。
- Qdrant 依赖未安装时，`store_type="qdrant"` 会抛出清晰 ImportError；FAISS 路径不受影响。
- Python `>=3.14` 可能导致部分 AI 生态包暂未完整支持，依赖解析失败时先检查 Python 版本约束。

## 相关文档

- `.codestable/roadmap/large-scale-rag/large-scale-rag-roadmap.md`
- `.codestable/roadmap/large-scale-rag/large-scale-rag-items.yaml`
- `backend/rag/evaluation.py`
- `backend/rag/vector_stores.py`
