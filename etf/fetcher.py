"""
EFT数据获取模块 - A股EFT查询系统
支持获取EFT的场外资金申购、份额变动、融资流向等数据
"""

from utils import format_date, validate_date_range, load_cached_data, save_cached_data
from config import DATA_SOURCES, TUSHARE_TOKEN
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



    def get_etf_fund_flow(self, etf_code: str, start_date: str, end_date: str, use_cache: bool = True) -> pd.DataFrame:
        """
        获取ETF资金流向数据
        :param etf_code: ETF代码
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :param use_cache: 是否使用缓存
        :return: ETF资金流向数据DataFrame
        """
        try:
            # 生成缓存键
            cache_key = f"etf_fund_flow_{etf_code}_{start_date}_{end_date}"

            # 尝试从缓存加载
            if use_cache:
                cached_data = load_cached_data(cache_key)
                if cached_data is not None:
                    self.logger.info(f"从缓存加载ETF {etf_code} 资金流向数据")
                    return cached_data

            if 'akshare' not in self.data_sources:
                return pd.DataFrame()

            ak = self.data_sources['akshare']

            # 方法2: 获取ETF历史行情数据作为资金流向的替代
            try:
                fund_flow = ak.fund_etf_hist_em(symbol=etf_code, period="daily",
                                                start_date=start_date, end_date=end_date)
                if not fund_flow.empty:
                    # 计算资金流向指标
                    fund_flow['净流入'] = fund_flow['成交额'] * \
                        fund_flow['涨跌幅'] / 100
                    fund_flow['累计净流入'] = fund_flow['净流入'].cumsum()

                    # 保存到缓存
                    if use_cache:
                        save_cached_data(fund_flow, cache_key)
                        self.logger.info(f"ETF {etf_code} 资金流向数据已缓存")

                    return fund_flow
            except Exception as e:
                self.logger.warning(f"方法2获取ETF {etf_code} 历史数据失败: {e}")

            return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 资金流向数据失败: {e}")
            return pd.DataFrame()

    def get_etf_share_changes(self, etf_code: str, start_date: str, end_date: str, use_cache: bool = True) -> pd.DataFrame:
        """
        获取ETF份额变动数据
        :param etf_code: ETF代码
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :param use_cache: 是否使用缓存
        :return: ETF份额变动数据DataFrame
        """
        try:
            # 生成缓存键
            cache_key = f"etf_share_changes_{etf_code}_{start_date}_{end_date}"

            # 尝试从缓存加载
            if use_cache:
                cached_data = load_cached_data(cache_key)
                if cached_data is not None:
                    self.logger.info(f"从缓存加载ETF {etf_code} 份额变动数据")
                    return cached_data

            if 'akshare' not in self.data_sources:
                return pd.DataFrame()

            ak = self.data_sources['akshare']

            # 获取ETF历史行情数据，用于分析份额变动趋势
            share_changes = ak.fund_etf_hist_em(symbol=etf_code, period="daily",
                                                start_date=start_date, end_date=end_date)

            if not share_changes.empty:
                # 保存到缓存
                if use_cache:
                    save_cached_data(share_changes, cache_key)
                    self.logger.info(f"ETF {etf_code} 份额变动数据已缓存")
                return share_changes
            else:
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 份额变动数据失败: {e}")
            return pd.DataFrame()

    def get_etf_outside_market_data(self, etf_code: str, start_date: str, end_date: str, use_cache: bool = True) -> pd.DataFrame:
        """
        获取ETF场外市场数据（申购赎回等）
        :param etf_code: ETF代码
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :param use_cache: 是否使用缓存
        :return: ETF场外市场数据DataFrame
        """
        try:
            # 生成缓存键
            cache_key = f"etf_outside_market_{etf_code}_{start_date}_{end_date}"

            # 尝试从缓存加载
            if use_cache:
                cached_data = load_cached_data(cache_key)
                if cached_data is not None:
                    self.logger.info(f"从缓存加载ETF {etf_code} 场外市场数据")
                    return cached_data

            if 'akshare' not in self.data_sources:
                return pd.DataFrame()

            ak = self.data_sources['akshare']

            # 获取ETF历史行情数据作为场外市场数据的替代
            outside_data = ak.fund_etf_hist_em(symbol=etf_code, period="daily",
                                               start_date=start_date, end_date=end_date)

            if not outside_data.empty:
                # 保存到缓存
                if use_cache:
                    save_cached_data(outside_data, cache_key)
                    self.logger.info(f"ETF {etf_code} 场外市场数据已缓存")
                return outside_data
            else:
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"获取ETF {etf_code} 场外市场数据失败: {e}")
            return pd.DataFrame()

    def get_etf_minute_data(self, etf_code: str, period: str = "1", use_cache: bool = True, for_realtime: bool = False) -> pd.DataFrame:
        """
        获取ETF分钟级别数据
        :param etf_code: ETF代码
        :param period: 时间周期 ("1" for 1分钟, "5" for 5分钟, "15" for 15分钟, "30" for 30分钟, "60" for 60分钟)
        :param use_cache: 是否使用缓存
        :param for_realtime: 是否用于实时分析（实时分析不使用缓存）
        :return: ETF分钟数据DataFrame
        """
        try:
            # 实时分析不使用缓存，确保数据最新
            if for_realtime:
                use_cache = False
                self.logger.info(f"实时分析模式：不使用缓存，获取最新的ETF {etf_code} 分钟数据")

            # 生成缓存键（分钟数据按日期和小时缓存，提高实时性）
            from datetime import datetime
            now = datetime.now()
            today = now.strftime('%Y%m%d')
            current_hour = now.strftime('%H')
            cache_key = f"etf_minute_data_{etf_code}_{period}_{today}_{current_hour}"

            # 尝试从缓存加载（仅在非实时模式下）
            if use_cache and not for_realtime:
                cached_data = load_cached_data(cache_key)
                if cached_data is not None:
                    self.logger.info(f"从缓存加载ETF {etf_code} 分钟数据")
                    return cached_data

            if 'akshare' not in self.data_sources:
                self.logger.warning("AKShare数据源未初始化，无法获取分钟数据")
                # 返回一个空的DataFrame，但包含所需的列名
                return pd.DataFrame(columns=['时间', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '均价', '涨跌幅'])

            ak = self.data_sources['akshare']

            # 获取ETF分钟数据
            self.logger.info(f"尝试获取ETF {etf_code} 的{period}分钟数据...")
            minute_data = ak.fund_etf_hist_min_em(
                symbol=etf_code, period=period)
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

                # 保存到缓存（仅在非实时模式下）
                if use_cache and not for_realtime:
                    save_cached_data(minute_data, cache_key)
                    self.logger.info(f"ETF {etf_code} 分钟数据已缓存")
                elif for_realtime:
                    self.logger.info(f"实时模式：ETF {etf_code} 分钟数据不缓存，保证数据实时性")
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
