from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from dotenv import load_dotenv



class BaseAgent:
    """Agent基类封装langchain的create_agent
    """
    
    
    # NOTE:这里的model可以是一个字符串，也可以是一个BaseLanguageModel对象，如果是字符串，就会被ChatOpenAI识别为模型名称，创建一个ChatOpenAI对象；如果是BaseLanguageModel对象，就直接使用这个对象作为模型。
    def __init__(
        self,
        model:Optional[str | BaseLanguageModel] = None
                 ):
        
        
        
        pass