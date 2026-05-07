from typing import Any, Optional
from langchain_openai import OpenAIEmbeddings
from langchain.embeddings import Embeddings
from pydantic import SecretStr


from ..config import settings,get_logger



logger = get_logger(__name__)



def get_embeddings(
    model:Optional[str] = None,
    batch_size: Optional[int] = None,
    **kwargs: Any
) -> Embeddings:
    """获取 embedding 模型实例

    Args:
        model (Optional[str], optional): 模型名称默认使用 setting 中配置的模型. Defaults to None.
        batch_size (Optional[int], optional): 批处理大小，默认使用配置值. Defaults to None.

    Returns:
        Embeddings: 实例
    """
    
    model = model or settings.embedding_model
    
    batch_size = batch_size or settings.embedding_batch_size
    
    
    logger.info(f"🔢 创建 Embedding 模型: {model}")
    logger.debug(f"   batch_size: {batch_size}")
    
    
    try:
        embeddings = OpenAIEmbeddings(
            model=model,
            api_key=SecretStr(settings.openai_api_key),
            base_url=settings.openai_base_url,
            chunk_size=batch_size,
            **kwargs
        )
        logger.debug(f"✅ Embedding 模型创建成功: {model}")
        return embeddings

    except Exception as e:
        logger.error(f"❌ Embedding 模型创建失败: {e}")
        raise
    


def get_embedding_dimension(model: Optional[str] = None) -> int:
    """获取 embedding 维度

    Args:
        model (Optional[str], optional): 模型名称默认使用 setting 中配置的模型. Defaults to None.

    Returns:
        int: 维度
    """
    dimensions = {
    "BAAI/bge-large-zh-v1.5": 1024,
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-m3": 1024,
    "Pro/BAAI/bge-m3": 1024,
    "Qwen/Qwen3-Embedding-8B": 4096,
    "Qwen/Qwen3-Embedding-4B": 2560,
    "Qwen/Qwen3-Embedding-0.6B": 1024,
    "netease-youdao/bce-embedding-base_v1": 768,
    }
    
    if model not in dimensions:
        logger.warning(f"⚠️ 未知的 embedding 模型: {model}，使用默认维度 1536")
        return 1536
    
    return dimensions[model]


def estimate_embedding_cost(num_tokens:int,model: Optional[str] = None) -> float:
    """估算 embedding 成本

    Args:
        num_tokens (int): 消耗 Token 数量
        model (Optional[str], optional): 模型名称. Defaults to None.

    Returns:
        float: 估算成本
    """
    model = model or settings.embedding_model
    
    pricing = {
        "BAAI/bge-large-zh-v1.5": 0.10,
        "BAAI/bge-large-en-v1.5": 0.10,
        "BAAI/bge-m3": 0.70,
        "Pro/BAAI/bge-m3": 0.70,
        "Qwen/Qwen3-Embedding-8B": 1.00,
        "Qwen/Qwen3-Embedding-4B": 0.50,
        "Qwen/Qwen3-Embedding-0.6B": 0.20,
        "netease-youdao/bce-embedding-base_v1": 0.10,

    }
    
    if model not in pricing:
        logger.warning(f"⚠️ 未知的 embedding 模型: {model}，使用默认价格 0.0004/1K tokens")
        cost_per_1k_tokens = 0.0004
    else:
        cost_per_1k_tokens = pricing[model]
        
    cost = (num_tokens / 1000) * cost_per_1k_tokens
    logger.info(
        f"💰 Embedding 成本估算: "
        f"{num_tokens:,} tokens × ${cost_per_1k_tokens}/M = ${cost:.4f}"
    )
    
    return cost



def test_embeddings(
    model: Optional[str] = None,
    test_text:str = "这是一个测试文本"
) -> bool:
    """测试 embedding 模型是否可用

    Args:
        model (Optional[str], optional): 模型名称. Defaults to None.
        test_text (str, optional): 测试文本. Defaults to "这是一个测试文本".

    Returns:
        bool: 是否成功
    """
    try:
        logger.info(f"🔍 测试 Embedding 模型: {model}，使用测试文本: '{test_text}'")
        embeddings = get_embeddings(model=model)
        
        
        vector = embeddings.embed_query(test_text)
        
        logger.info(f"✅ Embedding 模型测试成功，向量维度: {len(vector)}")
        
        texts = [test_text,test_text + '2',test_text + '3']
        
        
        vectors = embeddings.embed_documents(texts)
        
        logger.info(f"✅ Embedding 模型批量测试成功，向量数量: {len(vectors)}")
        
        logger.info("测试通过")
        return True
    except Exception as e:
        logger.error(f"❌ Embedding 模型测试失败: {e}")
        return False
    
EMBEDDING_CONFIGS: dict[str, dict[str, Any]] = {
    "fast": {
        "model": "BAAI/bge-large-zh-v1.5",
        "description": "中文轻量嵌入，适合开发和测试",
    },
    "quality": {
        "model": "BAAI/bge-m3",
        "description": "多语言高质量嵌入，适合生产环境",
    },
    "multilingual": {
        "model": "BAAI/bge-m3",
        "description": "多语言长文本嵌入",
    },
    "large": {
        "model": "Qwen/Qwen3-Embedding-8B",
        "description": "超长文本和高质量嵌入，32K token 上下文",
    },
}


def get_embeddings_by_preset(
    preset: str = "fast",
    **kwargs: Any,
) -> Embeddings:
    """
    根据预设配置获取 Embedding 模型
    
    Args:
        preset: 预设名称
            - "fast": 快速模型（text-embedding-3-small）
            - "quality": 高质量模型（text-embedding-3-large）
            - "legacy": 旧版模型（text-embedding-ada-002）
        **kwargs: 覆盖预设的参数
        
    Returns:
        Embeddings 实例
        
    Raises:
        ValueError: 如果预设名称不存在
        
    Example:
        >>> # 使用快速模型
        >>> embeddings = get_embeddings_by_preset("fast")
        >>> 
        >>> # 使用高质量模型
        >>> embeddings = get_embeddings_by_preset("quality")
    """
    if preset not in EMBEDDING_CONFIGS:
        available = ", ".join(EMBEDDING_CONFIGS.keys())
        raise ValueError(
            f"未知的预设: {preset}. 可用预设: {available}"
        )
    
    config = EMBEDDING_CONFIGS[preset].copy()
    model = config.pop("model")
    config.pop("description", None)
    config.update(kwargs)
    
    logger.info(f"📋 使用预设 Embedding 配置: {preset}")
    return get_embeddings(model=model, **config)


if __name__ == "__main__":
    test_embeddings()
