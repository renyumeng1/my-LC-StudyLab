"""文档检索节点
# Note 这个节点可以对相关度算法进行拔高
# TODO 拔高相关度算法
"""

from datetime import datetime
from typing import Any,cast
from langchain.messages import AIMessage

from ..state import StudyFlowState,RetrievedDocument,LearningPlan

from ...rag.index_manager import IndexManager
from ...rag.embeddings import get_embeddings
from ...rag.retrievers import create_retriever
from ...config.logging import get_logger




logger = get_logger(__name__)



def retrieval_node(state:StudyFlowState) -> dict[str, Any]:
    """
    文档检索节点
    
    功能：
    1. 根据学习计划的主题和关键点检索相关文档
    2. 对检索结果进行排序和过滤
    3. 返回最相关的文档列表
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典，包含 retrieved_docs
    """
    
    
    logger.info(f"[Retrieval Node] 开始文档检索，学习主题: {cast(LearningPlan, state['learning_plan'])['topic']}")
    
    
    try:
        learning_plan =state.get("learning_plan")
        if not learning_plan:
            raise ValueError("学习计划不存在，无法进行文档检索")
        
        topic = learning_plan["topic"]
        key_points = learning_plan["key_points"]
        
        
        main_query = f"{topic}"
        
        logger.info(f"[Retrieval Node] 主查询: {main_query}")
        
        
        
        index_manager = IndexManager()
        embeddings = get_embeddings()
        
        try:
            vector_store = index_manager.load_index("test_index",embeddings)
            
            retriever = create_retriever(vector_store, top_k=5)
            
            logger.info("[Retrieval Node] 执行检索...")
            
            docs = retriever.invoke(main_query)
            
            
        except FileNotFoundError as e:
            logger.warning(f"[Retrieval Node] 索引文件未找到: {e}")
            docs = []
            
        retrieved_docs:list[RetrievedDocument] = []
        
        for i,doc in enumerate(docs):
            retrieved_doc:RetrievedDocument = {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": 1.0 - i * 0.1,  # 模拟相关性分数，实际应根据检索结果计算
            }
            
            retrieved_docs.append(retrieved_doc)
            
        logger.info(f"[Retrieval Node] 检索完成，找到 {len(retrieved_docs)} 个相关文档")
        
        
        if len(retrieved_docs) < 3 and key_points and docs:
            logger.info("[Retrieval Node] 文档较少，使用关键点补充检索...")
            
            try:
                for point in key_points[:2]:
                    additional_docs = retriever.invoke(point)
                    for doc in additional_docs:
                        retrieved_doc:RetrievedDocument = {
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "relevance_score": 0.7,  # 模拟较低的相关性分数
                        }
                        retrieved_docs.append(retrieved_doc)
                        
            except Exception as e:
                logger.warning(f"[Retrieval Node] 关键点补充检索失败: {e}")
                
        
        logger.info(f"[Retrieval Node] 最终检索到 {len(retrieved_docs)} 个文档")
        
        
        retrieval_summary = f"\n\n📄 已检索到 {len(retrieved_docs)} 个相关文档，将用于生成学习内容和练习题。"
        
        
        return {
            "retrieved_docs": retrieved_docs,
            "messages": [AIMessage(content=retrieval_summary)],
            "current_step": "retrieval",
            "update_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"[Retrieval Node] 文档检索失败: {str(e)}", exc_info=True)
        
        # 如果检索失败，返回空列表而不是报错，让流程继续
        # 这样即使没有文档，也可以基于 LLM 的知识生成内容
        logger.warning("[Retrieval Node] 检索失败，将继续使用 LLM 内置知识")
        
        return {
            "retrieved_docs": [],
            "messages":[AIMessage(content="\n\n⚠️ 文档检索遇到问题，将使用 AI 内置知识继续生成内容。")],
            "current_step": "retrieval",
            "update_at": datetime.now().isoformat(),
        }
        