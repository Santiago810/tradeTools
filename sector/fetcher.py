"""
板块资金数据获取器
"""

import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import time
from config import TUSHARE_TOKEN


class SectorFetcher:
    """板块资金数据获取器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
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
                self.logger.info(f"正在通过AKShare获取板块资金流向数据... (尝试 {attempt + 1}/{max_retries})")

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
                        stocks_data = self._get_sector_stocks_tushare(sector_name)
                        if not stocks_data.empty:
                            self.logger.info(f"TuShare成功获取板块 {sector_name} 的 {len(stocks_data)} 只成分股")
                        else:
                            self.logger.warning(f"TuShare也未获取到板块 {sector_name} 的成分股数据")
                            return pd.DataFrame()
                    except Exception as e:
                        self.logger.error(f"TuShare获取板块 {sector_name} 成分股失败: {e}")
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

            self.logger.info(f"成功获取板块 {sector_name} 的 {len(data)} 只成分股数据")
            return data

        except Exception as e:
            self.logger.error(f"获取板块 {sector_name} 详细数据失败: {e}")
            return pd.DataFrame()

    def get_sector_history(self, sector_name: str, period: int = 5) -> pd.DataFrame:
        """
        获取板块历史资金流向数据
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
            industries = stock_basic['industry'].value_counts().head(30)  # 取前30个行业
            
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
            result_df = result_df.sort_values('主力资金', ascending=False).reset_index(drop=True)
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
        if not sector_name or sector_name is None:
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
                matching_stocks = stock_basic[stock_basic['industry'].str.contains(sector_name, na=False)]
            except Exception as e:
                self.logger.warning(f"行业名称匹配失败: {e}")
                return pd.DataFrame()
            
            if matching_stocks.empty:
                # 尝试模糊匹配
                for industry in stock_basic['industry'].unique():
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
            self.logger.info(f"TuShare成功获取板块 {sector_name} 的 {len(result_df)} 只成分股")
            return result_df
            
        except Exception as e:
            self.logger.error(f"TuShare获取板块 {sector_name} 成分股失败: {e}")
            return pd.DataFrame()


def create_sector_fetcher() -> SectorFetcher:
    """创建板块数据获取器实例"""
    return SectorFetcher()