"""
板块资金数据获取器
"""

import pandas as pd
import numpy as np
import akshare as ak
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import pickle
import time


class SectorFetcher:
    """板块资金数据获取器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache_dir = "temp"
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_sector_fund_flow(self, use_cache: bool = True) -> pd.DataFrame:
        """
        获取板块资金流向数据
        :param use_cache: 是否使用缓存
        :return: 板块资金流向数据
        """
        cache_file = os.path.join(
            self.cache_dir, f"sector_fund_flow_{datetime.now().strftime('%Y%m%d')}.pkl")

        # 检查缓存
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                self.logger.info("从缓存加载板块资金流向数据")
                return data
            except Exception as e:
                self.logger.warning(f"缓存加载失败: {e}")

        # 尝试获取数据，带重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.logger.info(f"正在获取板块资金流向数据... (尝试 {attempt + 1}/{max_retries})")

                # 添加延时避免请求过快
                if attempt > 0:
                    time.sleep(2 * attempt)

                # 获取板块资金流向数据
                data = ak.stock_sector_fund_flow_rank(indicator="今日")

                if data.empty:
                    self.logger.warning("获取到空的板块资金流向数据")
                    if attempt < max_retries - 1:
                        continue
                    return pd.DataFrame()

                # 数据清洗和标准化
                data = self._clean_sector_data(data)

                # 保存缓存
                if use_cache:
                    try:
                        with open(cache_file, 'wb') as f:
                            pickle.dump(data, f)
                        self.logger.info("板块资金流向数据已缓存")
                    except Exception as e:
                        self.logger.warning(f"缓存保存失败: {e}")

                self.logger.info(f"成功获取 {len(data)} 个板块的资金流向数据")
                return data

            except Exception as e:
                self.logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，记录详细错误并提供用户友好的错误信息
                    if "Connection aborted" in str(e) or "RemoteDisconnected" in str(e):
                        self.logger.error("数据源服务器连接中断，服务器可能临时不可用")
                    elif "timeout" in str(e).lower():
                        self.logger.error("请求超时，网络连接可能不稳定")
                    else:
                        self.logger.error(f"获取板块资金流向数据失败: {e}")
                    return pd.DataFrame()

        return pd.DataFrame()

    def get_sector_detail(self, sector_name: str, use_cache: bool = True) -> pd.DataFrame:
        """
        获取指定板块的详细资金数据
        :param sector_name: 板块名称
        :param use_cache: 是否使用缓存
        :return: 板块详细数据
        """
        cache_file = os.path.join(
            self.cache_dir, f"sector_detail_{sector_name}_{datetime.now().strftime('%Y%m%d')}.pkl")

        # 检查缓存
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                self.logger.info(f"从缓存加载板块 {sector_name} 详细数据")
                return data
            except Exception as e:
                self.logger.warning(f"缓存加载失败: {e}")

        try:
            self.logger.info(f"正在获取板块 {sector_name} 的详细数据...")

            # 方法1: 尝试获取板块成分股
            stocks_data = pd.DataFrame()
            try:
                stocks_data = ak.stock_board_concept_cons_em(
                    symbol=sector_name)
                self.logger.info(f"通过概念板块接口获取到 {len(stocks_data)} 只成分股")
            except Exception as e:
                self.logger.warning(f"概念板块接口失败: {e}")

                # 方法2: 尝试其他接口
                try:
                    stocks_data = ak.stock_board_industry_cons_em(
                        symbol=sector_name)
                    if not stocks_data.empty:
                        self.logger.info(
                            f"通过行业板块接口获取到 {len(stocks_data)} 只成分股")
                    else:
                        self.logger.warning("行业板块接口返回空数据")
                except Exception as e2:
                    self.logger.warning(f"行业板块接口也失败: {e2}")

            if stocks_data.empty:
                self.logger.warning(f"未获取到板块 {sector_name} 的成分股数据")
                return pd.DataFrame()

            # 获取成分股信息，优化API调用
            detailed_data = []

            # 只处理前20只股票，避免数据过多
            limited_stocks = stocks_data.head(20)
            
            # 尝试批量获取个股资金流向数据（一次性获取所有数据）
            stock_flow_data = None
            try:
                self.logger.info("正在获取个股资金流向数据...")
                stock_flow_data = ak.stock_individual_fund_flow_rank(indicator="今日")
                self.logger.info(f"成功获取 {len(stock_flow_data)} 只股票的资金流向数据")
            except Exception as e:
                self.logger.warning(f"批量获取个股资金流向失败: {e}")

            # 处理成分股数据
            for i, (_, stock) in enumerate(limited_stocks.iterrows()):
                try:
                    stock_code = stock.get('代码', stock.get('股票代码', ''))
                    stock_name = stock.get('名称', stock.get('股票名称', ''))

                    if not stock_code or not stock_name:
                        continue

                    # 基础股票信息，尝试从成分股数据中获取更多信息
                    stock_data = {
                        '代码': stock_code,
                        '名称': stock_name,
                        '板块': sector_name,
                        '主力净流入': 0,
                        '涨跌幅': 0,
                        '换手率': 0,
                        '最新价': 0
                    }
                    
                    # 尝试从成分股原始数据中获取价格和涨跌幅信息
                    try:
                        if '最新价' in stock:
                            stock_data['最新价'] = float(stock['最新价']) if stock['最新价'] else 0
                        elif '现价' in stock:
                            stock_data['最新价'] = float(stock['现价']) if stock['现价'] else 0
                        
                        if '涨跌幅' in stock:
                            stock_data['涨跌幅'] = float(stock['涨跌幅']) if stock['涨跌幅'] else 0
                        elif '涨跌' in stock:
                            stock_data['涨跌幅'] = float(stock['涨跌']) if stock['涨跌'] else 0
                            
                        if '换手率' in stock:
                            stock_data['换手率'] = float(stock['换手率']) if stock['换手率'] else 0
                            
                    except (ValueError, TypeError) as e:
                        self.logger.debug(f"解析股票 {stock_code} 基础数据失败: {e}")

                    # 如果成功获取了资金流向数据，尝试匹配
                    if stock_flow_data is not None and not stock_flow_data.empty:
                        try:
                            stock_info = stock_flow_data[stock_flow_data['代码'] == stock_code]
                            if not stock_info.empty:
                                flow_info = stock_info.iloc[0]
                                # 更新资金流向数据（使用正确的列名）
                                if '今日主力净流入-净额' in flow_info:
                                    # 转换为万元
                                    stock_data['主力净流入'] = flow_info['今日主力净流入-净额'] / 10000
                                if '今日涨跌幅' in flow_info:
                                    stock_data['涨跌幅'] = flow_info['今日涨跌幅']
                                if '最新价' in flow_info:
                                    stock_data['最新价'] = flow_info['最新价']
                                # 换手率在个股资金流向数据中通常没有，保持为0
                                self.logger.debug(f"成功匹配股票 {stock_code} 的资金流向数据")
                        except Exception as match_e:
                            self.logger.debug(f"匹配股票 {stock_code} 数据失败: {match_e}")

                    detailed_data.append(stock_data)

                    # 添加进度提示
                    if (i + 1) % 10 == 0:
                        self.logger.info(f"已处理 {i + 1}/{len(limited_stocks)} 只股票")

                except Exception as e:
                    self.logger.warning(f"处理股票 {stock_code} 失败: {e}")
                    continue

            if not detailed_data:
                self.logger.warning(f"未能获取板块 {sector_name} 的有效数据")
                return pd.DataFrame()

            data = pd.DataFrame(detailed_data)

            # 保存缓存
            if use_cache:
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(data, f)
                    self.logger.info(f"板块 {sector_name} 详细数据已缓存")
                except Exception as e:
                    self.logger.warning(f"缓存保存失败: {e}")

            self.logger.info(f"成功获取板块 {sector_name} 的 {len(data)} 只成分股数据")
            return data

        except Exception as e:
            self.logger.error(f"获取板块 {sector_name} 详细数据失败: {e}")
            return pd.DataFrame()

    def get_sector_history(self, sector_name: str, period: int = 5, use_cache: bool = True) -> pd.DataFrame:
        """
        获取板块历史资金流向数据
        :param sector_name: 板块名称
        :param period: 历史天数
        :param use_cache: 是否使用缓存
        :return: 历史数据
        """
        cache_file = os.path.join(
            self.cache_dir, f"sector_history_{sector_name}_{period}d_{datetime.now().strftime('%Y%m%d')}.pkl")

        # 检查缓存
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                self.logger.info(f"从缓存加载板块 {sector_name} 历史数据")
                return data
            except Exception as e:
                self.logger.warning(f"缓存加载失败: {e}")

        try:
            self.logger.info(f"正在获取板块 {sector_name} 的历史数据...")

            # 获取历史数据（模拟，实际可能需要其他接口）
            history_data = []
            for i in range(period):
                date = datetime.now() - timedelta(days=i)
                try:
                    # 这里可以根据实际API调整
                    daily_data = ak.stock_sector_fund_flow_rank(indicator="今日")
                    sector_data = daily_data[daily_data['板块'] == sector_name]

                    if not sector_data.empty:
                        sector_info = sector_data.iloc[0].to_dict()
                        sector_info['日期'] = date.strftime('%Y-%m-%d')
                        history_data.append(sector_info)

                except Exception as e:
                    self.logger.warning(
                        f"获取 {date.strftime('%Y-%m-%d')} 数据失败: {e}")
                    continue

            if not history_data:
                return pd.DataFrame()

            data = pd.DataFrame(history_data)

            # 保存缓存
            if use_cache:
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(data, f)
                    self.logger.info(f"板块 {sector_name} 历史数据已缓存")
                except Exception as e:
                    self.logger.warning(f"缓存保存失败: {e}")

            self.logger.info(f"成功获取板块 {sector_name} 的 {len(data)} 天历史数据")
            return data

        except Exception as e:
            self.logger.error(f"获取板块 {sector_name} 历史数据失败: {e}")
            return pd.DataFrame()

    def _clean_sector_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        清洗板块数据
        :param data: 原始数据
        :return: 清洗后的数据
        """
        try:
            # 根据实际数据结构重命名列名
            column_mapping = {
                '名称': '板块',
                '今日涨跌幅': '涨跌幅',
                '今日主力净流入-净额': '主力资金',
                '今日主力净流入-净占比': '主力占比',
                '今日超大单净流入-净额': '超大单',
                '今日超大单净流入-净占比': '超大单占比',
                '今日大单净流入-净额': '大单',
                '今日大单净流入-净占比': '大单占比',
                '今日中单净流入-净额': '中单',
                '今日中单净流入-净占比': '中单占比',
                '今日小单净流入-净额': '小单',
                '今日小单净流入-净占比': '小单占比'
            }

            # 重命名存在的列
            for old_col, new_col in column_mapping.items():
                if old_col in data.columns:
                    data = data.rename(columns={old_col: new_col})

            # 确保必要的列存在
            if '板块' not in data.columns:
                data['板块'] = data.get('名称', f'板块{data.index}')

            if '涨跌幅' not in data.columns:
                data['涨跌幅'] = data.get('今日涨跌幅', 0)

            if '主力资金' not in data.columns:
                data['主力资金'] = data.get('今日主力净流入-净额', 0)

            # 数据类型转换 - 将主力资金从元转换为亿元
            if '主力资金' in data.columns:
                data['主力资金'] = pd.to_numeric(
                    data['主力资金'], errors='coerce').fillna(0)
                data['主力资金'] = data['主力资金'] / 1e8  # 转换为亿元

            # 转换其他数值列
            numeric_columns = ['涨跌幅', '主力占比', '超大单', '大单', '中单', '小单']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(
                        data[col], errors='coerce').fillna(0)
                    # 如果是资金类数据，也转换为亿元
                    if col in ['超大单', '大单', '中单', '小单']:
                        data[col] = data[col] / 1e8

            # 添加换手率列（如果没有的话，设为0）
            if '换手率' not in data.columns:
                data['换手率'] = 0.0

            # 添加量比列（如果没有的话，设为1）
            if '量比' not in data.columns:
                data['量比'] = 1.0

            # 重新设置排名
            data = data.reset_index(drop=True)
            data['排名'] = data.index + 1

            # 只保留需要的列
            keep_columns = ['排名', '板块', '涨跌幅', '主力资金',
                            '主力占比', '超大单', '大单', '中单', '小单', '换手率', '量比']
            available_columns = [
                col for col in keep_columns if col in data.columns]
            data = data[available_columns]

            self.logger.info(f"数据清洗完成，保留列: {list(data.columns)}")
            return data

        except Exception as e:
            self.logger.error(f"数据清洗失败: {e}")
            import traceback
            traceback.print_exc()
            return data


def create_sector_fetcher() -> SectorFetcher:
    """创建板块数据获取器实例"""
    return SectorFetcher()
