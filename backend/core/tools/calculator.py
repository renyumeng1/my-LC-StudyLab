"""
计算器工具
提供安全的数学表达式计算功能
"""

import re
from typing import Union
from langchain_core.tools import tool

from config import get_logger

logger = get_logger(__name__)


def _safe_eval(expression: str) -> Union[float, int, str]:
    """
    安全地计算数学表达式
    
    只允许基本的数学运算，防止代码注入攻击。
    
    Args:
        expression: 数学表达式字符串
        
    Returns:
        计算结果或错误信息
    """
    # 移除空格
    expression = expression.replace(" ", "")
    
    # 只允许数字、基本运算符和括号
    if not re.match(r'^[\d+\-*/().]+$', expression):
        return "错误：表达式包含不允许的字符。只支持数字和基本运算符 (+, -, *, /, ())"
    
    # 检查括号匹配
    if expression.count('(') != expression.count(')'):
        return "错误：括号不匹配"
    
    try:
        # 使用 eval 计算，但已经通过正则验证了安全性
        result = eval(expression)
        
        # 如果结果是整数，返回整数类型
        if isinstance(result, float) and result.is_integer():
            return int(result)
        
        # 浮点数保留合理的精度
        if isinstance(result, float):
            return round(result, 10)
        
        return result
    except ZeroDivisionError:
        return "错误：除数不能为零"
    except Exception as e:
        return f"错误：计算失败 - {str(e)}"


@tool
def calculator(expression: str) -> str:
    """
    计算数学表达式
    
    支持基本的数学运算：加法(+)、减法(-)、乘法(*)、除法(/)、括号()
    
    Args:
        expression: 要计算的数学表达式，例如 "2 + 2" 或 "(10 + 5) * 3"
        
    Returns:
        计算结果的字符串表示
        
    Example:
        >>> calculator("2 + 2")
        '2 + 2 = 4'
        
        >>> calculator("(10 + 5) * 3")
        '(10 + 5) * 3 = 45'
        
        >>> calculator("10 / 3")
        '10 / 3 = 3.3333333333'
    """
    logger.debug(f"🧮 计算表达式: {expression}")
    
    result = _safe_eval(expression)
    
    if isinstance(result, str) and result.startswith("错误"):
        logger.warning(f"❌ 计算失败: {result}")
        return result
    
    result_str = f"{expression} = {result}"
    logger.debug(f"✅ 计算结果: {result_str}")
    
    return result_str
