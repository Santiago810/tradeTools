"""
板块资金数据可视化器
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
import logging
from typing import Dict, Any, List, Optional

class SectorVisualizer:
    """板块资金数据可视化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.colors = {
            'positive': '#FF4444',  # 红色 - 上涨/流入 (中国习惯)
            'negative': '#00C851',  # 绿色 - 下跌/流出 (中国习惯)
            'neutral': '#33B5E5',   # 蓝色 - 中性
            'background': '#F8F9FA'
        }
    
    def create_sector_overview_chart(self, processed_data: Dict[str, Any]) -> Optional[go.Figure]:
        """
        创建板块概览图表
        :param processed_data: 处理后的数据
        :return: 图表对象
        """
        try:
            if not processed_data or 'raw_data' not in processed_data:
                return None
            
            sector_data = processed_data['raw_data']
            
            # 创建子图
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('资金流向分布', '涨跌幅分布', '资金流向 vs 涨跌幅', '板块活跃度'),
                specs=[[{"type": "bar"}, {"type": "histogram"}],
                       [{"type": "scatter"}, {"type": "bar"}]]
            )
            
            # 1. 资金流向分布
            inflow_data = sector_data[sector_data['主力资金'] > 0]
            outflow_data = sector_data[sector_data['主力资金'] < 0]
            
            fig.add_trace(
                go.Bar(
                    x=['资金流入', '资金流出'],
                    y=[len(inflow_data), len(outflow_data)],
                    marker_color=[self.colors['positive'], self.colors['negative']],
                    name='板块数量'
                ),
                row=1, col=1
            )
            
            # 2. 涨跌幅分布
            fig.add_trace(
                go.Histogram(
                    x=sector_data['涨跌幅'],
                    nbinsx=20,
                    marker_color=self.colors['neutral'],
                    name='涨跌幅分布'
                ),
                row=1, col=2
            )
            
            # 3. 资金流向 vs 涨跌幅散点图
            colors = [self.colors['positive'] if x > 0 else self.colors['negative'] 
                     for x in sector_data['主力资金']]
            
            fig.add_trace(
                go.Scatter(
                    x=sector_data['主力资金'],
                    y=sector_data['涨跌幅'],
                    mode='markers',
                    marker=dict(color=colors, size=8, opacity=0.7),
                    text=sector_data['板块'],
                    hovertemplate='<b>%{text}</b><br>主力资金: %{x:.2f}亿<br>涨跌幅: %{y:.2f}%<extra></extra>',
                    name='板块分布'
                ),
                row=2, col=1
            )
            
            # 4. 板块活跃度（按主力资金绝对值）
            sector_data_copy = sector_data.copy()
            sector_data_copy['资金活跃度'] = sector_data_copy['主力资金'].abs()
            top_active = sector_data_copy.nlargest(10, '资金活跃度')
            
            fig.add_trace(
                go.Bar(
                    x=top_active['资金活跃度'],
                    y=top_active['板块'],
                    orientation='h',
                    marker_color=self.colors['neutral'],
                    name='资金活跃度'
                ),
                row=2, col=2
            )
            
            # 更新布局
            fig.update_layout(
                title='板块资金流向概览',
                height=800,
                showlegend=False,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建板块概览图表失败: {e}")
            return None
    
    def create_sector_ranking_chart(self, processed_data: Dict[str, Any], chart_type: str = 'inflow') -> Optional[go.Figure]:
        """
        创建板块排行榜图表
        :param processed_data: 处理后的数据
        :param chart_type: 图表类型 ('inflow', 'outflow', 'rising', 'falling')
        :return: 图表对象
        """
        try:
            if not processed_data or 'rankings' not in processed_data:
                return None
            
            rankings = processed_data['rankings']
            
            if chart_type == 'inflow':
                data = rankings.get('资金流入榜', [])
                title = '板块资金流入排行榜'
                value_col = '主力资金'
                color = self.colors['positive']
            elif chart_type == 'outflow':
                data = rankings.get('资金流出榜', [])
                title = '板块资金流出排行榜'
                value_col = '主力资金'
                color = self.colors['negative']
            elif chart_type == 'rising':
                data = rankings.get('涨幅榜', [])
                title = '板块涨幅排行榜'
                value_col = '涨跌幅'
                color = self.colors['positive']
            elif chart_type == 'falling':
                data = rankings.get('跌幅榜', [])
                title = '板块跌幅排行榜'
                value_col = '涨跌幅'
                color = self.colors['negative']
            else:
                return None
            
            if not data:
                return None
            
            df = pd.DataFrame(data)
            
            fig = go.Figure()
            
            fig.add_trace(
                go.Bar(
                    x=df[value_col],
                    y=df['板块'],
                    orientation='h',
                    marker_color=color,
                    text=df[value_col],
                    texttemplate='%{text:.2f}',
                    textposition='outside'
                )
            )
            
            fig.update_layout(
                title=title,
                xaxis_title=value_col,
                yaxis_title='板块',
                height=500,
                template='plotly_white',
                yaxis={'categoryorder': 'total ascending'}
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建板块排行榜图表失败: {e}")
            return None
    
    def create_sector_detail_chart(self, detail_analysis: Dict[str, Any]) -> Optional[go.Figure]:
        """
        创建板块详细分析图表
        :param detail_analysis: 详细分析数据
        :return: 图表对象
        """
        try:
            if not detail_analysis or 'raw_data' not in detail_analysis:
                return None
            
            stock_data = detail_analysis['raw_data']
            sector_name = detail_analysis.get('sector_name', '未知板块')
            
            # 创建子图
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    f'{sector_name} - 个股资金流向',
                    f'{sector_name} - 个股涨跌分布',
                    f'{sector_name} - 资金流向vs涨跌幅',
                    f'{sector_name} - 龙头股表现'
                ),
                specs=[[{"type": "bar"}, {"type": "histogram"}],
                       [{"type": "scatter"}, {"type": "bar"}]]
            )
            
            # 1. 个股资金流向（Top10 + Bottom10）
            top_stocks = stock_data.nlargest(10, '主力净流入')
            bottom_stocks = stock_data.nsmallest(10, '主力净流入')
            
            fig.add_trace(
                go.Bar(
                    x=top_stocks['主力净流入'],
                    y=top_stocks['名称'],
                    orientation='h',
                    marker_color=self.colors['positive'],
                    name='资金流入',
                    text=top_stocks['主力净流入'],
                    texttemplate='%{text:.0f}万'
                ),
                row=1, col=1
            )
            
            # 2. 个股涨跌分布
            fig.add_trace(
                go.Histogram(
                    x=stock_data['涨跌幅'],
                    nbinsx=15,
                    marker_color=self.colors['neutral'],
                    name='涨跌幅分布'
                ),
                row=1, col=2
            )
            
            # 3. 资金流向 vs 涨跌幅
            colors = [self.colors['positive'] if x > 0 else self.colors['negative'] 
                     for x in stock_data['主力净流入']]
            
            fig.add_trace(
                go.Scatter(
                    x=stock_data['主力净流入'],
                    y=stock_data['涨跌幅'],
                    mode='markers',
                    marker=dict(color=colors, size=6, opacity=0.7),
                    text=stock_data['名称'],
                    hovertemplate='<b>%{text}</b><br>主力净流入: %{x:.0f}万<br>涨跌幅: %{y:.2f}%<extra></extra>',
                    name='个股分布'
                ),
                row=2, col=1
            )
            
            # 4. 龙头股表现（按资金流入排序的前5名）
            top5_stocks = stock_data.nlargest(5, '主力净流入')
            fig.add_trace(
                go.Bar(
                    x=top5_stocks['名称'],
                    y=top5_stocks['涨跌幅'],
                    marker_color=[self.colors['positive'] if x > 0 else self.colors['negative'] 
                                 for x in top5_stocks['涨跌幅']],
                    name='龙头股涨跌幅',
                    text=top5_stocks['涨跌幅'],
                    texttemplate='%{text:.2f}%'
                ),
                row=2, col=2
            )
            
            # 更新布局
            fig.update_layout(
                title=f'{sector_name} 详细分析',
                height=800,
                showlegend=False,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建板块详细图表失败: {e}")
            return None
    
    def create_market_sentiment_gauge(self, processed_data: Dict[str, Any]) -> Optional[go.Figure]:
        """
        创建市场情绪仪表盘
        :param processed_data: 处理后的数据
        :return: 图表对象
        """
        try:
            if not processed_data or 'market_sentiment' not in processed_data:
                return None
            
            sentiment = processed_data['market_sentiment']
            score = sentiment.get('情绪评分', 50)
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "市场情绪指数"},
                delta = {'reference': 50},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 25], 'color': "lightgray"},
                        {'range': [25, 50], 'color': "gray"},
                        {'range': [50, 75], 'color': "lightgreen"},
                        {'range': [75, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig.update_layout(
                height=400,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建市场情绪仪表盘失败: {e}")
            return None

def create_sector_visualizer() -> SectorVisualizer:
    """创建板块数据可视化器实例"""
    return SectorVisualizer()