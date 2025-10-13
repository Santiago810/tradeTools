"""
两融数据获取模块 - A股两融交易查询系统
支持获取A股市场的融资融券交易数据
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

from config import DATA_SOURCES, TUSHARE_TOKEN, MARGIN_TRADING_CONFIG
from utils import format_date, validate_date_range, load_cached_data, save_cached_data

class MarginDataFetcher:
    """两融数据获取器"""
    
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
    
    def get_margin_trading_summary(self, start_date: str, end_date: str, 
                                 use_cache: bool = True) -> pd.DataFrame:
        """
        获取两融交易汇总数据
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :param use_cache: 是否使用缓存
        :return: 两融交易汇总数据DataFrame
        """
        start_date, end_date = validate_date_range(start_date, end_date)
        # 添加版本标识以区分不同的数据获取逻辑
        cache_key = f"margin_summary_v2_{start_date}_{end_date}"  # v2表示合并沪深数据的新版本
        
        # 尝试从缓存加载
        if use_cache:
            cached_data = load_cached_data(cache_key)
            if cached_data is not None:
                self.logger.info("从缓存加载两融汇总数据(沪深合并版本)")
                return cached_data
        
        # 从多个数据源获取数据
        data_frames = []
        
        # 1. 尝试从AKShare获取
        akshare_data = self._get_margin_data_akshare(start_date, end_date)
        if not akshare_data.empty:
            data_frames.append(akshare_data)
        
        # 2. 尝试从TuShare获取
        tushare_data = self._get_margin_data_tushare(start_date, end_date)
        if not tushare_data.empty:
            data_frames.append(tushare_data)
        
        # 3. 尝试从东方财富获取
        eastmoney_data = self._get_margin_data_eastmoney(start_date, end_date)
        if not eastmoney_data.empty:
            data_frames.append(eastmoney_data)
        
        # 合并数据 - 优先使用AKShare的合并数据，因为它已经正确处理了沪深合并
        if data_frames:
            # 优先选择AKShare数据（如果可用），因为它提供了正确的沪深合并数据
            if not akshare_data.empty:
                result = akshare_data
                self.logger.info(f"使用AKShare数据源，共{len(result)}条记录")
            else:
                # 如果AKShare不可用，选择数据最完整的其他数据源
                result = max(data_frames, key=len)
                self.logger.info(f"使用备用数据源，共{len(result)}条记录")
            
            # 保存到缓存
            if use_cache:
                save_cached_data(result, cache_key)
            
            return result
        else:
            self.logger.error("所有数据源都无法获取数据")
            return pd.DataFrame()
    
    def _get_margin_data_akshare(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从AKShare获取两融数据"""
        try:
            if 'akshare' not in self.data_sources:
                return pd.DataFrame()
            
            ak = self.data_sources['akshare']
            
            # 获取两融余额数据
            self.logger.info("正在从AKShare获取沪深两市两融数据...")
            
            # 获取上海交易所两融数据
            sh_margin = ak.macro_china_market_margin_sh()
            self.logger.info(f"获取上海交易所数据: {len(sh_margin)}条")
            
            # 获取深圳交易所两融数据
            sz_margin = ak.macro_china_market_margin_sz()
            self.logger.info(f"获取深圳交易所数据: {len(sz_margin)}条")
            
            # 合并沪深两市数据
            merged_data = self._merge_sh_sz_margin_data(sh_margin, sz_margin, start_date, end_date)
            
            if not merged_data.empty:
                # 标准化列名
                merged_data = self._standardize_columns_akshare(merged_data)
                self.logger.info(f"AKShare获取到合并后数据{len(merged_data)}条记录")
                return merged_data
            
        except Exception as e:
            self.logger.error(f"AKShare获取数据失败: {e}")
        
        return pd.DataFrame()
    
    def _get_margin_data_tushare(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从TuShare获取两融数据"""
        try:
            if 'tushare' not in self.data_sources:
                return pd.DataFrame()
            
            pro = self.data_sources['tushare']
            
            self.logger.info("正在从TuShare获取两融数据...")
            
            # 获取两融余额数据
            margin_data = pro.margin(start_date=start_date, end_date=end_date, 
                                   exchange_id='', trade_date='')
            
            if not margin_data.empty:
                # 按日期合并各交易所数据
                margin_data = self._merge_tushare_exchanges(margin_data)
                # 标准化列名
                margin_data = self._standardize_columns_tushare(margin_data)
                self.logger.info(f"TuShare获取到{len(margin_data)}条记录")
                return margin_data
            
        except Exception as e:
            self.logger.error(f"TuShare获取数据失败: {e}")
        
        return pd.DataFrame()
    
    def _get_margin_data_eastmoney(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从东方财富网获取两融数据"""
        try:
            self.logger.info("正在从东方财富网获取两融数据...")
            
            # 构建请求URL
            url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
            
            params = {
                'sortColumns': 'TRADE_DATE',
                'sortTypes': '-1',
                'pageSize': '5000',
                'pageNumber': '1',
                'reportName': 'RPT_RZRQ_LSHJ',
                'columns': 'ALL',
                'filter': f'(TRADE_DATE>="{start_date}" and TRADE_DATE<="{end_date}")'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success') and data.get('result', {}).get('data'):
                records = data['result']['data']
                df = pd.DataFrame(records)
                
                if not df.empty:
                    # 标准化列名
                    df = self._standardize_columns_eastmoney(df)
                    self.logger.info(f"东方财富网获取到{len(df)}条记录")
                    return df
            
        except Exception as e:
            self.logger.error(f"东方财富网获取数据失败: {e}")
        
        return pd.DataFrame()
    
    def _standardize_columns_akshare(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化AKShare数据列名"""
        column_mapping = {
            '日期': '交易日期',
            '融资余额': '融资余额',
            '融券余额': '融券余额',
            '融资融券余额': '两融余额',
            '融资买入额': '融资买入额',
            '融券卖出量': '融券卖出量',
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 确保日期格式正确
        if '交易日期' in df.columns:
            df['交易日期'] = pd.to_datetime(df['交易日期']).dt.strftime('%Y%m%d')
        
        # 数值列转换
        numeric_columns = ['融资余额', '融券余额', '两融余额', '融资买入额']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def _merge_tushare_exchanges(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        合并TuShare各交易所数据
        :param df: TuShare原始数据
        :return: 按日期合并后的数据
        """
        try:
            if df.empty:
                return df
            
            # 按交易日期分组，合并各交易所数据
            grouped = df.groupby('trade_date').agg({
                'rzye': 'sum',      # 融资余额
                'rzmre': 'sum',     # 融资买入额
                'rzche': 'sum',     # 融资偿还额
                'rqye': 'sum',      # 融券余额
                'rqmcl': 'sum',     # 融券卖出量
                'rzrqye': 'sum',    # 两融余额
                'rqyl': 'sum'       # 融券余量
            }).reset_index()
            
            # 添加exchange_id列标识为合并数据
            grouped['exchange_id'] = 'ALL'
            
            self.logger.info(f"TuShare数据合并完成: {len(grouped)}条记录")
            return grouped
            
        except Exception as e:
            self.logger.error(f"TuShare数据合并失败: {e}")
            return df
    
    def _merge_sh_sz_margin_data(self, sh_data: pd.DataFrame, sz_data: pd.DataFrame, 
                                start_date: str, end_date: str) -> pd.DataFrame:
        """
        合并沪深两市两融数据
        :param sh_data: 上海交易所数据
        :param sz_data: 深圳交易所数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 合并后的数据
        """
        try:
            if sh_data.empty or sz_data.empty:
                self.logger.warning("沪深数据中有空数据，无法合并")
                return pd.DataFrame()
            
            # 确保日期列格式一致
            sh_data['日期'] = pd.to_datetime(sh_data['日期'])
            sz_data['日期'] = pd.to_datetime(sz_data['日期'])
            
            # 过滤日期范围
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')
            
            sh_filtered = sh_data[(sh_data['日期'] >= start_dt) & (sh_data['日期'] <= end_dt)].copy()
            sz_filtered = sz_data[(sz_data['日期'] >= start_dt) & (sz_data['日期'] <= end_dt)].copy()
            
            # 如果指定日期范围内没有数据，尝试获取最近的数据
            if sh_filtered.empty or sz_filtered.empty:
                self.logger.warning(f"指定日期范围内数据为空: 沪市{len(sh_filtered)}条，深市{len(sz_filtered)}条")
                # 获取最近20个交易日的数据作为备选
                sh_filtered = sh_data.tail(20).copy()
                sz_filtered = sz_data.tail(20).copy()
                self.logger.info(f"使用最近数据: 沪市{len(sh_filtered)}条，深市{len(sz_filtered)}条")
                
                if sh_filtered.empty or sz_filtered.empty:
                    return pd.DataFrame()
            
            # 按日期合并数据
            merged = pd.merge(sh_filtered, sz_filtered, on='日期', suffixes=('_sh', '_sz'))
            
            if merged.empty:
                self.logger.warning("合并后数据为空")
                return pd.DataFrame()
            
            # 计算合计数据
            result = pd.DataFrame()
            result['日期'] = merged['日期']
            
            # 合并数值列（沪深两市相加）
            numeric_cols = ['融资买入额', '融资余额', '融券卖出量', '融券余量', '融券余额', '融资融券余额']
            
            for col in numeric_cols:
                sh_col = f'{col}_sh'
                sz_col = f'{col}_sz'
                
                if sh_col in merged.columns and sz_col in merged.columns:
                    # 确保数值类型
                    sh_values = pd.to_numeric(merged[sh_col], errors='coerce').fillna(0)
                    sz_values = pd.to_numeric(merged[sz_col], errors='coerce').fillna(0)
                    result[col] = sh_values + sz_values
            
            # 重新格式化日期
            result['日期'] = result['日期'].dt.strftime('%Y%m%d')
            
            self.logger.info(f"成功合并沪深数据，共{len(result)}条记录")
            
            # 显示最新数据作为验证
            if not result.empty and '融资融券余额' in result.columns:
                latest_balance = result['融资融券余额'].iloc[-1] / 1e12  # 转换为万亿
                self.logger.info(f"最新两融余额: {latest_balance:.2f}万亿")
            
            return result
            
        except Exception as e:
            self.logger.error(f"合并沪深数据失败: {e}")
            return pd.DataFrame()
    
    def _standardize_columns_tushare(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化TuShare数据列名"""
        column_mapping = {
            'trade_date': '交易日期',
            'rzye': '融资余额',
            'rqye': '融券余额',
            'rzrqye': '两融余额',
            'rzmre': '融资买入额',
            'rqmcl': '融券卖出量',
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 数值列转换（TuShare数据通常以万元为单位）
        numeric_columns = ['融资余额', '融券余额', '两融余额', '融资买入额']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') * 10000  # 万元转元
        
        return df
    
    def _standardize_columns_eastmoney(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化东方财富数据列名"""
        column_mapping = {
            'TRADE_DATE': '交易日期',
            'RZYE': '融资余额',
            'RQYE': '融券余额',
            'RZRQYE': '两融余额',
            'RZMRE': '融资买入额',
            'RQMCL': '融券卖出量',
            'RQMCJE': '融券卖出额',
        }
        
        # 重命名列
        df = df.rename(columns=column_mapping)
        
        # 确保日期格式正确
        if '交易日期' in df.columns:
            df['交易日期'] = pd.to_datetime(df['交易日期']).dt.strftime('%Y%m%d')
        
        # 数值列转换（东方财富数据通常以元为单位）
        numeric_columns = ['融资余额', '融券余额', '两融余额', '融资买入额', '融券卖出额']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def get_market_turnover(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取市场成交金额数据
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 市场成交金额DataFrame
        """
        try:
            if 'akshare' not in self.data_sources:
                self.logger.error("无法获取市场成交数据：AKShare未初始化")
                return pd.DataFrame()
            
            ak = self.data_sources['akshare']
            
            # 获取沪深股市成交金额
            self.logger.info("正在获取市场成交金额数据...")
            
            # 使用AKShare的新接口获取股票历史数据
            # 替换已废弃的 stock_zh_a_hist_daily_tx 函数
            try:
                # 沪市成交金额 (上证指数)
                sh_turnover = ak.stock_zh_a_hist(symbol="sh000001", 
                                               period="daily",
                                               start_date=start_date, 
                                               end_date=end_date)
                
                # 深市成交金额 (深证成指)
                sz_turnover = ak.stock_zh_a_hist(symbol="sz399001", 
                                               period="daily",
                                               start_date=start_date, 
                                               end_date=end_date)
            except AttributeError:
                # 如果上述接口不可用，尝试其他可能的接口
                self.logger.warning("stock_zh_a_hist接口不可用，尝试备选方案")
                try:
                    # 尝试使用市场概况数据作为替代
                    sh_turnover = ak.stock_zh_a_spot_em()
                    sz_turnover = ak.stock_zh_a_spot_em()
                except Exception as e:
                    raise e
            
            # 合并数据
            if not sh_turnover.empty and not sz_turnover.empty:
                # 处理数据
                sh_turnover['市场'] = '沪市'
                sz_turnover['市场'] = '深市'
                
                # 标准化列名
                turnover_data = pd.concat([sh_turnover, sz_turnover], ignore_index=True)
                
                if '日期' in turnover_data.columns:
                    turnover_data['交易日期'] = pd.to_datetime(turnover_data['日期']).dt.strftime('%Y%m%d')
                
                return turnover_data
            
        except Exception as e:
            self.logger.error(f"获取市场成交数据失败: {e}")
        
        return pd.DataFrame()
    
    def get_stock_margin_detail(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取个股两融明细数据
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 个股两融明细DataFrame
        """
        try:
            if 'akshare' not in self.data_sources:
                return pd.DataFrame()
            
            ak = self.data_sources['akshare']
            
            self.logger.info(f"正在获取{stock_code}的两融明细数据...")
            
            # 获取个股两融数据
            stock_margin = ak.stock_margin_underlying_info_szse(symbol=stock_code)
            
            if not stock_margin.empty:
                # 过滤日期范围
                stock_margin['交易日期'] = pd.to_datetime(stock_margin['日期']).dt.strftime('%Y%m%d')
                stock_margin = stock_margin[
                    (stock_margin['交易日期'] >= start_date) & 
                    (stock_margin['交易日期'] <= end_date)
                ]
                
                self.logger.info(f"获取到{stock_code}的{len(stock_margin)}条记录")
                return stock_margin
            
        except Exception as e:
            self.logger.error(f"获取{stock_code}两融明细失败: {e}")
        
        return pd.DataFrame()

# 工厂函数
def create_margin_fetcher() -> MarginDataFetcher:
    """创建两融数据获取器实例"""
    return MarginDataFetcher()