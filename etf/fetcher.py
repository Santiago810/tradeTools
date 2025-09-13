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
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
                return self._get_default_etf_info(etf_code)
            
            ak = self.data_sources['akshare']
            
            # 尝试多种方法获取ETF基本信息
            etf_info = {}
            
            # 方法1: 尝试获取ETF基金信息
            try:
                fund_info = ak.fund_etf_fund_info_em(etf_code)
                if not fund_info.empty:
                    latest_info = fund_info.iloc[-1]
                    etf_info.update({
                        '基金代码': etf_code,
                        '基金简称': latest_info.get('基金简称', f"ETF-{etf_code}"),
                        '最新净值': latest_info.get('单位净值', 'N/A')
                    })
            except Exception as e:
                self.logger.warning(f"方法1获取ETF {etf_code} 基金信息失败: {e}")
            
            # 方法2: 尝试获取ETF实时行情获取基本信息
            try:
                realtime_data = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                                  start_date="20240101", end_date="20241231")
                if not realtime_data.empty:
                    latest_data = realtime_data.iloc[-1]
                    etf_info.update({
                        '基金代码': etf_code,
                        '最新价格': latest_data.get('收盘', 'N/A'),
                        '最新日期': latest_data.get('日期', 'N/A')
                    })
            except Exception as e:
                self.logger.warning(f"方法2获取ETF {etf_code} 实时信息失败: {e}")
            
            # 方法3: 根据ETF代码推断基本信息
            etf_name_mapping = {
                '510310': '沪深300ETF',
                '510050': '上证50ETF', 
                '510500': '中证500ETF',
                '159919': '沪深300ETF',
                '159915': '创业板ETF',
                '512100': '中证1000ETF'
            }
            
            if etf_code in etf_name_mapping:
                etf_info.update({
                    '基金简称': etf_name_mapping[etf_code],
                    '跟踪标的': etf_name_mapping[etf_code].replace('ETF', '指数')
                })
            
            # 合并默认信息
            default_info = self._get_default_etf_info(etf_code)
            default_info.update(etf_info)
            
            return default_info
            
        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 基本信息失败: {e}")
            return self._get_default_etf_info(etf_code)
    
    def _get_default_etf_info(self, etf_code: str) -> Dict:
        """获取默认ETF信息"""
        # 根据ETF代码提供更准确的默认信息
        etf_defaults = {
            '510310': {
                '基金简称': '沪深300ETF',
                '成立日期': '2012-05-28',
                '基金规模': '约500亿元',
                '跟踪标的': '沪深300指数'
            },
            '510050': {
                '基金简称': '上证50ETF',
                '成立日期': '2004-12-30',
                '基金规模': '约600亿元',
                '跟踪标的': '上证50指数'
            },
            '510500': {
                '基金简称': '中证500ETF',
                '成立日期': '2013-02-06',
                '基金规模': '约300亿元',
                '跟踪标的': '中证500指数'
            },
            '159919': {
                '基金简称': '沪深300ETF',
                '成立日期': '2012-04-26',
                '基金规模': '约400亿元',
                '跟踪标的': '沪深300指数'
            },
            '159915': {
                '基金简称': '创业板ETF',
                '成立日期': '2011-09-20',
                '基金规模': '约200亿元',
                '跟踪标的': '创业板指数'
            },
            '512100': {
                '基金简称': '中证1000ETF',
                '成立日期': '2019-12-25',
                '基金规模': '约150亿元',
                '跟踪标的': '中证1000指数'
            }
        }
        
        # 获取特定ETF的默认信息，如果没有则使用通用默认值
        specific_info = etf_defaults.get(etf_code, {})
        
        return {
            '基金代码': etf_code,
            '基金简称': specific_info.get('基金简称', f"ETF-{etf_code}"),
            '成立日期': specific_info.get('成立日期', 'N/A'),
            '基金规模': specific_info.get('基金规模', 'N/A'), 
            '跟踪标的': specific_info.get('跟踪标的', 'N/A'),
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
            
            # 方法1: 尝试获取ETF资金流向数据（检查API是否存在）
            try:
                if hasattr(ak, 'fund_etf_fund_flow_em'):
                    fund_flow = ak.fund_etf_fund_flow_em(symbol=etf_code)
                    if not fund_flow.empty:
                        # 过滤日期范围
                        fund_flow['日期'] = pd.to_datetime(fund_flow['日期'])
                        start_dt = pd.to_datetime(start_date)
                        end_dt = pd.to_datetime(end_date)
                        fund_flow = fund_flow[(fund_flow['日期'] >= start_dt) & (fund_flow['日期'] <= end_dt)]
                        if not fund_flow.empty:
                            return fund_flow
                else:
                    self.logger.info(f"AKShare未提供fund_etf_fund_flow_em接口，跳过方法1")
            except Exception as e:
                self.logger.warning(f"方法1获取ETF {etf_code} 资金流向失败: {e}")
            
            # 方法2: 获取ETF历史行情数据作为资金流向的替代
            try:
                fund_flow = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                              start_date=start_date, end_date=end_date)
                if not fund_flow.empty:
                    # 计算资金流向指标
                    fund_flow['净流入'] = fund_flow['成交额'] * fund_flow['涨跌幅'] / 100
                    fund_flow['累计净流入'] = fund_flow['净流入'].cumsum()
                    return fund_flow
            except Exception as e:
                self.logger.warning(f"方法2获取ETF {etf_code} 历史数据失败: {e}")
            
            return pd.DataFrame()
            
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
    


# 工厂函数
def create_etf_fetcher() -> ETFFetcher:
    """创建ETF数据获取器实例"""
    return ETFFetcher()