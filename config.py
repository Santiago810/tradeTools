"""
配置文件 - A股两融交易查询系统
"""

import os
from datetime import datetime, timedelta

# API配置
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', 'cd09c30ee83c804e585ef11e55c564b2c6799f971c87de252159f2e0')  # 需要用户自己申请Token

# 数据源配置
DATA_SOURCES = {
    'akshare': {
        'enabled': True,
        'description': 'AKShare开源金融数据接口'
    },
    'tushare': {
        'enabled': True,
        'description': 'TuShare专业金融数据接口'
    },
    'eastmoney': {
        'enabled': True,
        'description': '东方财富网数据'
    }
}

# 两融数据相关配置
MARGIN_TRADING_CONFIG = {
    # 默认查询时间范围
    'default_start_date': (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
    'default_end_date': datetime.now().strftime('%Y%m%d'),
    
    # 数据更新频率
    'update_frequency': 'daily',
    
    # 缓存配置
    'cache_enabled': True,
    'cache_duration': 3600,  # 1小时
    
    # 输出配置
    'output_formats': ['csv', 'excel', 'json'],
    'charts_enabled': True
}

# 股票市场配置
MARKET_CONFIG = {
    'markets': ['沪A', '深A', '创业板', '科创板'],
    'exchanges': ['SSE', 'SZSE'],  # 上交所、深交所
    'trading_days_only': True
}

# 可视化配置
CHART_CONFIG = {
    'figure_size': (12, 8),
    'dpi': 300,
    'style': 'seaborn-v0_8',
    'color_palette': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'],
    'font_family': 'SimHei'  # 支持中文显示
}

# 数据存储配置
STORAGE_CONFIG = {
    'data_dir': 'data',
    'output_dir': 'output',
    'log_dir': 'logs',
    'temp_dir': 'temp'
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_enabled': True,
    'console_enabled': True
}

# API限制配置
API_LIMITS = {
    'tushare': {
        'requests_per_minute': 200,
        'requests_per_day': 10000
    },
    'akshare': {
        'requests_per_minute': 60,
        'requests_per_day': 5000
    }
}