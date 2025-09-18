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
            
            # 资金流向排行
            top_inflow = sector_data.nlargest(10, '主力资金')[['板块', '主力资金', '涨跌幅', '换手率']].to_dict('records')
            top_outflow = sector_data.nsmallest(10, '主力资金')[['板块', '主力资金', '涨跌幅', '换手率']].to_dict('records')
            
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
                top_inflow_stocks = detail_data.nlargest(min(10, len(detail_data)), '主力净流入')[available_columns].to_dict('records')
                top_outflow_stocks = detail_data.nsmallest(min(10, len(detail_data)), '主力净流入')[available_columns].to_dict('records')
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