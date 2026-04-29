from typing import Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel


from ..schemas import ModelPresetConfig,ModelPreset

from ..config import settings, get_logger

logger = get_logger(__name__)


def get_chat_model(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    streaming: Optional[bool] = None,
    **kwargs:Any
) -> BaseChatModel:
    """获取配置好的聊天模型示例

    Args:
        model_name (Optional[str], optional): 模型名称. Defaults to None.
        temperature (Optional[float], optional): 模型温度. Defaults to None.
        max_tokens (Optional[int], optional): 最大tokens. Defaults to None.
        streaming (Optional[bool], optional): 是否启用流式. Defaults to None.

    Returns:
        BaseChatModel: 模型实例
    """ 
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
    
    

def get_streaming_model(
    model:Optional[str] = None,
    temperature:Optional[float] = None,
    **kwargs:Any
) -> BaseChatModel:
    """获取配置好的流式聊天模型示例，强制启用streaming=True

    Args:
        model (Optional[str], optional): 模型名称. Defaults to None.
        temperature (Optional[float], optional): 模型温度. Defaults to None.

    Returns:
        BaseChatModel: 模型实例
    """ 
    return get_chat_model(
        model_name=model,
        temperature=temperature,
        streaming=True,
        **kwargs
    )
    
    
def get_structured_output_model(
    model:Optional[str] = None,
    temperature:Optional[float] = None,
    **kwargs:Any
) -> BaseChatModel:
    """获取配置好的结构化输出模型示例，强制启用streaming=False

    Args:
        model (Optional[str], optional): 模型名称. Defaults to None.
        temperature (Optional[float], optional): 模型温度. Defaults to None.

    Returns:
        BaseChatModel: 模型实例
    """ 
    return get_chat_model(
        model_name=model,
        temperature=temperature,
        streaming=False,
        **kwargs
    )
    

    
MODEL_PRESETS_CONFIG:ModelPresetConfig = ModelPresetConfig(
    default=ModelPreset(
        model_name="gpt-5.5",
        temperature=0.7,
        description="默认预设，适用于大多数场景，平衡了速度和准确性。"
    ),
    fast=ModelPreset(
        model_name="deepseek-v4-flash",
        temperature=0.7,
        description="快速预设，适用于对响应速度要求较高的场景，可能牺牲部分准确性。"
    ),
    precise=ModelPreset(
        model_name="deepseek-v4-pro",
        temperature=0.3,
        description="精准预设，适用于对回答准确性要求较高的场景，响应速度可能较慢。"
    ),
    creative=ModelPreset(
        model_name="deepseek-v4-pro",
        temperature=1.0,
        description="创意预设，适用于需要生成富有创意内容的场景，可能牺牲部分准确性和响应速度。"
    )
)


def get_model_by_preset(preset:str = "default", **kwargs:Any) -> BaseChatModel:
    """根据预设名称获取配置好的聊天模型示例

    Args:
        preset (str, optional): 预设名称，支持"default"、"fast"、"precise"、"creative". Defaults to "default".

    Returns:
        BaseChatModel: 模型实例
    """ 
    if preset not in MODEL_PRESETS_CONFIG:
        available = ", ".join(MODEL_PRESETS_CONFIG.keys())
        raise ValueError(f"未知的预设: {preset}. 可用预设: {available}")
    
    config = MODEL_PRESETS_CONFIG[preset].copy()
    config.pop("description", None)  # 移除描述字段
    config.update(kwargs)  # 用户参数覆盖预设
    
    logger.info(f"📋 使用预设模型配置: {preset}")
    return get_chat_model(**config)


def get_model_string(
    model_name: Optional[str] = None,
    provider:str="openai"
) -> str:
    
    model_name = model_name or settings.model_name
    model_string = f"{provider}:{model_name}"
    
    logger.debug(f"🔤 生成模型标识符: {model_string}")
    return model_string
