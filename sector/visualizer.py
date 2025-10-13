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
    
    def create_index_sector_chart(self, analysis_result: Dict[str, Any]) -> Optional[go.Figure]:
        """
        创建指数板块分析图表
        :param analysis_result: 指数板块分析结果
        :return: 图表对象
        """
        try:
            if not analysis_result or 'raw_data' not in analysis_result:
                return None
            
            stock_data = analysis_result['raw_data']
            sector_name = analysis_result.get('sector_name', '未知板块')
            index_code = analysis_result.get('index_code', '')
            
            if stock_data.empty:
                return None
            
            # 创建子图
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    f'{sector_name}({index_code}) - 权重股资金流向',
                    f'{sector_name} - 权重分布',
                    f'{sector_name} - 权重vs涨跌幅',
                    f'{sector_name} - 龙头股表现'
                ),
                specs=[[{"type": "bar"}, {"type": "pie"}],
                       [{"type": "scatter"}, {"type": "bar"}]]
            )
            
            # 1. 权重股资金流向（按权重排序的前10只）
            top_weight_stocks = stock_data.nlargest(10, '权重')
            colors_flow = [self.colors['positive'] if x > 0 else self.colors['negative'] 
                          for x in top_weight_stocks['主力净流入']]
            
            fig.add_trace(
                go.Bar(
                    x=top_weight_stocks['主力净流入'],
                    y=top_weight_stocks['股票名称'],
                    orientation='h',
                    marker_color=colors_flow,
                    name='资金流向',
                    text=top_weight_stocks['主力净流入'],
                    texttemplate='%{text:.0f}万',
                    hovertemplate='<b>%{y}</b><br>主力净流入: %{x:.0f}万<br>权重: %{customdata:.2f}%<extra></extra>',
                    customdata=top_weight_stocks['权重'] * 100
                ),
                row=1, col=1
            )
            
            # 2. 权重分布饼图（前8只股票）
            top8_stocks = stock_data.nlargest(8, '权重')
            other_weight = stock_data.iloc[8:]['权重'].sum() if len(stock_data) > 8 else 0
            
            pie_labels = top8_stocks['股票名称'].tolist()
            pie_values = (top8_stocks['权重'] * 100).tolist()
            
            if other_weight > 0:
                pie_labels.append('其他')
                pie_values.append(other_weight * 100)
            
            fig.add_trace(
                go.Pie(
                    labels=pie_labels,
                    values=pie_values,
                    name='权重分布',
                    textinfo='label+percent',
                    textposition='inside'
                ),
                row=1, col=2
            )
            
            # 3. 权重 vs 涨跌幅散点图
            colors_scatter = [self.colors['positive'] if x > 0 else self.colors['negative'] 
                             for x in stock_data['涨跌幅']]
            
            # 计算合适的点大小（限制在5-20之间）
            weight_sizes = stock_data['权重'] * 1000
            weight_sizes = np.clip(weight_sizes, 5, 20)  # 限制大小范围
            
            fig.add_trace(
                go.Scatter(
                    x=stock_data['权重'] * 100,
                    y=stock_data['涨跌幅'],
                    mode='markers',
                    marker=dict(
                        color=colors_scatter, 
                        size=weight_sizes,  # 使用处理后的大小
                        sizemin=5,
                        opacity=0.7
                    ),
                    text=stock_data['股票名称'],
                    hovertemplate='<b>%{text}</b><br>权重: %{x:.2f}%<br>涨跌幅: %{y:.2f}%<br>主力净流入: %{customdata:.0f}万<extra></extra>',
                    customdata=stock_data['主力净流入'],
                    name='权重vs涨跌幅'
                ),
                row=2, col=1
            )
            
            # 4. 权重前5股票的表现
            top5_weight = stock_data.nlargest(5, '权重')
            colors_perf = [self.colors['positive'] if x > 0 else self.colors['negative'] 
                          for x in top5_weight['涨跌幅']]
            
            fig.add_trace(
                go.Bar(
                    x=top5_weight['股票名称'],
                    y=top5_weight['涨跌幅'],
                    marker_color=colors_perf,
                    name='权重股表现',
                    text=top5_weight['涨跌幅'],
                    texttemplate='%{text:.2f}%',
                    hovertemplate='<b>%{x}</b><br>涨跌幅: %{y:.2f}%<br>权重: %{customdata:.2f}%<extra></extra>',
                    customdata=top5_weight['权重'] * 100
                ),
                row=2, col=2
            )
            
            # 更新布局
            fig.update_layout(
                title=f'{sector_name}({index_code}) 权重股分析',
                height=800,
                showlegend=False,
                template='plotly_white'
            )
            
            # 更新x轴标签
            fig.update_xaxes(title_text="主力净流入(万元)", row=1, col=1)
            fig.update_xaxes(title_text="权重(%)", row=2, col=1)
            fig.update_xaxes(title_text="股票", row=2, col=2)
            
            # 更新y轴标签
            fig.update_yaxes(title_text="股票", row=1, col=1)
            fig.update_yaxes(title_text="涨跌幅(%)", row=2, col=1)
            fig.update_yaxes(title_text="涨跌幅(%)", row=2, col=2)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建指数板块图表失败: {e}")
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

    def create_sector_history_chart(self, history_data: pd.DataFrame, analysis_result: Dict[str, Any]) -> Optional[go.Figure]:
        """
        创建板块历史趋势图表
        :param history_data: 历史数据
        :param analysis_result: 历史分析结果
        :return: 图表对象
        """
        try:
            if history_data.empty:
                return None
            
            sector_name = history_data['板块名称'].iloc[0] if '板块名称' in history_data.columns else '板块'
            
            # 创建子图
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    f'{sector_name} - 涨跌幅趋势',
                    f'{sector_name} - 资金流向趋势',
                    f'{sector_name} - 换手率趋势',
                    f'{sector_name} - 成交量趋势',
                    f'{sector_name} - 累计收益',
                    f'{sector_name} - 上涨比例趋势'
                ),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            dates = history_data['交易日期']
            
            # 1. 涨跌幅趋势
            colors_change = [self.colors['positive'] if x > 0 else self.colors['negative'] 
                           for x in history_data['涨跌幅']]
            
            fig.add_trace(
                go.Bar(
                    x=dates,
                    y=history_data['涨跌幅'],
                    marker_color=colors_change,
                    name='日涨跌幅',
                    hovertemplate='日期: %{x}<br>涨跌幅: %{y:.2f}%<extra></extra>'
                ),
                row=1, col=1
            )
            
            # 2. 资金流向趋势
            colors_fund = [self.colors['positive'] if x > 0 else self.colors['negative'] 
                          for x in history_data['主力净流入']]
            
            fig.add_trace(
                go.Bar(
                    x=dates,
                    y=history_data['主力净流入'],
                    marker_color=colors_fund,
                    name='主力净流入',
                    hovertemplate='日期: %{x}<br>主力净流入: %{y:.2f}万元<extra></extra>'
                ),
                row=1, col=2
            )
            
            # 3. 换手率趋势
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=history_data['换手率'],
                    mode='lines+markers',
                    line=dict(color=self.colors['neutral'], width=2),
                    marker=dict(size=4),
                    name='换手率',
                    hovertemplate='日期: %{x}<br>换手率: %{y:.2f}%<extra></extra>'
                ),
                row=2, col=1
            )
            
            # 4. 成交量趋势
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=history_data['成交量'],
                    mode='lines',
                    fill='tonexty',
                    line=dict(color=self.colors['neutral'], width=1),
                    name='成交量',
                    hovertemplate='日期: %{x}<br>成交量: %{y:.0f}<extra></extra>'
                ),
                row=2, col=2
            )
            
            # 5. 累计收益曲线
            cumulative_returns = (1 + history_data['涨跌幅'] / 100).cumprod() - 1
            
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=cumulative_returns * 100,
                    mode='lines',
                    line=dict(color=self.colors['positive'], width=3),
                    name='累计收益率',
                    hovertemplate='日期: %{x}<br>累计收益: %{y:.2f}%<extra></extra>'
                ),
                row=3, col=1
            )
            
            # 6. 上涨比例趋势
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=history_data['上涨比例'],
                    mode='lines+markers',
                    line=dict(color=self.colors['neutral'], width=2),
                    marker=dict(size=4),
                    name='上涨比例',
                    hovertemplate='日期: %{x}<br>上涨比例: %{y:.1f}%<extra></extra>'
                ),
                row=3, col=2
            )
            
            # 更新布局
            fig.update_layout(
                title=f'{sector_name} 历史趋势分析 ({len(history_data)}天)',
                height=1000,
                showlegend=False,
                template='plotly_white'
            )
            
            # 更新x轴标签
            fig.update_xaxes(title_text="日期", row=1, col=1)
            fig.update_xaxes(title_text="日期", row=1, col=2)
            fig.update_xaxes(title_text="日期", row=2, col=1)
            fig.update_xaxes(title_text="日期", row=2, col=2)
            fig.update_xaxes(title_text="日期", row=3, col=1)
            fig.update_xaxes(title_text="日期", row=3, col=2)
            
            # 更新y轴标签
            fig.update_yaxes(title_text="涨跌幅(%)", row=1, col=1)
            fig.update_yaxes(title_text="资金流入(万元)", row=1, col=2)
            fig.update_yaxes(title_text="换手率(%)", row=2, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=2)
            fig.update_yaxes(title_text="累计收益率(%)", row=3, col=1)
            fig.update_yaxes(title_text="上涨比例(%)", row=3, col=2)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建板块历史趋势图表失败: {e}")
            return None

def create_sector_visualizer() -> SectorVisualizer:
    """创建板块数据可视化器实例"""
    return SectorVisualizer()