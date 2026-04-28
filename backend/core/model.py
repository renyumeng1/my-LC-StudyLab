from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from ..config import settings, get_logger

logger = get_logger(__name__)


def get_chat_model(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    streaming: Optional[bool] = None,
    **kwargs:Any
) -> BaseChatModel:
    model_name = model_name or settings.model_name
    temperature = temperature if temperature is not None else settings.openai_temperature
    max_tokens = max_tokens if max_tokens is not None else settings.open_ai_max_tokens
    streaming = streaming if streaming is not None else settings.openai_stream
    
    model_config:dict[str,Any] = {
        "model": model_name,
        "temperature": temperature,
        "streaming": streaming,
        "api_key": settings.openai_api_key,
        "base_url": settings.openai_base_url,
    }
    
    if max_tokens is not None:
        model_config["max_tokens"] = max_tokens
    elif settings.open_ai_max_tokens is not None:
        model_config["max_tokens"] = settings.open_ai_max_tokens
        
    model_config.update(kwargs)
    
    logger.info(
        f"🤖 创建聊天模型: {model_name} "
        f"(temperature={temperature}, streaming={streaming})"
    )
    
    try:
        model = ChatOpenAI(**model_config)
        logger.debug(f"✅ 模型创建成功: {model_name}")
        return model
    
    except Exception as e:
        logger.error(f"❌ 模型创建失败: {e}")
        raise
