"""
工具函数模块 - A股两融交易查询系统
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional
from config import STORAGE_CONFIG, LOGGING_CONFIG

def setup_logging():
    """设置日志配置"""
    # 创建日志目录
    log_dir = STORAGE_CONFIG['log_dir']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置日志
    log_file = os.path.join(log_dir, f"margin_trading_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG['level']),
        format=LOGGING_CONFIG['format'],
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        STORAGE_CONFIG['data_dir'],
        STORAGE_CONFIG['output_dir'],
        STORAGE_CONFIG['log_dir'],
        STORAGE_CONFIG['temp_dir']
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")

def format_date(date_input) -> str:
    """
    格式化日期
    :param date_input: 日期输入，支持字符串、datetime对象
    :return: 格式化后的日期字符串 YYYYMMDD
    """
    if isinstance(date_input, str):
        # 如果已经是YYYYMMDD格式
        if len(date_input) == 8 and date_input.isdigit():
            return date_input
        # 尝试解析其他日期格式
        try:
            dt = pd.to_datetime(date_input)
            return dt.strftime('%Y%m%d')
        except:
            raise ValueError(f"无法解析日期格式: {date_input}")
    elif isinstance(date_input, datetime):
        return date_input.strftime('%Y%m%d')
    else:
        raise ValueError(f"不支持的日期类型: {type(date_input)}")

def validate_date_range(start_date: str, end_date: str) -> tuple:
    """
    验证日期范围
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 验证后的日期元组
    """
    start_date = format_date(start_date)
    end_date = format_date(end_date)
    
    if start_date > end_date:
        raise ValueError("开始日期不能大于结束日期")
    
    # 检查日期范围是否合理（不超过2年）
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    if (end_dt - start_dt).days > 730:
        logging.warning("查询时间范围超过2年，可能影响性能")
    
    return start_date, end_date

def calculate_margin_ratio(margin_data: pd.DataFrame) -> pd.DataFrame:
    """
    计算两融交易占比
    :param margin_data: 两融数据DataFrame
    :return: 包含占比计算的DataFrame
    """
    if margin_data.empty:
        return margin_data
    
    # 确保必要的列存在
    required_columns = ['融资余额', '融券余额', '两融余额', '成交金额']
    for col in required_columns:
        if col not in margin_data.columns:
            logging.warning(f"缺少必要列: {col}")
    
    result = margin_data.copy()
    
    try:
        # 计算两融余额占比
        if '两融余额' in result.columns and '成交金额' in result.columns:
            result['两融余额占比'] = (result['两融余额'] / result['成交金额']) * 100
        
        # 计算融资占比
        if '融资余额' in result.columns and '成交金额' in result.columns:
            result['融资占比'] = (result['融资余额'] / result['成交金额']) * 100
        
        # 计算融券占比
        if '融券余额' in result.columns and '成交金额' in result.columns:
            result['融券占比'] = (result['融券余额'] / result['成交金额']) * 100
        
        # 处理无穷大和NaN值
        result = result.replace([np.inf, -np.inf], np.nan)
        
    except Exception as e:
        logging.error(f"计算两融占比时出错: {e}")
    
    return result

def save_data(data: pd.DataFrame, filename: str, format_type: str = 'csv'):
    """
    保存数据到文件
    :param data: 要保存的DataFrame
    :param filename: 文件名
    :param format_type: 文件格式 ('csv', 'excel', 'json')
    """
    output_dir = STORAGE_CONFIG['output_dir']
    ensure_directories()
    
    file_path = os.path.join(output_dir, filename)
    
    try:
        if format_type.lower() == 'csv':
            data.to_csv(file_path, index=False, encoding='utf-8-sig')
        elif format_type.lower() == 'excel':
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            data.to_excel(file_path, index=False, engine='openpyxl')
        elif format_type.lower() == 'json':
            if not file_path.endswith('.json'):
                file_path += '.json'
            data.to_json(file_path, orient='records', force_ascii=False, indent=2)
        
        logging.info(f"数据已保存到: {file_path}")
        return file_path
        
    except Exception as e:
        logging.error(f"保存数据时出错: {e}")
        return None

def load_cached_data(cache_key: str):
    """
    加载缓存数据
    :param cache_key: 缓存键
    :return: 缓存的数据或None
    """
    cache_dir = STORAGE_CONFIG['temp_dir']
    cache_file = os.path.join(cache_dir, f"{cache_key}.pkl")
    
    try:
        if os.path.exists(cache_file):
            # 检查缓存时间
            cache_time = os.path.getmtime(cache_file)
            current_time = datetime.now().timestamp()
            
            if current_time - cache_time < 3600:  # 1小时内的缓存有效
                import pickle
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        
    except Exception as e:
        logging.error(f"加载缓存数据时出错: {e}")
    
    return None

def save_cached_data(data, cache_key: str):
    """
    保存数据到缓存
    :param data: 要缓存的数据（DataFrame或其他对象）
    :param cache_key: 缓存键
    """
    cache_dir = STORAGE_CONFIG['temp_dir']
    ensure_directories()
    cache_file = os.path.join(cache_dir, f"{cache_key}.pkl")
    
    try:
        import pickle
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        logging.info(f"数据已缓存到: {cache_file}")
    except Exception as e:
        logging.error(f"保存缓存数据时出错: {e}")

def format_number(number: float, decimal_places: int = 2) -> str:
    """
    格式化数字显示
    :param number: 要格式化的数字
    :param decimal_places: 小数位数
    :return: 格式化后的字符串
    """
    if pd.isna(number):
        return "N/A"
    
    if abs(number) >= 1e8:
        return f"{number/1e8:.{decimal_places}f}亿"
    elif abs(number) >= 1e4:
        return f"{number/1e4:.{decimal_places}f}万"
    else:
        return f"{number:.{decimal_places}f}"

def get_trading_dates(start_date: str, end_date: str) -> List[str]:
    """
    获取指定范围内的交易日期
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 交易日期列表
    """
    try:
        import akshare as ak
        # 获取交易日历
        trade_cal = ak.tool_trade_date_hist_sina()
        trade_dates = trade_cal['trade_date'].dt.strftime('%Y%m%d').tolist()
        
        # 筛选指定范围内的交易日期
        result = [date for date in trade_dates if start_date <= date <= end_date]
        return result
        
    except Exception as e:
        logging.error(f"获取交易日期时出错: {e}")
        # 如果获取失败，返回日期范围内的所有日期（排除周末）
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        weekdays = [d.strftime('%Y%m%d') for d in dates if d.weekday() < 5]
        return weekdays