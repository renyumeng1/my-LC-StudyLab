from typing import Optional, Sequence,Any
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool



from ..core.model import get_chat_model,get_streaming_model
from ..core.prompts import get_system_prompt,get_prompt_with_tools
from ..core.tools import ALL_TOOLS,BASIC_TOOLS

from ..config import settings,get_logger



logger = get_logger(__name__)

class BaseAgent:
    """Agent基类封装langchain的create_agent
    """
    
    
    # NOTE:这里的model可以是一个字符串，也可以是一个BaseLanguageModel对象，如果是字符串，就会被ChatOpenAI识别为模型名称，创建一个ChatOpenAI对象；如果是BaseLanguageModel对象，就直接使用这个对象作为模型。
    def __init__(
        self,
        model:Optional[str | BaseLanguageModel] = None,
        tools:Optional[Sequence[BaseTool]] = None,
        system_prompt:Optional[str]=None,
        prompt_mode:str = "default",
        debug:bool = False,
        **kwargs:Any
    ) -> None:
        """
        初始化 Base Agent
        
        
        Args:
            model: LLM 模型，可以是：
                   - 字符串标识符（如 "openai:gpt-4o"）
                   - BaseChatModel 实例
                   如果为 None，使用默认配置创建
            tools: Agent 可用的工具列表（Sequence[BaseTool]）
                   如果为 None 或空列表，Agent 将只包含模型节点，不进行工具调用循环
            system_prompt: 自定义系统提示词
                          如果为 None，则根据 prompt_mode 生成
            prompt_mode: 提示词模式（default/coding/research/concise/detailed）
            debug: 是否启用详细日志（对应 create_agent 的 debug 参数）
            **kwargs: 其他传递给 create_agent 的参数，如：
                     - checkpointer: 状态持久化
                     - store: 跨线程数据存储
                     - interrupt_before/interrupt_after: 中断点
                     - name: Agent 名称
        """
        pass