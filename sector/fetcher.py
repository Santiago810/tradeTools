"""
板块资金数据获取器
"""

import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import time
from difflib import SequenceMatcher
from config import TUSHARE_TOKEN, index_stock_top_n


class SectorFetcher:
    """板块资金数据获取器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 指数信息缓存
        self._index_stock_cache = None
        self._cache_timestamp = None
        self._cache_duration = 3600*24  # 缓存1小时

        # 初始化TuShare
        self.ts_pro = None
        if TUSHARE_TOKEN:
            try:
                ts.set_token(TUSHARE_TOKEN)
                self.ts_pro = ts.pro_api()
                self.logger.info("TuShare数据源初始化成功")
            except Exception as e:
                self.logger.warning(f"TuShare初始化失败: {e}")
        else:
            self.logger.info("未配置TuShare Token，将使用AKShare作为主要数据源")

    def get_index_stock_info(self) -> Dict[str, str]:
        """
        获取指数股票信息，带缓存机制
        :return: {index_code: display_name} 字典
        """
        try:
            # 检查缓存是否有效
            current_time = time.time()
            if (self._index_stock_cache is not None and
                self._cache_timestamp is not None and
                    current_time - self._cache_timestamp < self._cache_duration):
                self.logger.debug("使用缓存的指数信息")
                return self._index_stock_cache

            self.logger.info("正在获取指数信息...")

            # 获取指数信息
            index_df = ak.index_stock_info()

            if index_df.empty:
                self.logger.warning("获取到空的指数信息")
                return {}

            # 转换为字典格式
            index_stock = {}
            for _, row in index_df.iterrows():
                index_code = row['index_code']
                display_name = row['display_name']
                index_stock[index_code] = display_name

            # 更新缓存
            self._index_stock_cache = index_stock
            self._cache_timestamp = current_time

            self.logger.info(f"成功获取 {len(index_stock)} 个指数信息")
            return index_stock

        except Exception as e:
            self.logger.error(f"获取指数信息失败: {e}")

            # 如果有缓存，返回缓存数据
            if self._index_stock_cache is not None:
                self.logger.warning("获取指数信息失败，使用缓存数据")
                return self._index_stock_cache

            # 返回空字典
            return {}

    def get_sector_fund_flow(self) -> pd.DataFrame:
        """
        获取板块资金流向数据
        :return: 板块资金流向数据
        """
        # 尝试获取数据，带重试机制和多数据源支持
        max_retries = 3

        # 首先尝试AKShare
        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"正在通过AKShare获取板块资金流向数据... (尝试 {attempt + 1}/{max_retries})")

                # 添加延时避免请求过快
                if attempt > 0:
                    time.sleep(2 * attempt)

                # 获取板块资金流向数据
                data = ak.stock_sector_fund_flow_rank(indicator="今日")

                if not data.empty:
                    # 数据清洗和标准化
                    data = self._clean_sector_data(data)

                    self.logger.info(f"AKShare成功获取 {len(data)} 个板块的资金流向数据")
                    return data
                else:
                    self.logger.warning("AKShare获取到空的板块资金流向数据")

            except Exception as e:
                self.logger.warning(f"AKShare第 {attempt + 1} 次尝试失败: {e}")
                if "Connection aborted" in str(e) or "RemoteDisconnected" in str(e):
                    self.logger.warning("AKShare连接中断")
                elif "timeout" in str(e).lower():
                    self.logger.warning("AKShare请求超时")

        # AKShare失败后尝试TuShare
        if self.ts_pro:
            self.logger.info("AKShare获取失败，尝试使用TuShare...")
            try:
                data = self._get_sector_fund_flow_tushare()

                if not data.empty:
                    self.logger.info(f"TuShare成功获取 {len(data)} 个板块的资金流向数据")
                    return data
                else:
                    self.logger.warning("TuShare也未获取到数据")

            except Exception as e:
                self.logger.error(f"TuShare获取板块数据失败: {e}")
        else:
            self.logger.warning("TuShare未配置，无法使用备选数据源")

        # 所有数据源都失败
        self.logger.error("所有数据源都无法获取板块资金流向数据")
        return pd.DataFrame()

    def search_similar_sectors(self, query: str) -> List[Tuple[str, str, float]]:
        """
        搜索相似的板块名称
        :param query: 查询字符串
        :return: [(index_code, display_name, similarity), ...] 按相似度排序
        """
        if not query or not query.strip():
            return []

        query = query.strip()
        similarities = []

        # 获取指数信息
        index_stock = self.get_index_stock_info()

        if not index_stock:
            self.logger.warning("无法获取指数信息，搜索失败")
            return []

        for index_code, display_name in index_stock.items():
            # 计算相似度
            similarity = SequenceMatcher(None, query, display_name).ratio()

            # 如果查询字符串包含在显示名称中，提高相似度
            if query in display_name:
                similarity += 0.3

            # 如果显示名称包含查询字符串，也提高相似度
            if display_name in query:
                similarity += 0.2

            similarities.append((index_code, display_name, similarity))

        # 按相似度排序，取前5个
        similarities.sort(key=lambda x: x[2], reverse=True)
        return similarities[:5]

    def get_index_constituents(self, index_code: str) -> pd.DataFrame:
        """
        获取指数成分股及权重
        :param index_code: 指数代码
        :return: 成分股数据，包含权重信息
        """
        try:
            self.logger.info(f"正在获取指数 {index_code} 的成分股...")

            # 尝试多种方式获取指数成分股
            constituents_data = pd.DataFrame()

            # 方法1: 使用akshare获取指数成分股
            try:
                # 统一使用index_stock_cons接口
                constituents_data = ak.index_stock_cons(symbol=index_code)

                if not constituents_data.empty:
                    self.logger.info(
                        f"通过akshare获取到 {len(constituents_data)} 只成分股")

            except Exception as e:
                self.logger.warning(f"akshare获取指数成分股失败: {e}")

                # 方法2: 使用tushare获取
                if self.ts_pro:
                    try:
                        # 转换指数代码格式
                        ts_code = f"{index_code}.SH" if index_code.startswith(
                            '000') else f"{index_code}.SZ"
                        constituents_data = self.ts_pro.index_weight(
                            index_code=ts_code, trade_date='')

                        if not constituents_data.empty:
                            self.logger.info(
                                f"通过tushare获取到 {len(constituents_data)} 只成分股")

                    except Exception as e2:
                        self.logger.warning(f"tushare获取指数成分股也失败: {e2}")

            if constituents_data.empty:
                self.logger.warning(f"无法获取指数 {index_code} 的成分股数据")
                return pd.DataFrame()

            # 数据标准化处理
            processed_data = self._process_constituents_data(
                constituents_data, index_code)

            # 只取前index_stock_top_n只股票
            if len(processed_data) > index_stock_top_n:
                processed_data = processed_data.head(index_stock_top_n)
                self.logger.info(f"按配置取前 {index_stock_top_n} 只权重股")

            return processed_data

        except Exception as e:
            self.logger.error(f"获取指数 {index_code} 成分股失败: {e}")
            return pd.DataFrame()

    def get_sector_data_by_index(self, index_code: str) -> pd.DataFrame:
        """
        通过指数代码获取板块数据
        :param index_code: 指数代码
        :return: 板块数据
        """
        try:
            # 获取指数成分股
            constituents = self.get_index_constituents(index_code)

            if constituents.empty:
                self.logger.warning(f"指数 {index_code} 没有成分股数据")
                return pd.DataFrame()

            # 获取成分股的实时数据
            stock_data = self._get_stocks_realtime_data(constituents)

            if stock_data.empty:
                self.logger.warning(f"无法获取指数 {index_code} 成分股的实时数据")
                return pd.DataFrame()

            # 按权重融合数据
            sector_data = self._aggregate_sector_data(stock_data, index_code)

            # 如果实时数据为空或无效，尝试使用最新历史数据
            if sector_data.empty or (not sector_data.empty and sector_data.iloc[0].get('涨跌幅', 0) == 0):
                self.logger.info(f"实时数据无效，尝试使用最新历史数据作为备选")
                try:
                    history_data = self.get_sector_history_by_index(
                        index_code, days=5)
                    if not history_data.empty:
                        latest_data = history_data.tail(1).copy()

                        # 获取指数信息
                        index_stock = self.get_index_stock_info()
                        board_name = index_stock.get(
                            index_code, f'指数{index_code}')

                        # 获取历史数据的最新记录
                        latest_record = latest_data.iloc[0]
                        
                        # 获取成分股数据用于详细分析
                        constituents = self.get_index_constituents(index_code)
                        constituents_list = []
                        
                        if not constituents.empty:
                            # 构造简化的成分股数据（基于权重，不包含实时资金流向）
                            for _, stock in constituents.iterrows():
                                stock_info = {
                                    '股票代码': stock['股票代码'],
                                    '股票名称': stock['股票名称'],
                                    '权重': stock['权重'],
                                    '涨跌幅': 0,  # 历史模式下个股涨跌幅设为0
                                    '主力净流入': 0,  # 历史模式下个股资金流向设为0
                                    '最新价': 0,
                                    '换手率': 0
                                }
                                constituents_list.append(stock_info)
                        
                        # 重新构造数据格式以匹配实时数据结构
                        fallback_data = pd.DataFrame([{
                            '板块': board_name,
                            '指数代码': index_code,
                            '涨跌幅': latest_record.get('涨跌幅', 0),
                            '主力资金': latest_record.get('主力净流入', 0) / 10000,  # 转换为亿元
                            '换手率': latest_record.get('换手率', 0),
                            '上涨股票数': latest_record.get('上涨股票数', 0),
                            '总股票数': latest_record.get('总股票数', 0),
                            '上涨比例': latest_record.get('上涨比例', 0),
                            '成分股数据': constituents_list  # 包含成分股基础信息
                        }])

                        self.logger.info(
                            f"使用最新历史数据: {latest_data.iloc[0]['交易日期']}")
                        return fallback_data
                except Exception as e:
                    self.logger.warning(f"获取历史数据备选方案也失败: {e}")

            return sector_data

        except Exception as e:
            self.logger.error(f"通过指数 {index_code} 获取板块数据失败: {e}")
            return pd.DataFrame()

    def _process_constituents_data(self, data: pd.DataFrame, index_code: str) -> pd.DataFrame:
        """
        处理成分股数据
        :param data: 原始成分股数据
        :param index_code: 指数代码
        :return: 处理后的数据
        """
        try:
            processed_data = []

            for _, row in data.iterrows():
                stock_info = {}

                # 提取股票代码
                if '品种代码' in row:
                    stock_info['股票代码'] = row['品种代码']
                elif 'con_code' in row:
                    stock_info['股票代码'] = row['con_code'].split('.')[0]
                elif '代码' in row:
                    stock_info['股票代码'] = row['代码']
                else:
                    continue

                # 提取股票名称
                if '品种名称' in row:
                    stock_info['股票名称'] = row['品种名称']
                elif 'con_name' in row:
                    stock_info['股票名称'] = row['con_name']
                elif '名称' in row:
                    stock_info['股票名称'] = row['名称']
                else:
                    stock_info['股票名称'] = stock_info['股票代码']

                # 提取权重
                if '权重' in row:
                    stock_info['权重'] = float(row['权重']) if row['权重'] else 1.0
                elif 'weight' in row:
                    stock_info['权重'] = float(
                        row['weight']) if row['weight'] else 1.0
                else:
                    stock_info['权重'] = 1.0  # 默认权重

                stock_info['指数代码'] = index_code
                processed_data.append(stock_info)

            if not processed_data:
                return pd.DataFrame()

            result_df = pd.DataFrame(processed_data)

            # 按权重排序
            result_df = result_df.sort_values(
                '权重', ascending=False).reset_index(drop=True)

            # 权重归一化
            total_weight = result_df['权重'].sum()
            if total_weight > 0:
                result_df['权重'] = result_df['权重'] / total_weight

            return result_df

        except Exception as e:
            self.logger.error(f"处理成分股数据失败: {e}")
            return pd.DataFrame()

    def _get_stocks_realtime_data(self, constituents: pd.DataFrame) -> pd.DataFrame:
        """
        获取成分股实时数据
        :param constituents: 成分股列表
        :return: 实时数据
        """
        try:
            stock_data = []

            # 批量获取股票实时数据
            stock_codes = constituents['股票代码'].tolist()

            # 尝试批量获取资金流向数据，带重试机制
            fund_flow_data = pd.DataFrame()
            for attempt in range(3):
                try:
                    fund_flow_data = ak.stock_individual_fund_flow_rank(
                        indicator="今日")
                    self.logger.info(f"获取到 {len(fund_flow_data)} 只股票的资金流向数据")
                    break
                except Exception as e:
                    self.logger.warning(
                        f"批量获取资金流向数据失败 (尝试 {attempt + 1}/3): {e}")
                    if attempt < 2:
                        time.sleep(2)

            # 尝试批量获取股票基本信息，带重试机制
            stock_info_data = pd.DataFrame()
            for attempt in range(3):
                try:
                    stock_info_data = ak.stock_zh_a_spot_em()
                    self.logger.info(f"获取到 {len(stock_info_data)} 只股票的基本信息")
                    break
                except Exception as e:
                    self.logger.warning(
                        f"批量获取股票基本信息失败 (尝试 {attempt + 1}/3): {e}")
                    if attempt < 2:
                        time.sleep(2)

            for _, constituent in constituents.iterrows():
                stock_code = constituent['股票代码']
                stock_name = constituent['股票名称']
                weight = constituent['权重']

                stock_record = {
                    '股票代码': stock_code,
                    '股票名称': stock_name,
                    '权重': weight,
                    '最新价': 0,
                    '涨跌幅': 0,
                    '主力净流入': 0,
                    '换手率': 0,
                    '成交量': 0,
                    '成交额': 0
                }

                # 从资金流向数据中匹配
                if not fund_flow_data.empty:
                    flow_match = fund_flow_data[fund_flow_data['代码']
                                                == stock_code]
                    if not flow_match.empty:
                        flow_info = flow_match.iloc[0]
                        if '今日主力净流入-净额' in flow_info:
                            # 转万元
                            stock_record['主力净流入'] = flow_info['今日主力净流入-净额'] / 10000
                        if '今日涨跌幅' in flow_info:
                            stock_record['涨跌幅'] = flow_info['今日涨跌幅']
                        if '最新价' in flow_info:
                            stock_record['最新价'] = flow_info['最新价']

                # 从股票基本信息中匹配
                if not stock_info_data.empty:
                    info_match = stock_info_data[stock_info_data['代码']
                                                 == stock_code]
                    if not info_match.empty:
                        info = info_match.iloc[0]
                        if '最新价' in info and stock_record['最新价'] == 0:
                            stock_record['最新价'] = info['最新价']
                        if '涨跌幅' in info and stock_record['涨跌幅'] == 0:
                            stock_record['涨跌幅'] = info['涨跌幅']
                        if '换手率' in info:
                            stock_record['换手率'] = info['换手率']
                        if '成交量' in info:
                            stock_record['成交量'] = info['成交量']
                        if '成交额' in info:
                            stock_record['成交额'] = info['成交额']

                stock_data.append(stock_record)

            return pd.DataFrame(stock_data)

        except Exception as e:
            self.logger.error(f"获取成分股实时数据失败: {e}")
            return pd.DataFrame()

    def _aggregate_sector_data(self, stock_data: pd.DataFrame, index_code: str) -> pd.DataFrame:
        """
        按权重聚合板块数据
        :param stock_data: 股票数据
        :param index_code: 指数代码
        :return: 聚合后的板块数据
        """
        try:
            if stock_data.empty:
                return pd.DataFrame()

            # 计算加权平均
            total_weight = stock_data['权重'].sum()
            if total_weight == 0:
                return pd.DataFrame()

            # 加权计算各项指标
            weighted_change = (
                stock_data['涨跌幅'] * stock_data['权重']).sum() / total_weight
            weighted_turnover = (
                stock_data['换手率'] * stock_data['权重']).sum() / total_weight

            # 资金流向按权重加权
            total_fund_flow = (stock_data['主力净流入'] * stock_data['权重']).sum()

            # 计算板块强度指标
            rising_stocks = len(stock_data[stock_data['涨跌幅'] > 0])
            total_stocks = len(stock_data)
            rising_ratio = rising_stocks / total_stocks if total_stocks > 0 else 0

            # 获取指数信息
            index_stock = self.get_index_stock_info()

            # 构建板块数据
            sector_record = {
                '板块': index_stock.get(index_code, f'指数{index_code}'),
                '指数代码': index_code,
                '涨跌幅': weighted_change,
                '主力资金': total_fund_flow / 10000,  # 转换为亿元
                '换手率': weighted_turnover,
                '上涨股票数': rising_stocks,
                '总股票数': total_stocks,
                '上涨比例': rising_ratio * 100,
                '成分股数据': stock_data.to_dict('records')
            }

            return pd.DataFrame([sector_record])

        except Exception as e:
            self.logger.error(f"聚合板块数据失败: {e}")
            return pd.DataFrame()

    def get_sector_detail(self, sector_name: str) -> pd.DataFrame:
        """
        获取指定板块的详细资金数据
        :param sector_name: 板块名称
        :return: 板块详细数据
        """
        # 检查sector_name是否有效
        if not sector_name or sector_name is None:
            self.logger.error("板块名称为空，无法获取详细数据")
            return pd.DataFrame()

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
                self.logger.warning(f"AKShare未获取到板块 {sector_name} 的成分股数据")

                # 尝试使用TuShare获取
                if self.ts_pro:
                    self.logger.info(f"尝试使用TuShare获取板块 {sector_name} 的成分股...")
                    try:
                        stocks_data = self._get_sector_stocks_tushare(
                            sector_name)
                        if not stocks_data.empty:
                            self.logger.info(
                                f"TuShare成功获取板块 {sector_name} 的 {len(stocks_data)} 只成分股")
                        else:
                            self.logger.warning(
                                f"TuShare也未获取到板块 {sector_name} 的成分股数据")
                            return pd.DataFrame()
                    except Exception as e:
                        self.logger.error(
                            f"TuShare获取板块 {sector_name} 成分股失败: {e}")
                        return pd.DataFrame()
                else:
                    return pd.DataFrame()

            # 获取成分股信息，优化API调用
            detailed_data = []

            # 只处理前20只股票，避免数据过多
            limited_stocks = stocks_data.head(20)

            # 尝试批量获取个股资金流向数据（一次性获取所有数据）
            stock_flow_data = None
            try:
                self.logger.info("正在获取个股资金流向数据...")
                stock_flow_data = ak.stock_individual_fund_flow_rank(
                    indicator="今日")
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
                            stock_data['最新价'] = float(
                                stock['最新价']) if stock['最新价'] else 0
                        elif '现价' in stock:
                            stock_data['最新价'] = float(
                                stock['现价']) if stock['现价'] else 0

                        if '涨跌幅' in stock:
                            stock_data['涨跌幅'] = float(
                                stock['涨跌幅']) if stock['涨跌幅'] else 0
                        elif '涨跌' in stock:
                            stock_data['涨跌幅'] = float(
                                stock['涨跌']) if stock['涨跌'] else 0

                        if '换手率' in stock:
                            stock_data['换手率'] = float(
                                stock['换手率']) if stock['换手率'] else 0

                    except (ValueError, TypeError) as e:
                        self.logger.debug(f"解析股票 {stock_code} 基础数据失败: {e}")

                    # 如果成功获取了资金流向数据，尝试匹配
                    if stock_flow_data is not None and not stock_flow_data.empty:
                        try:
                            stock_info = stock_flow_data[stock_flow_data['代码']
                                                         == stock_code]
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
                                self.logger.debug(
                                    f"成功匹配股票 {stock_code} 的资金流向数据")
                        except Exception as match_e:
                            self.logger.debug(
                                f"匹配股票 {stock_code} 数据失败: {match_e}")

                    detailed_data.append(stock_data)

                    # 添加进度提示
                    if (i + 1) % 10 == 0:
                        self.logger.info(
                            f"已处理 {i + 1}/{len(limited_stocks)} 只股票")

                except Exception as e:
                    self.logger.warning(f"处理股票 {stock_code} 失败: {e}")
                    continue

            if not detailed_data:
                self.logger.warning(f"未能获取板块 {sector_name} 的有效数据")
                return pd.DataFrame()

            data = pd.DataFrame(detailed_data)

            self.logger.info(f"成功获取板块 {sector_name} 的 {len(data)} 只成分股数据")
            return data

        except Exception as e:
            self.logger.error(f"获取板块 {sector_name} 详细数据失败: {e}")
            return pd.DataFrame()

    def get_sector_history_by_index(self, index_code: str, days: int = 60) -> pd.DataFrame:
        """
        获取指数板块的历史数据（通过成分股权重融合）
        :param index_code: 指数代码
        :param days: 历史天数，默认60天（约2个月）
        :return: 历史数据DataFrame
        """
        try:
            self.logger.info(f"正在获取指数 {index_code} 的历史数据，回溯 {days} 天...")

            # 获取指数成分股
            constituents = self.get_index_constituents(index_code)
            if constituents.empty:
                self.logger.warning(f"指数 {index_code} 没有成分股数据")
                return pd.DataFrame()

            # 获取日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 获取成分股历史数据
            stock_history_data = self._get_stocks_history_data(
                constituents, start_date, end_date)

            if stock_history_data.empty:
                self.logger.warning(f"无法获取指数 {index_code} 成分股的历史数据")
                return pd.DataFrame()

            # 按日期聚合数据
            sector_history = self._aggregate_daily_sector_data(
                stock_history_data, index_code)

            return sector_history

        except Exception as e:
            self.logger.error(f"获取指数 {index_code} 历史数据失败: {e}")
            return pd.DataFrame()

    def _get_stocks_history_data(self, constituents: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        获取成分股历史数据
        :param constituents: 成分股列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 历史数据DataFrame
        """
        try:
            all_stock_data = []
            stock_codes = constituents['股票代码'].tolist()

            self.logger.info(f"正在获取 {len(stock_codes)} 只成分股的历史数据...")

            # 为了避免API限制，分批处理股票
            batch_size = 5  # 每批处理5只股票
            for i in range(0, len(stock_codes), batch_size):
                batch_codes = stock_codes[i:i+batch_size]

                for stock_code in batch_codes:
                    try:
                        # 获取股票权重
                        stock_weight = constituents[constituents['股票代码']
                                                    == stock_code]['权重'].iloc[0]
                        stock_name = constituents[constituents['股票代码']
                                                  == stock_code]['股票名称'].iloc[0]

                        # 获取股票历史数据
                        stock_history = self._get_single_stock_history(
                            stock_code, start_date, end_date)

                        if not stock_history.empty:
                            # 添加权重和股票信息
                            stock_history['股票代码'] = stock_code
                            stock_history['股票名称'] = stock_name
                            stock_history['权重'] = stock_weight
                            all_stock_data.append(stock_history)

                        # 添加延时避免API限制
                        time.sleep(0.1)

                    except Exception as e:
                        self.logger.warning(f"获取股票 {stock_code} 历史数据失败: {e}")
                        continue

                # 批次间延时和进度报告
                if i + batch_size < len(stock_codes):
                    time.sleep(1)
                    success_count = len(all_stock_data)
                    processed_count = min(i + batch_size, len(stock_codes))
                    self.logger.info(
                        f"已处理 {processed_count}/{len(stock_codes)} 只股票，成功获取 {success_count} 只")

            if not all_stock_data:
                return pd.DataFrame()

            # 合并所有股票数据
            combined_data = pd.concat(all_stock_data, ignore_index=True)

            self.logger.info(f"成功获取 {len(all_stock_data)} 只股票的历史数据")
            return combined_data

        except Exception as e:
            self.logger.error(f"获取成分股历史数据失败: {e}")
            return pd.DataFrame()

    def _get_single_stock_history(self, stock_code: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        获取单只股票的历史数据（包含资金流向）
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 股票历史数据
        """
        try:
            # 方法1: 获取股票历史资金流向数据（包含价格和资金流向）
            stock_data = pd.DataFrame()

            # 同时获取资金流向数据和基础数据，然后合并
            fund_flow_data = pd.DataFrame()
            basic_data = pd.DataFrame()

            # 1.1 获取资金流向数据
            try:
                market = "sz" if stock_code.startswith(
                    ('0', '2', '3')) else "sh"
                fund_flow_raw = ak.stock_individual_fund_flow(
                    stock=stock_code, market=market)

                if not fund_flow_raw.empty:
                    # 过滤日期范围
                    fund_flow_raw['日期'] = pd.to_datetime(fund_flow_raw['日期'])
                    mask = (fund_flow_raw['日期'] >= start_date) & (
                        fund_flow_raw['日期'] <= end_date)
                    fund_flow_data = fund_flow_raw[mask].copy()
                    self.logger.debug(
                        f"获取股票 {stock_code} 资金流向数据: {len(fund_flow_data)} 天")
                else:
                    self.logger.debug(f"股票 {stock_code} 资金流向数据为空")

            except Exception as e:
                self.logger.debug(f"股票 {stock_code} 资金流向API调用失败: {e}")
                # 常见的API失败原因，不需要记录为错误

            # 1.2 获取基础数据（包含换手率、成交量等）
            try:
                basic_raw = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    adjust=""
                )

                if not basic_raw.empty:
                    basic_data = basic_raw.copy()
                    basic_data['日期'] = pd.to_datetime(basic_data['日期'])
                    self.logger.debug(
                        f"获取股票 {stock_code} 基础数据: {len(basic_data)} 天")

            except Exception as e:
                self.logger.debug(f"获取股票 {stock_code} 基础数据失败: {e}")

            # 1.3 合并数据
            if not fund_flow_data.empty and not basic_data.empty:
                # 合并两个数据源
                stock_data = self._merge_fund_flow_and_basic_data(
                    fund_flow_data, basic_data)
                if not stock_data.empty:
                    self.logger.debug(
                        f"成功合并股票 {stock_code} 的完整历史数据: {len(stock_data)} 天")
                    return stock_data

            # 1.4 如果合并失败，优先使用资金流向数据
            elif not fund_flow_data.empty:
                stock_data = self._standardize_fund_flow_history_columns(
                    fund_flow_data)
                self.logger.debug(
                    f"使用资金流向数据获取股票 {stock_code}: {len(stock_data)} 天")
                return stock_data

            # 1.5 如果资金流向数据也没有，使用基础数据
            elif not basic_data.empty:
                stock_data = self._standardize_stock_history_columns(
                    basic_data)
                self.logger.debug(
                    f"使用基础历史数据获取股票 {stock_code}: {len(stock_data)} 天")
                return stock_data

            # 1.6 如果基础数据也失败，尝试简化的历史数据获取
            else:
                self.logger.debug(f"尝试简化方式获取股票 {stock_code} 历史数据")
                try:
                    # 使用更简单的接口
                    simple_data = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=start_date.strftime('%Y%m%d'),
                        end_date=end_date.strftime('%Y%m%d')
                    )

                    if not simple_data.empty:
                        stock_data = self._standardize_stock_history_columns(
                            simple_data)
                        self.logger.debug(
                            f"简化方式成功获取股票 {stock_code}: {len(stock_data)} 天")
                        return stock_data

                except Exception as e:
                    self.logger.debug(f"简化方式获取股票 {stock_code} 也失败: {e}")

            # 方法2: 使用tushare获取（如果可用）
            if self.ts_pro:
                try:
                    ts_code = f"{stock_code}.SH" if stock_code.startswith(
                        ('6', '9')) else f"{stock_code}.SZ"
                    ts_data = self.ts_pro.daily(
                        ts_code=ts_code,
                        start_date=start_date.strftime('%Y%m%d'),
                        end_date=end_date.strftime('%Y%m%d')
                    )

                    if not ts_data.empty:
                        stock_data = self._standardize_tushare_history_columns(
                            ts_data)
                        self.logger.debug(
                            f"使用tushare获取股票 {stock_code}: {len(stock_data)} 天")
                        return stock_data

                except Exception as e:
                    self.logger.debug(f"tushare获取股票 {stock_code} 历史数据失败: {e}")

            return stock_data

        except Exception as e:
            self.logger.debug(f"获取股票 {stock_code} 历史数据失败: {e}")
            return pd.DataFrame()

    def _standardize_fund_flow_history_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        标准化资金流向历史数据列名
        :param data: 原始数据
        :return: 标准化后的数据
        """
        try:
            # 资金流向历史数据的列名映射
            column_mapping = {
                '日期': '交易日期',
                '收盘价': '收盘价',
                '涨跌幅': '涨跌幅',
                '主力净流入-净额': '主力净流入',
                '主力净流入-净占比': '主力净流入占比',
                '超大单净流入-净额': '超大单净流入',
                '超大单净流入-净占比': '超大单净流入占比',
                '大单净流入-净额': '大单净流入',
                '大单净流入-净占比': '大单净流入占比',
                '中单净流入-净额': '中单净流入',
                '中单净流入-净占比': '中单净流入占比',
                '小单净流入-净额': '小单净流入',
                '小单净流入-净占比': '小单净流入占比'
            }

            # 重命名列
            for old_col, new_col in column_mapping.items():
                if old_col in data.columns:
                    data = data.rename(columns={old_col: new_col})

            # 确保日期格式正确
            if '交易日期' in data.columns:
                data['交易日期'] = pd.to_datetime(data['交易日期'])

            # 数值列转换
            numeric_columns = ['收盘价', '涨跌幅', '主力净流入', '主力净流入占比',
                               '超大单净流入', '大单净流入', '中单净流入', '小单净流入']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(
                        data[col], errors='coerce').fillna(0)

            # 添加缺失的列（设置默认值）
            if '开盘价' not in data.columns:
                data['开盘价'] = data.get('收盘价', 0)
            if '最高价' not in data.columns:
                data['最高价'] = data.get('收盘价', 0)
            if '最低价' not in data.columns:
                data['最低价'] = data.get('收盘价', 0)
            if '成交量' not in data.columns:
                data['成交量'] = 0
            if '成交额' not in data.columns:
                data['成交额'] = 0
            if '换手率' not in data.columns:
                data['换手率'] = 0

            # 将主力净流入从元转换为万元（如果需要）
            if '主力净流入' in data.columns:
                # 检查数值大小，如果是元为单位则转换为万元
                # max_value = data['主力净流入'].abs().max()
                # if max_value > 100000:  # 如果最大值超过10万，认为是以元为单位
                data['主力净流入'] = data['主力净流入'] / 10000

            return data

        except Exception as e:
            self.logger.error(f"标准化资金流向历史数据列名失败: {e}")
            return data

    def _merge_fund_flow_and_basic_data(self, fund_flow_data: pd.DataFrame, basic_data: pd.DataFrame) -> pd.DataFrame:
        """
        合并资金流向数据和基础数据
        :param fund_flow_data: 资金流向数据
        :param basic_data: 基础数据
        :return: 合并后的数据
        """
        try:
            # 标准化资金流向数据
            fund_flow_std = self._standardize_fund_flow_history_columns(
                fund_flow_data.copy())

            # 标准化基础数据
            basic_std = self._standardize_stock_history_columns(
                basic_data.copy())

            # 按日期合并
            merged_data = pd.merge(
                fund_flow_std,
                basic_std[['交易日期', '成交量', '成交额', '换手率', '开盘价', '最高价', '最低价']],
                on='交易日期',
                how='left',
                suffixes=('', '_basic')
            )

            # 填充缺失的数据，优先使用基础数据中的完整信息
            for col in ['换手率', '成交量', '成交额', '开盘价', '最高价', '最低价']:
                basic_col = f'{col}_basic'
                if basic_col in merged_data.columns:
                    # 如果原列不存在或为0，使用基础数据填充
                    if col not in merged_data.columns:
                        merged_data[col] = merged_data[basic_col]
                    else:
                        merged_data[col] = merged_data[col].fillna(
                            merged_data[basic_col])
                        # 如果原数据为0，也用基础数据替换
                        zero_mask = (merged_data[col] == 0) & (
                            merged_data[basic_col] != 0)
                        if zero_mask.any():
                            # 确保数据类型兼容
                            merged_data[col] = merged_data[col].astype(float)
                            merged_data.loc[zero_mask, col] = merged_data.loc[zero_mask, basic_col].astype(
                                float)

                    # 删除临时列
                    merged_data = merged_data.drop(
                        basic_col, axis=1, errors='ignore')

            self.logger.debug(f"成功合并数据，最终列名: {list(merged_data.columns)}")
            return merged_data

        except Exception as e:
            self.logger.error(f"合并资金流向和基础数据失败: {e}")
            # 如果合并失败，返回资金流向数据
            return self._standardize_fund_flow_history_columns(fund_flow_data)

    def _standardize_stock_history_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        标准化akshare股票历史数据列名
        :param data: 原始数据
        :return: 标准化后的数据
        """
        try:
            # akshare的列名映射
            column_mapping = {
                '日期': '交易日期',
                '开盘': '开盘价',
                '收盘': '收盘价',
                '最高': '最高价',
                '最低': '最低价',
                '成交量': '成交量',
                '成交额': '成交额',
                '振幅': '振幅',
                '涨跌幅': '涨跌幅',
                '涨跌额': '涨跌额',
                '换手率': '换手率'
            }

            # 重命名列
            for old_col, new_col in column_mapping.items():
                if old_col in data.columns:
                    data = data.rename(columns={old_col: new_col})

            # 确保日期格式正确
            if '交易日期' in data.columns:
                data['交易日期'] = pd.to_datetime(data['交易日期'])

            # 数值列转换
            numeric_columns = ['开盘价', '收盘价', '最高价',
                               '最低价', '成交量', '成交额', '涨跌幅', '换手率']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(
                        data[col], errors='coerce').fillna(0)

            # 添加缺失的列
            if '主力净流入' not in data.columns:
                data['主力净流入'] = 0  # 历史数据中通常没有资金流向数据
                self.logger.debug("基础历史数据不包含资金流向信息，已设置默认值")

            return data

        except Exception as e:
            self.logger.error(f"标准化股票历史数据列名失败: {e}")
            return data

    def _standardize_tushare_history_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        标准化tushare股票历史数据列名
        :param data: 原始数据
        :return: 标准化后的数据
        """
        try:
            # tushare的列名映射
            column_mapping = {
                'trade_date': '交易日期',
                'open': '开盘价',
                'close': '收盘价',
                'high': '最高价',
                'low': '最低价',
                'vol': '成交量',
                'amount': '成交额',
                'pct_chg': '涨跌幅',
                'change': '涨跌额'
            }

            # 重命名列
            for old_col, new_col in column_mapping.items():
                if old_col in data.columns:
                    data = data.rename(columns={old_col: new_col})

            # 日期格式转换
            if '交易日期' in data.columns:
                data['交易日期'] = pd.to_datetime(data['交易日期'], format='%Y%m%d')

            # 数值列转换
            numeric_columns = ['开盘价', '收盘价', '最高价',
                               '最低价', '成交量', '成交额', '涨跌幅', '涨跌额']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(
                        data[col], errors='coerce').fillna(0)

            # 添加缺失的列
            if '换手率' not in data.columns:
                data['换手率'] = 0
            if '主力净流入' not in data.columns:
                data['主力净流入'] = 0

            return data

        except Exception as e:
            self.logger.error(f"标准化tushare历史数据列名失败: {e}")
            return data

    def _aggregate_daily_sector_data(self, stock_history_data: pd.DataFrame, index_code: str) -> pd.DataFrame:
        """
        按日期聚合板块数据
        :param stock_history_data: 股票历史数据
        :param index_code: 指数代码
        :return: 聚合后的板块历史数据
        """
        try:
            if stock_history_data.empty:
                return pd.DataFrame()

            # 按日期分组聚合
            daily_data = []

            # 获取所有交易日期
            dates = sorted(stock_history_data['交易日期'].unique())

            for date in dates:
                # 获取当日所有股票数据
                daily_stocks = stock_history_data[stock_history_data['交易日期'] == date]

                if daily_stocks.empty:
                    continue

                # 计算权重总和（用于归一化）
                total_weight = daily_stocks['权重'].sum()
                if total_weight == 0:
                    continue

                # 按权重计算加权指标
                weighted_change = (
                    daily_stocks['涨跌幅'] * daily_stocks['权重']).sum() / total_weight
                weighted_turnover = (
                    daily_stocks['换手率'] * daily_stocks['权重']).sum() / total_weight

                # 成交量和成交额按权重加权
                weighted_volume = (
                    daily_stocks['成交量'] * daily_stocks['权重']).sum()
                weighted_amount = (
                    daily_stocks['成交额'] * daily_stocks['权重']).sum()

                # 资金流向按权重加权（如果有数据）
                weighted_fund_flow = (
                    daily_stocks['主力净流入'] * daily_stocks['权重']).sum()

                # 计算板块强度指标
                rising_stocks = len(daily_stocks[daily_stocks['涨跌幅'] > 0])
                total_stocks = len(daily_stocks)
                rising_ratio = rising_stocks / total_stocks if total_stocks > 0 else 0

                # 获取指数名称
                index_stock = self.get_index_stock_info()
                sector_name = index_stock.get(index_code, f'指数{index_code}')

                # 构建当日板块数据
                daily_record = {
                    '交易日期': date,
                    '板块名称': sector_name,
                    '指数代码': index_code,
                    '涨跌幅': weighted_change,
                    '换手率': weighted_turnover,
                    '成交量': weighted_volume,
                    '成交额': weighted_amount,
                    '主力净流入': weighted_fund_flow,
                    '上涨股票数': rising_stocks,
                    '总股票数': total_stocks,
                    '上涨比例': rising_ratio * 100,
                    '平均价格': (daily_stocks['收盘价'] * daily_stocks['权重']).sum() / total_weight
                }

                daily_data.append(daily_record)

            if not daily_data:
                return pd.DataFrame()

            # 转换为DataFrame并排序
            result_df = pd.DataFrame(daily_data)
            result_df = result_df.sort_values('交易日期').reset_index(drop=True)

            self.logger.info(f"成功聚合 {len(result_df)} 天的板块历史数据")
            return result_df

        except Exception as e:
            self.logger.error(f"聚合板块历史数据失败: {e}")
            return pd.DataFrame()

    def get_sector_history(self, sector_name: str, period: int = 5) -> pd.DataFrame:
        """
        获取板块历史资金流向数据（保留原方法以兼容性）
        :param sector_name: 板块名称
        :param period: 历史天数
        :return: 历史数据
        """
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

    def _get_sector_fund_flow_tushare(self) -> pd.DataFrame:
        """
        使用TuShare获取板块资金流向数据
        :return: 板块资金流向数据
        """
        if not self.ts_pro:
            self.logger.warning("TuShare未初始化，无法获取数据")
            return pd.DataFrame()

        try:
            self.logger.info("正在通过TuShare获取板块资金流向数据...")

            # 使用最基础的免费接口 - 只获取股票基本信息
            stock_basic = self.ts_pro.stock_basic(exchange='', list_status='L',
                                                  fields='ts_code,symbol,name,industry')

            if stock_basic.empty:
                self.logger.warning("TuShare股票基本信息为空")
                return pd.DataFrame()

            # 按行业分组，创建基础板块数据
            processed_data = []
            industries = stock_basic['industry'].value_counts().head(
                30)  # 取前30个行业

            for i, (industry, count) in enumerate(industries.items()):
                if count >= 3:  # 至少3只股票的行业
                    sector_data = {
                        '排名': i + 1,
                        '板块': industry,
                        '涨跌幅': 0,  # 免费版本无法获取实时涨跌幅
                        '主力资金': 0,  # 免费版本无法获取资金流向
                        '主力占比': 0,
                        '超大单': 0,
                        '大单': 0,
                        '中单': 0,
                        '小单': 0,
                        '换手率': 0,
                        '量比': 1.0
                    }
                    processed_data.append(sector_data)

            if not processed_data:
                self.logger.warning("TuShare未获取到有效的板块数据")
                return pd.DataFrame()

            result_df = pd.DataFrame(processed_data)

            # 按主力资金排序
            result_df = result_df.sort_values(
                '主力资金', ascending=False).reset_index(drop=True)
            result_df['排名'] = result_df.index + 1

            self.logger.info(f"TuShare成功获取 {len(result_df)} 个板块的资金流向数据")
            return result_df

        except Exception as e:
            self.logger.error(f"TuShare获取板块资金流向数据失败: {e}")
            return pd.DataFrame()

    def _get_sector_stocks_tushare(self, sector_name: str) -> pd.DataFrame:
        """
        使用TuShare获取板块成分股
        :param sector_name: 板块名称
        :return: 成分股数据
        """
        if not self.ts_pro:
            return pd.DataFrame()

        # 检查sector_name是否有效
        if not sector_name or sector_name is None or str(sector_name).strip() == '':
            self.logger.warning("板块名称为空，无法获取成分股")
            return pd.DataFrame()

        try:
            self.logger.info(f"正在通过TuShare获取板块 {sector_name} 的成分股...")

            # 使用免费接口 - 通过行业名称匹配
            stock_basic = self.ts_pro.stock_basic(exchange='', list_status='L',
                                                  fields='ts_code,symbol,name,industry')

            if stock_basic.empty:
                self.logger.warning("TuShare股票基本信息为空")
                return pd.DataFrame()

            # 查找匹配的行业 - 添加空值检查
            matching_stocks = pd.DataFrame()
            try:
                # 确保sector_name是字符串且不为空
                if sector_name and isinstance(sector_name, str):
                    matching_stocks = stock_basic[stock_basic['industry'].str.contains(
                        sector_name, na=False)]
                else:
                    self.logger.warning(f"板块名称格式无效: {sector_name}")
                    return pd.DataFrame()
            except Exception as e:
                self.logger.warning(f"行业名称匹配失败: {e}")
                return pd.DataFrame()

            if matching_stocks.empty:
                # 尝试模糊匹配
                for industry in stock_basic['industry'].unique():
                    # 检查industry是否为None或空值
                    if industry is not None and sector_name is not None:
                        if sector_name in industry or industry in sector_name:
                            matching_stocks = stock_basic[stock_basic['industry'] == industry]
                            break

                if matching_stocks.empty:
                    self.logger.warning(f"TuShare未找到匹配的行业: {sector_name}")
                    return pd.DataFrame()

            # 只使用基本信息，避免API限制
            result_data = []

            for _, stock in matching_stocks.head(20).iterrows():
                stock_data = {
                    '代码': stock['ts_code'].split('.')[0],  # 去掉后缀
                    '名称': stock['name'],
                    '板块': sector_name,
                    '主力净流入': 0,  # TuShare免费版本没有资金流向数据
                    '涨跌幅': 0,      # 免费版本无法获取实时涨跌幅
                    '换手率': 0,      # 免费版本没有换手率
                    '最新价': 0       # 免费版本无法获取实时价格
                }
                result_data.append(stock_data)

            result_df = pd.DataFrame(result_data)
            self.logger.info(
                f"TuShare成功获取板块 {sector_name} 的 {len(result_df)} 只成分股")
            return result_df

        except Exception as e:
            self.logger.error(f"TuShare获取板块 {sector_name} 成分股失败: {e}")
            return pd.DataFrame()


def create_sector_fetcher() -> SectorFetcher:
    """创建板块数据获取器实例"""
    return SectorFetcher()
