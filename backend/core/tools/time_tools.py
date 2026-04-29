from datetime import datetime
from venv import logger

from langchain.tools import tool

from ...config import get_logger

logger = get_logger(__name__)


@tool
def get_current_time() -> str:
    """获取当前时间
    
    **注意：查询天气时不需要调用此工具！天气工具内部已经知道了当前时间！**
    

    Returns:
        str: 当前时间的字符串表示。
    
    Example:
        >>> get_current_time()
        '当前时间是：2024-06-01 12:34:56'
    
    """ 
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.debug(f"当前时间为：{current_time}")
    
    return f"当前时间是：{current_time}"


@tool
def get_current_date() -> str:
    """获取当前日期和星期。

    仅当用户明确询问日期相关问题时使用，例如：
    - 今天是几号
    - 今天星期几
    - 当前日期是什么

    **不要在天气查询前调用此工具。天气工具已经知道了当前日期。**

    Returns:
        str: 当前日期和星期，格式为 ``今天是：YYYY-MM-DD （星期X）``。

    Example:
        >>> get_current_date()
        '今天是：2024-06-01 （星期六）'
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    weekday_map = {
       0: "星期一",
       1: "星期二",
       2: "星期三",
       3: "星期四",
       4: "星期五",
       5: "星期六",
       6: "星期日"
    }
    
    weekday = weekday_map[now.weekday()]
    
    result = f"{date_str} （{weekday}）"
    
    
    logger.debug(f"当前日期为：{result}")
    
    return f"今天是：{result}"
