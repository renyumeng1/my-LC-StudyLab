from typing import Any, NotRequired, Optional, TypedDict



class OpenAIConfig(TypedDict):
    """OpenAI相关配置的类型定义
    """
    api_key:str
    base_url:str
    model:str
    temperature:float
    max_tokens:NotRequired[int]
    
class ModelConfig(OpenAIConfig):
    """模型相关配置的类型定义，继承自OpenAIConfig
    """
    streaming:bool
    model_kwargs:NotRequired[dict[str,Any]]
