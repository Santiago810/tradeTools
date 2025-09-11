"""
两融交易模块
A股融资融券交易数据查询和分析系统
"""

from .fetcher import create_margin_fetcher
from .processor import create_margin_processor
from .visualizer import create_margin_visualizer

__all__ = [
    'create_margin_fetcher',
    'create_margin_processor', 
    'create_margin_visualizer'
]