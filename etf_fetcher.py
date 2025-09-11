"""
EFT数据获取模块 - A股EFT查询系统
支持获取EFT的场外资金申购、份额变动、融资流向等数据
"""

import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config import DATA_SOURCES, TUSHARE_TOKEN
from utils import format_date, validate_date_range, load_cached_data, save_cached_data

class ETFFetcher:
    """EFT数据获取器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 初始化数据源
        self._init_data_sources()
    
    def _init_data_sources(self):
        """初始化数据源"""
        self.data_sources = {}
        
        # AKShare
        if DATA_SOURCES['akshare']['enabled']:
            try:
                import akshare as ak
                self.data_sources['akshare'] = ak
                self.logger.info("AKShare数据源初始化成功")
            except ImportError:
                self.logger.warning("AKShare未安装，跳过该数据源")
        
        # TuShare
        if DATA_SOURCES['tushare']['enabled'] and TUSHARE_TOKEN:
            try:
                import tushare as ts
                ts.set_token(TUSHARE_TOKEN)
                self.data_sources['tushare'] = ts.pro_api()
                self.logger.info("TuShare数据源初始化成功")
            except ImportError:
                self.logger.warning("TuShare未安装，跳过该数据源")
            except Exception as e:
                self.logger.error(f"TuShare初始化失败: {e}")
    
    def get_etf_info(self, etf_code: str) -> Dict:
        """
        获取ETF基本信息
        :param etf_code: ETF代码
        :return: ETF基本信息字典
        """
        try:
            if 'akshare' not in self.data_sources:
                return {}
            
            ak = self.data_sources['akshare']
            
            # 尝试获取ETF基本信息
            try:
                etf_info = ak.fund_etf_fund_info_em(etf_code)
                if not etf_info.empty:
                    # 从历史数据中提取基本信息
                    latest_info = etf_info.iloc[-1] if len(etf_info) > 0 else None
                    if latest_info is not None:
                        return {
                            '基金代码': etf_code,
                            '基金简称': f"ETF-{etf_code}",  # 默认名称
                            '成立日期': 'N/A',
                            '基金规模': 'N/A',
                            '跟踪标的': 'N/A',
                            '基金类型': 'ETF',
                            '最新净值': latest_info.get('单位净值', 'N/A') if hasattr(latest_info, '单位净值') else 'N/A'
                        }
            except Exception as e:
                self.logger.warning(f"获取ETF {etf_code} 基金信息失败: {e}")
            
            # 如果上面的方法失败，返回基本结构
            return {
                '基金代码': etf_code,
                '基金简称': f"ETF-{etf_code}",
                '成立日期': 'N/A',
                '基金规模': 'N/A',
                '跟踪标的': 'N/A',
                '基金类型': 'ETF'
            }
            
        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 基本信息失败: {e}")
            # 返回默认信息
            return {
                '基金代码': etf_code,
                '基金简称': f"ETF-{etf_code}",
                '成立日期': 'N/A',
                '基金规模': 'N/A',
                '跟踪标的': 'N/A',
                '基金类型': 'ETF'
            }
    
    def get_etf_fund_flow(self, etf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取ETF资金流向数据
        :param etf_code: ETF代码
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :return: ETF资金流向数据DataFrame
        """
        try:
            if 'akshare' not in self.data_sources:
                return pd.DataFrame()
            
            ak = self.data_sources['akshare']
            
            # 获取ETF历史行情数据作为资金流向的替代
            fund_flow = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                          start_date=start_date, end_date=end_date)
            return fund_flow if not fund_flow.empty else pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 资金流向数据失败: {e}")
            return pd.DataFrame()
    
    def get_etf_share_changes(self, etf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取ETF份额变动数据
        :param etf_code: ETF代码
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :return: ETF份额变动数据DataFrame
        """
        try:
            if 'akshare' not in self.data_sources:
                return pd.DataFrame()
            
            ak = self.data_sources['akshare']
            
            # 获取ETF历史行情数据，用于分析份额变动趋势
            share_changes = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                              start_date=start_date, end_date=end_date)
            return share_changes if not share_changes.empty else pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 份额变动数据失败: {e}")
            return pd.DataFrame()
    
    def get_etf_outside_market_data(self, etf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取ETF场外市场数据（申购赎回等）
        :param etf_code: ETF代码
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :return: ETF场外市场数据DataFrame
        """
        try:
            if 'akshare' not in self.data_sources:
                return pd.DataFrame()
            
            ak = self.data_sources['akshare']
            
            # 获取ETF历史行情数据作为场外市场数据的替代
            outside_data = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                             start_date=start_date, end_date=end_date)
            return outside_data if not outside_data.empty else pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 场外市场数据失败: {e}")
            return pd.DataFrame()
    
    def get_etf_minute_data(self, etf_code: str, period: str = "1") -> pd.DataFrame:
        """
        获取ETF分钟级别数据
        :param etf_code: ETF代码
        :param period: 时间周期 ("1" for 1分钟, "5" for 5分钟, "15" for 15分钟, "30" for 30分钟, "60" for 60分钟)
        :return: ETF分钟数据DataFrame
        """
        try:
            if 'akshare' not in self.data_sources:
                self.logger.warning("AKShare数据源未初始化，无法获取分钟数据")
                # 返回一个空的DataFrame，但包含所需的列名
                return pd.DataFrame(columns=['时间', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '均价', '涨跌幅'])
            
            ak = self.data_sources['akshare']
            
            # 获取ETF分钟数据
            self.logger.info(f"尝试获取ETF {etf_code} 的{period}分钟数据...")
            minute_data = ak.fund_etf_hist_min_em(symbol=etf_code, period=period)
            self.logger.info(f"获取到的分钟数据行数: {len(minute_data)}")
            
            if not minute_data.empty:
                # 确保列名统一
                column_mapping = {
                    '时间': '时间',
                    '开盘': '开盘',
                    '收盘': '收盘',
                    '最高': '最高',
                    '最低': '最低',
                    '成交量': '成交量',
                    '成交额': '成交额',
                    '均价': '均价',
                    '涨跌幅': '涨跌幅'
                }
                minute_data = minute_data.rename(columns=column_mapping)
            else:
                self.logger.warning(f"获取到的ETF {etf_code} 分钟数据为空")
                # 如果获取不到数据，返回一个空的DataFrame，但包含所需的列名
                return pd.DataFrame(columns=['时间', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '均价', '涨跌幅'])
            return minute_data
            
        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 分钟数据失败: {e}")
            # 返回一个空的DataFrame，但包含所需的列名
            return pd.DataFrame(columns=['时间', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '均价', '涨跌幅'])
    
    def get_etf_margin_data(self, etf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取ETF融资买入数据
        :param etf_code: ETF代码
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :return: ETF融资买入数据DataFrame
        """
        try:
            if 'akshare' not in self.data_sources:
                self.logger.warning("AKShare数据源未初始化，无法获取融资买入数据")
                # 返回一个空的DataFrame，但包含所需的列名
                return pd.DataFrame(columns=['证券代码', '证券简称', '融资买入额', '融资余额', '融券卖出量', '融券余量'])
            
            ak = self.data_sources['akshare']
            
            # 尝试获取ETF融资买入数据
            # 注意：不是所有ETF都有融资买入数据，需要检查是否为融资融券标的
            margin_data = pd.DataFrame()
            
            try:
                # 获取最新的融资融券数据
                margin_data = ak.stock_margin_underlying_info_szse(date=end_date)
                if not margin_data.empty:
                    # 筛选出指定ETF的数据
                    etf_margin_data = margin_data[margin_data['证券代码'] == etf_code]
                    if not etf_margin_data.empty:
                        return etf_margin_data
            except Exception as e:
                self.logger.warning(f"通过stock_margin_underlying_info_szse获取ETF {etf_code} 融资买入数据失败: {e}")
            
            # 如果上面的方法失败，尝试另一种方式
            try:
                self.logger.info(f"尝试获取ETF {etf_code} 在{end_date}的融资融券明细数据...")
                # 获取历史融资融券数据
                margin_hist_data = ak.stock_margin_detail_szse(date=end_date)
                self.logger.info(f"获取到的融资融券数据行数: {len(margin_hist_data)}")
                if not margin_hist_data.empty:
                    # 筛选出指定ETF的数据
                    etf_margin_data = margin_hist_data[margin_hist_data['证券代码'] == etf_code]
                    if not etf_margin_data.empty:
                        return etf_margin_data
            except Exception as e:
                self.logger.warning(f"通过stock_margin_detail_szse获取ETF {etf_code} 历史融资买入数据失败: {e}")
            
            self.logger.warning(f"无法获取ETF {etf_code} 的融资买入数据，所有方法均失败")
            # 如果都失败了，返回空的DataFrame，但包含所需的列名
            return pd.DataFrame(columns=['证券代码', '证券简称', '融资买入额', '融资余额', '融券卖出量', '融券余量'])
            
        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 融资买入数据失败: {e}")
            # 返回一个空的DataFrame，但包含所需的列名
            return pd.DataFrame(columns=['证券代码', '证券简称', '融资买入额', '融资余额', '融券卖出量', '融券余量'])

# 工厂函数
def create_etf_fetcher() -> ETFFetcher:
    """创建ETF数据获取器实例"""
    return ETFFetcher()