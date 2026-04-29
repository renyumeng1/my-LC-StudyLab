from typing import Annotated, Any, NotRequired, Optional, TypedDict



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
    

class ModelPreset(TypedDict):
    """模型预设配置的类型定义
    """
    model_name:str
    temperature:float
    description:str
    

class ModelPresetConfig(TypedDict):
    """模型预设配置的类型定义
    """
    default: ModelPreset
    fast: ModelPreset
    precise: ModelPreset
    creative: ModelPreset
