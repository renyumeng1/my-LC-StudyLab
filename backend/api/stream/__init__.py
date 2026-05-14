"""
stream/__init__.py — 包入口
===========================
只导出 generate_stream，对外隐藏内部实现细节。
"""

from .generator import generate_stream

__all__ = ["generate_stream"]
