"""
ETF基金模块
A股ETF基金数据查询和分析系统
"""

from .fetcher import create_etf_fetcher
from .processor import create_etf_processor
from .visualizer import create_etf_visualizer

__all__ = [
    'create_etf_fetcher',
    'create_etf_processor',
    'create_etf_visualizer'
]