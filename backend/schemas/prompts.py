from typing import TypedDict


class SystemPrompt(TypedDict):
    """系统提示的类型定义
    """

    default:str
    coding:str
    research:str
    concise:str
    detailed:str