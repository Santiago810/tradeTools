"""
板块资金数据处理器
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional

class SectorProcessor:
    """板块资金数据处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_sector_data(self, sector_data: pd.DataFrame) -> Dict[str, Any]:
        """
        处理板块资金数据
        :param sector_data: 板块数据
        :return: 处理结果
        """
        try:
            if sector_data.empty:
                return {}
            
            # 基础统计
            total_sectors = len(sector_data)
            
            # 资金流向统计
            inflow_sectors = len(sector_data[sector_data['主力资金'] > 0])
            outflow_sectors = len(sector_data[sector_data['主力资金'] < 0])
            
            # 涨跌统计
            rising_sectors = len(sector_data[sector_data['涨跌幅'] > 0])
            falling_sectors = len(sector_data[sector_data['涨跌幅'] < 0])
            
            # 资金流向排行 - 只显示真正的流入和流出
            # 资金流入榜：只包含主力资金>0的板块
            inflow_sectors_data = sector_data[sector_data['主力资金'] > 0]
            if not inflow_sectors_data.empty:
                top_inflow = inflow_sectors_data.nlargest(10, '主力资金')[['板块', '主力资金', '涨跌幅', '换手率']].to_dict('records')
            else:
                top_inflow = []
            
            # 资金流出榜：只包含主力资金<0的板块
            outflow_sectors_data = sector_data[sector_data['主力资金'] < 0]
            if not outflow_sectors_data.empty:
                top_outflow = outflow_sectors_data.nsmallest(10, '主力资金')[['板块', '主力资金', '涨跌幅', '换手率']].to_dict('records')
            else:
                top_outflow = []
            
            # 涨幅排行
            top_rising = sector_data.nlargest(10, '涨跌幅')[['板块', '涨跌幅', '主力资金', '换手率']].to_dict('records')
            top_falling = sector_data.nsmallest(10, '涨跌幅')[['板块', '涨跌幅', '主力资金', '换手率']].to_dict('records')
            
            # 活跃度排行（按换手率，如果没有换手率数据则按主力资金排序）
            if '换手率' in sector_data.columns and sector_data['换手率'].sum() > 0:
                most_active = sector_data.nlargest(10, '换手率')[['板块', '换手率', '主力资金', '涨跌幅']].to_dict('records')
            else:
                # 如果没有换手率数据，按主力资金绝对值排序作为活跃度指标
                sector_data_copy = sector_data.copy()
                sector_data_copy['资金活跃度'] = sector_data_copy['主力资金'].abs()
                most_active = sector_data_copy.nlargest(10, '资金活跃度')[['板块', '主力资金', '涨跌幅']].to_dict('records')
                # 添加换手率字段（设为0）
                for item in most_active:
                    item['换手率'] = 0.0
            
            # 计算总体资金流向
            total_inflow = sector_data[sector_data['主力资金'] > 0]['主力资金'].sum()
            total_outflow = sector_data[sector_data['主力资金'] < 0]['主力资金'].sum()
            net_flow = total_inflow + total_outflow
            
            # 市场情绪指标
            market_sentiment = self._calculate_market_sentiment(sector_data)
            
            result = {
                'summary': {
                    '总板块数': total_sectors,
                    '资金净流入板块': inflow_sectors,
                    '资金净流出板块': outflow_sectors,
                    '上涨板块': rising_sectors,
                    '下跌板块': falling_sectors,
                    '总资金净流入': f"{net_flow:.2f}亿元",
                    '资金流入占比': f"{(inflow_sectors/total_sectors*100):.1f}%",
                    '上涨占比': f"{(rising_sectors/total_sectors*100):.1f}%"
                },
                'rankings': {
                    '资金流入榜': top_inflow,
                    '资金流出榜': top_outflow,
                    '涨幅榜': top_rising,
                    '跌幅榜': top_falling,
                    '活跃榜': most_active
                },
                'market_sentiment': market_sentiment,
                'raw_data': sector_data
            }
            
            self.logger.info(f"成功处理 {total_sectors} 个板块的数据")
            return result
            
        except Exception as e:
            self.logger.error(f"处理板块数据失败: {e}")
            return {}
    
    def analyze_index_sector_detail(self, index_code: str, sector_data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析指数板块的详细数据
        :param index_code: 指数代码
        :param sector_data: 板块数据（包含成分股信息）
        :return: 分析结果
        """
        try:
            if sector_data.empty:
                return self._get_empty_sector_analysis(index_code)
            
            sector_info = sector_data.iloc[0]
            sector_name = sector_info['板块']
            constituents_data = sector_info.get('成分股数据', [])
            
            if not constituents_data:
                return self._get_empty_sector_analysis(index_code, sector_name)
            
            # 转换成分股数据为DataFrame
            constituents_df = pd.DataFrame(constituents_data)
            
            # 基础统计
            total_stocks = len(constituents_df)
            rising_stocks = len(constituents_df[constituents_df['涨跌幅'] > 0])
            falling_stocks = len(constituents_df[constituents_df['涨跌幅'] < 0])
            
            # 资金流向统计
            inflow_stocks = len(constituents_df[constituents_df['主力净流入'] > 0])
            outflow_stocks = len(constituents_df[constituents_df['主力净流入'] < 0])
            
            # 个股排行
            top_inflow_stocks = constituents_df[constituents_df['主力净流入'] > 0].nlargest(
                min(10, len(constituents_df)), '主力净流入')[['股票代码', '股票名称', '主力净流入', '涨跌幅', '权重']].to_dict('records')
            
            top_outflow_stocks = constituents_df[constituents_df['主力净流入'] < 0].nsmallest(
                min(10, len(constituents_df)), '主力净流入')[['股票代码', '股票名称', '主力净流入', '涨跌幅', '权重']].to_dict('records')
            
            # 涨幅排行
            top_rising_stocks = constituents_df.nlargest(
                min(10, len(constituents_df)), '涨跌幅')[['股票代码', '股票名称', '涨跌幅', '主力净流入', '权重']].to_dict('records')
            
            # 计算板块总体指标
            total_net_inflow = constituents_df['主力净流入'].sum()
            avg_change = (constituents_df['涨跌幅'] * constituents_df['权重']).sum()  # 加权平均
            
            # 板块强度分析
            strength_analysis = self._analyze_index_sector_strength(constituents_df)
            
            result = {
                'sector_name': sector_name,
                'index_code': index_code,
                'summary': {
                    '成分股数量': total_stocks,
                    '资金净流入股票': inflow_stocks,
                    '资金净流出股票': outflow_stocks,
                    '上涨股票': rising_stocks,
                    '下跌股票': falling_stocks,
                    '板块总资金净流入': f"{total_net_inflow:.2f}万元",
                    '加权平均涨跌幅': f"{avg_change:.2f}%",
                    '上涨比例': f"{(rising_stocks/total_stocks*100):.1f}%" if total_stocks > 0 else "0.0%"
                },
                'stock_rankings': {
                    '资金流入榜': top_inflow_stocks,
                    '资金流出榜': top_outflow_stocks,
                    '涨幅榜': top_rising_stocks
                },
                'strength_analysis': strength_analysis,
                'raw_data': constituents_df
            }
            
            self.logger.info(f"成功分析指数板块 {sector_name}({index_code}) 的 {total_stocks} 只成分股")
            return result
            
        except Exception as e:
            self.logger.error(f"分析指数板块 {index_code} 详细数据失败: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_sector_analysis(index_code)
    
    def _get_empty_sector_analysis(self, index_code: str, sector_name: str = None) -> Dict[str, Any]:
        """
        获取空的板块分析结果
        :param index_code: 指数代码
        :param sector_name: 板块名称
        :return: 空分析结果
        """
        if not sector_name:
            # 尝试从fetcher获取指数名称
            try:
                from sector.fetcher import create_sector_fetcher
                fetcher = create_sector_fetcher()
                index_stock = fetcher.get_index_stock_info()
                sector_name = index_stock.get(index_code, f'指数{index_code}')
            except Exception:
                sector_name = f'指数{index_code}'
        
        return {
            'sector_name': sector_name,
            'index_code': index_code,
            'summary': {
                '成分股数量': 0,
                '资金净流入股票': 0,
                '资金净流出股票': 0,
                '上涨股票': 0,
                '下跌股票': 0,
                '板块总资金净流入': "0.00万元",
                '加权平均涨跌幅': "0.00%",
                '上涨比例': "0.0%"
            },
            'stock_rankings': {
                '资金流入榜': [],
                '资金流出榜': [],
                '涨幅榜': []
            },
            'strength_analysis': {},
            'raw_data': pd.DataFrame()
        }
    
    def analyze_sector_history(self, history_data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析板块历史数据
        :param history_data: 板块历史数据
        :return: 历史分析结果
        """
        try:
            if history_data.empty:
                return {}
            
            # 基础统计
            total_days = len(history_data)
            
            # 涨跌统计
            rising_days = len(history_data[history_data['涨跌幅'] > 0])
            falling_days = len(history_data[history_data['涨跌幅'] < 0])
            flat_days = total_days - rising_days - falling_days
            
            # 资金流向统计
            inflow_days = len(history_data[history_data['主力净流入'] > 0])
            outflow_days = len(history_data[history_data['主力净流入'] < 0])
            
            # 累计指标
            total_return = history_data['涨跌幅'].sum()
            total_fund_flow = history_data['主力净流入'].sum()
            avg_turnover = history_data['换手率'].mean()
            avg_volume = history_data['成交量'].mean()
            
            # 波动率计算
            volatility = history_data['涨跌幅'].std()
            
            # 最大回撤计算
            cumulative_returns = (1 + history_data['涨跌幅'] / 100).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min() * 100
            
            # 趋势分析
            recent_7_days = history_data.tail(7)
            recent_30_days = history_data.tail(30)
            
            recent_7_return = recent_7_days['涨跌幅'].sum() if len(recent_7_days) > 0 else 0
            recent_30_return = recent_30_days['涨跌幅'].sum() if len(recent_30_days) > 0 else 0
            
            recent_7_fund_flow = recent_7_days['主力净流入'].sum() if len(recent_7_days) > 0 else 0
            recent_30_fund_flow = recent_30_days['主力净流入'].sum() if len(recent_30_days) > 0 else 0
            
            # 强势期分析
            strong_days = len(history_data[history_data['涨跌幅'] > 3])  # 涨幅超过3%的天数
            weak_days = len(history_data[history_data['涨跌幅'] < -3])  # 跌幅超过3%的天数
            
            # 活跃度分析
            high_turnover_days = len(history_data[history_data['换手率'] > avg_turnover * 1.5])
            
            result = {
                'period_summary': {
                    '统计天数': total_days,
                    '上涨天数': rising_days,
                    '下跌天数': falling_days,
                    '平盘天数': flat_days,
                    '上涨概率': f"{(rising_days/total_days*100):.1f}%" if total_days > 0 else "0%"
                },
                'return_analysis': {
                    '累计涨跌幅': f"{total_return:.2f}%",
                    '平均日涨跌幅': f"{history_data['涨跌幅'].mean():.2f}%",
                    '最大单日涨幅': f"{history_data['涨跌幅'].max():.2f}%",
                    '最大单日跌幅': f"{history_data['涨跌幅'].min():.2f}%",
                    '波动率': f"{volatility:.2f}%",
                    '最大回撤': f"{max_drawdown:.2f}%"
                },
                'fund_flow_analysis': {
                    '资金净流入天数': inflow_days,
                    '资金净流出天数': outflow_days,
                    '净流入概率': f"{(inflow_days/total_days*100):.1f}%" if total_days > 0 else "0%",
                    '累计资金净流入': f"{total_fund_flow:.2f}万元",
                    '平均日资金流入': f"{history_data['主力净流入'].mean():.2f}万元",
                    '最大单日流入': f"{history_data['主力净流入'].max():.2f}万元",
                    '最大单日流出': f"{history_data['主力净流入'].min():.2f}万元"
                },
                'activity_analysis': {
                    '平均换手率': f"{avg_turnover:.2f}%",
                    '平均成交量': f"{avg_volume:.0f}",
                    '高活跃天数': high_turnover_days,
                    '强势天数': strong_days,
                    '弱势天数': weak_days
                },
                'recent_trend': {
                    '近7日涨跌幅': f"{recent_7_return:.2f}%",
                    '近30日涨跌幅': f"{recent_30_return:.2f}%",
                    '近7日资金流入': f"{recent_7_fund_flow:.2f}万元",
                    '近30日资金流入': f"{recent_30_fund_flow:.2f}万元"
                }
            }
            
            self.logger.info(f"成功分析 {total_days} 天的板块历史数据")
            return result
            
        except Exception as e:
            self.logger.error(f"分析板块历史数据失败: {e}")
            return {}

    def _analyze_index_sector_strength(self, constituents_df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析指数板块强度
        :param constituents_df: 成分股数据
        :return: 强度分析
        """
        try:
            # 资金集中度（按权重计算）
            total_inflow = constituents_df[constituents_df['主力净流入'] > 0]['主力净流入'].sum()
            
            # 取权重最大的前5只股票的资金流入
            top5_by_weight = constituents_df.nlargest(5, '权重')
            top5_inflow = top5_by_weight[top5_by_weight['主力净流入'] > 0]['主力净流入'].sum()
            
            if total_inflow > 0:
                concentration = (top5_inflow / total_inflow) * 100
            else:
                concentration = 0
            
            # 涨停股数量（涨幅>9.5%）
            limit_up_count = len(constituents_df[constituents_df['涨跌幅'] >= 9.5])
            
            # 强势股比例（涨幅>3%）
            strong_stocks = len(constituents_df[constituents_df['涨跌幅'] > 3])
            strong_ratio = (strong_stocks / len(constituents_df)) * 100
            
            # 权重股表现（权重前5的平均涨跌幅）
            top_weight_performance = (top5_by_weight['涨跌幅'] * top5_by_weight['权重']).sum() / top5_by_weight['权重'].sum()
            
            # 板块强度评级
            if strong_ratio >= 50 and limit_up_count >= 3:
                strength_level = "极强"
            elif strong_ratio >= 30 and limit_up_count >= 1:
                strength_level = "强"
            elif strong_ratio >= 20:
                strength_level = "中等"
            elif strong_ratio >= 10:
                strength_level = "弱"
            else:
                strength_level = "极弱"
            
            return {
                '板块强度': strength_level,
                '强势股比例': f"{strong_ratio:.1f}%",
                '涨停股数量': limit_up_count,
                '资金集中度': f"{concentration:.1f}%",
                '权重股表现': f"{top_weight_performance:.2f}%",
                '龙头效应': "明显" if concentration > 60 else "一般" if concentration > 30 else "分散"
            }
            
        except Exception as e:
            self.logger.error(f"分析指数板块强度失败: {e}")
            return {}

    def analyze_sector_detail(self, sector_name: str, detail_data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析单个板块的详细数据
        :param sector_name: 板块名称
        :param detail_data: 详细数据
        :return: 分析结果
        """
        try:
            if detail_data.empty:
                return {
                    'sector_name': sector_name,
                    'summary': {
                        '成分股数量': 0,
                        '资金净流入股票': 0,
                        '资金净流出股票': 0,
                        '上涨股票': 0,
                        '下跌股票': 0,
                        '板块总资金净流入': "0.00万元",
                        '平均涨跌幅': "0.00%",
                        '上涨比例': "0.0%"
                    },
                    'stock_rankings': {
                        '资金流入榜': [],
                        '资金流出榜': []
                    },
                    'strength_analysis': {},
                    'raw_data': pd.DataFrame()
                }
            
            # 确保必要的列存在
            if '主力净流入' not in detail_data.columns:
                detail_data['主力净流入'] = 0
            if '涨跌幅' not in detail_data.columns:
                detail_data['涨跌幅'] = 0
            if '名称' not in detail_data.columns:
                detail_data['名称'] = detail_data.get('股票名称', detail_data.get('代码', '未知股票'))
            if '代码' not in detail_data.columns:
                detail_data['代码'] = '000000'
            
            # 基础统计
            total_stocks = len(detail_data)
            
            # 资金流向统计
            inflow_stocks = len(detail_data[detail_data['主力净流入'] > 0])
            outflow_stocks = len(detail_data[detail_data['主力净流入'] < 0])
            
            # 涨跌统计
            rising_stocks = len(detail_data[detail_data['涨跌幅'] > 0])
            falling_stocks = len(detail_data[detail_data['涨跌幅'] < 0])
            
            # 个股排行 - 确保有足够的列
            required_columns = ['名称', '代码', '主力净流入', '涨跌幅']
            available_columns = [col for col in required_columns if col in detail_data.columns]
            
            if len(available_columns) >= 2:
                # 个股资金流入榜：只包含主力净流入>0的股票
                inflow_stocks_data = detail_data[detail_data['主力净流入'] > 0]
                if not inflow_stocks_data.empty:
                    top_inflow_stocks = inflow_stocks_data.nlargest(min(10, len(inflow_stocks_data)), '主力净流入')[available_columns].to_dict('records')
                else:
                    top_inflow_stocks = []
                
                # 个股资金流出榜：只包含主力净流入<0的股票
                outflow_stocks_data = detail_data[detail_data['主力净流入'] < 0]
                if not outflow_stocks_data.empty:
                    top_outflow_stocks = outflow_stocks_data.nsmallest(min(10, len(outflow_stocks_data)), '主力净流入')[available_columns].to_dict('records')
                else:
                    top_outflow_stocks = []
            else:
                top_inflow_stocks = []
                top_outflow_stocks = []
            
            # 计算板块总体资金流向
            total_net_inflow = detail_data['主力净流入'].sum()
            avg_change = detail_data['涨跌幅'].mean()
            
            # 板块强度分析
            strength_analysis = self._analyze_sector_strength(detail_data)
            
            result = {
                'sector_name': sector_name,
                'summary': {
                    '成分股数量': total_stocks,
                    '资金净流入股票': inflow_stocks,
                    '资金净流出股票': outflow_stocks,
                    '上涨股票': rising_stocks,
                    '下跌股票': falling_stocks,
                    '板块总资金净流入': f"{total_net_inflow:.2f}万元",
                    '平均涨跌幅': f"{avg_change:.2f}%",
                    '上涨比例': f"{(rising_stocks/total_stocks*100):.1f}%" if total_stocks > 0 else "0.0%"
                },
                'stock_rankings': {
                    '资金流入榜': top_inflow_stocks,
                    '资金流出榜': top_outflow_stocks
                },
                'strength_analysis': strength_analysis,
                'raw_data': detail_data
            }
            
            self.logger.info(f"成功分析板块 {sector_name} 的 {total_stocks} 只成分股")
            return result
            
        except Exception as e:
            self.logger.error(f"分析板块 {sector_name} 详细数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'sector_name': sector_name,
                'summary': {
                    '成分股数量': 0,
                    '资金净流入股票': 0,
                    '资金净流出股票': 0,
                    '上涨股票': 0,
                    '下跌股票': 0,
                    '板块总资金净流入': "0.00万元",
                    '平均涨跌幅': "0.00%",
                    '上涨比例': "0.0%"
                },
                'stock_rankings': {
                    '资金流入榜': [],
                    '资金流出榜': []
                },
                'strength_analysis': {},
                'raw_data': pd.DataFrame()
            }
    
    def _calculate_market_sentiment(self, sector_data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算市场情绪指标
        :param sector_data: 板块数据
        :return: 情绪指标
        """
        try:
            # 涨跌比例
            total_sectors = len(sector_data)
            rising_ratio = len(sector_data[sector_data['涨跌幅'] > 0]) / total_sectors
            
            # 资金流向比例
            inflow_ratio = len(sector_data[sector_data['主力资金'] > 0]) / total_sectors
            
            # 平均涨跌幅
            avg_change = sector_data['涨跌幅'].mean()
            
            # 资金流向强度
            total_inflow = sector_data[sector_data['主力资金'] > 0]['主力资金'].sum()
            total_outflow = abs(sector_data[sector_data['主力资金'] < 0]['主力资金'].sum())
            
            if total_outflow > 0:
                flow_ratio = total_inflow / total_outflow
            else:
                flow_ratio = float('inf') if total_inflow > 0 else 0
            
            # 情绪判断
            if rising_ratio >= 0.7 and inflow_ratio >= 0.6:
                sentiment = "极度乐观"
                sentiment_score = 90
            elif rising_ratio >= 0.6 and inflow_ratio >= 0.5:
                sentiment = "乐观"
                sentiment_score = 75
            elif rising_ratio >= 0.4 and inflow_ratio >= 0.4:
                sentiment = "中性"
                sentiment_score = 50
            elif rising_ratio >= 0.3 and inflow_ratio >= 0.3:
                sentiment = "悲观"
                sentiment_score = 25
            else:
                sentiment = "极度悲观"
                sentiment_score = 10
            
            return {
                '市场情绪': sentiment,
                '情绪评分': sentiment_score,
                '上涨比例': f"{rising_ratio*100:.1f}%",
                '资金流入比例': f"{inflow_ratio*100:.1f}%",
                '平均涨跌幅': f"{avg_change:.2f}%",
                '资金流向比': f"{flow_ratio:.2f}" if flow_ratio != float('inf') else "∞"
            }
            
        except Exception as e:
            self.logger.error(f"计算市场情绪失败: {e}")
            return {}
    
    def _analyze_sector_strength(self, detail_data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析板块强度
        :param detail_data: 详细数据
        :return: 强度分析
        """
        try:
            # 资金集中度
            total_inflow = detail_data[detail_data['主力净流入'] > 0]['主力净流入'].sum()
            top5_inflow = detail_data.nlargest(5, '主力净流入')['主力净流入'].sum()
            
            if total_inflow > 0:
                concentration = (top5_inflow / total_inflow) * 100
            else:
                concentration = 0
            
            # 涨停股数量
            limit_up_count = len(detail_data[detail_data['涨跌幅'] >= 9.5])
            
            # 强势股比例（涨幅>3%）
            strong_stocks = len(detail_data[detail_data['涨跌幅'] > 3])
            strong_ratio = (strong_stocks / len(detail_data)) * 100
            
            # 板块强度评级
            if strong_ratio >= 50 and limit_up_count >= 3:
                strength_level = "极强"
            elif strong_ratio >= 30 and limit_up_count >= 1:
                strength_level = "强"
            elif strong_ratio >= 20:
                strength_level = "中等"
            elif strong_ratio >= 10:
                strength_level = "弱"
            else:
                strength_level = "极弱"
            
            return {
                '板块强度': strength_level,
                '强势股比例': f"{strong_ratio:.1f}%",
                '涨停股数量': limit_up_count,
                '资金集中度': f"{concentration:.1f}%",
                '龙头效应': "明显" if concentration > 60 else "一般" if concentration > 30 else "分散"
            }
            
        except Exception as e:
            self.logger.error(f"分析板块强度失败: {e}")
            return {}

def create_sector_processor() -> SectorProcessor:
    """创建板块数据处理器实例"""
    return SectorProcessor()