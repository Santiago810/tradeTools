"""
ETF数据可视化模块 - A股ETF查询系统
生成ETF资金流向、份额变动等图表
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CHART_CONFIG

class ETFVisualizer:
    """ETF数据可视化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.color_palette = CHART_CONFIG['color_palette']
    

    

    

    
    def create_comprehensive_etf_chart(self, fund_flow_data: pd.DataFrame, 
                                     share_change_data: pd.DataFrame,
                                     outside_data: pd.DataFrame) -> go.Figure:
        """
        创建综合ETF图表
        :param fund_flow_data: 资金流向数据
        :param share_change_data: 份额变动数据
        :param outside_data: 场外市场数据
        :return: Plotly图表对象
        """
        try:
            fig = make_subplots(
                rows=5, cols=1,
                subplot_titles=['价格趋势', '成交额趋势', '涨跌幅', '净流入趋势', '换手率变化'],
                vertical_spacing=0.05
            )
            
            # 价格趋势子图（收盘价）
            if not outside_data.empty and '收盘' in outside_data.columns:
                if '日期' in outside_data.columns:
                    outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                    outside_data = outside_data.sort_values('日期')
                
                fig.add_trace(
                    go.Scatter(
                        x=outside_data['日期'],
                        y=outside_data['收盘'],
                        mode='lines+markers',
                        name='收盘价',
                        line=dict(color='#2196F3', width=2),
                        fill='tonexty',
                        fillcolor='rgba(33, 150, 243, 0.1)',
                        hovertemplate='<b>收盘价</b><br>' +
                                     '日期: %{x}<br>' +
                                     '收盘价: %{y:.3f}元<br>' +
                                     '<extra></extra>'
                    ),
                    row=1, col=1
                )
                
                # 添加价格均线
                if len(outside_data) >= 5:
                    ma5 = outside_data['收盘'].rolling(window=5, min_periods=1).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=outside_data['日期'],
                            y=ma5,
                            mode='lines',
                            name='5日均线',
                            line=dict(color='#FF9800', width=1, dash='dash'),
                            hovertemplate='<b>5日均线</b><br>' +
                                         '日期: %{x}<br>' +
                                         '均价: %{y:.3f}元<br>' +
                                         '<extra></extra>'
                        ),
                        row=1, col=1
                    )
                
                # 设置价格图的Y轴范围，从最低价附近开始以突出变化趋势
                min_price = outside_data['收盘'].min()
                max_price = outside_data['收盘'].max()
                price_range = max_price - min_price
                
                # Y轴下限：最低价减去价格范围的10%，但不低于最低价的95%
                y_min = max(min_price - price_range * 0.1, min_price * 0.95)
                # Y轴上限：最高价加上价格范围的10%
                y_max = max_price + price_range * 0.1
                
                fig.update_yaxes(range=[y_min, y_max], row=1, col=1)
            
            # 成交额趋势子图
            if not fund_flow_data.empty and '成交额' in fund_flow_data.columns:
                if '日期' in fund_flow_data.columns:
                    fund_flow_data['日期'] = pd.to_datetime(fund_flow_data['日期'])
                    fund_flow_data = fund_flow_data.sort_values('日期')
                
                # 将成交额转换为亿元单位
                turnover_in_billions = fund_flow_data['成交额'] / 1e8
                fig.add_trace(
                    go.Scatter(
                        x=fund_flow_data['日期'],
                        y=turnover_in_billions,
                        mode='lines+markers',
                        name='成交额',
                        line=dict(color=self.color_palette[0], width=2),
                        fill='tozeroy',
                        fillcolor=f'rgba{tuple(list(px.colors.hex_to_rgb(self.color_palette[0])) + [0.3])}'
                    ),
                    row=2, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
            
            # 涨跌幅子图 - 中国股市颜色习惯：红涨绿跌
            if not outside_data.empty and '涨跌幅' in outside_data.columns:
                if '日期' in outside_data.columns:
                    outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                    outside_data = outside_data.sort_values('日期')
                
                # 中国股市颜色习惯：红色表示上涨，绿色表示下跌
                colors = ['#FF4444' if x >= 0 else '#00C851' for x in outside_data['涨跌幅']]
                
                fig.add_trace(
                    go.Bar(
                        x=outside_data['日期'],
                        y=outside_data['涨跌幅'],
                        name='涨跌幅',
                        marker_color=colors,
                        hovertemplate='<b>涨跌幅</b><br>' +
                                     '日期: %{x}<br>' +
                                     '涨跌幅: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    ),
                    row=3, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)
            
            # 净流入趋势子图
            if not fund_flow_data.empty and '净流入' in fund_flow_data.columns:
                if '日期' in fund_flow_data.columns:
                    fund_flow_data['日期'] = pd.to_datetime(fund_flow_data['日期'])
                    fund_flow_data = fund_flow_data.sort_values('日期')
                
                # 将净流入转换为亿元单位
                net_inflow_in_billions = fund_flow_data['净流入'] / 1e8
                
                # 净流入柱状图：红色表示净流入，绿色表示净流出
                colors = ['#FF4444' if x >= 0 else '#00C851' for x in net_inflow_in_billions]
                
                fig.add_trace(
                    go.Bar(
                        x=fund_flow_data['日期'],
                        y=net_inflow_in_billions,
                        name='净流入',
                        marker_color=colors,
                        hovertemplate='<b>净流入</b><br>' +
                                     '日期: %{x}<br>' +
                                     '净流入: %{y:.2f}亿元<br>' +
                                     '<extra></extra>'
                    ),
                    row=4, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=4, col=1)
                
                # 添加净流入累计趋势线
                if '累计净流入' in fund_flow_data.columns:
                    cumulative_inflow = fund_flow_data['累计净流入'] / 1e8
                    fig.add_trace(
                        go.Scatter(
                            x=fund_flow_data['日期'],
                            y=cumulative_inflow,
                            mode='lines',
                            name='累计净流入',
                            line=dict(color='#2196F3', width=2),
                            yaxis='y2',
                            hovertemplate='<b>累计净流入</b><br>' +
                                         '日期: %{x}<br>' +
                                         '累计净流入: %{y:.2f}亿元<br>' +
                                         '<extra></extra>'
                        ),
                        row=4, col=1
                    )
            
            # 换手率子图 - 使用outside_data中的换手率数据
            if not outside_data.empty and '换手率' in outside_data.columns:
                if '日期' in outside_data.columns:
                    outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                    outside_data = outside_data.sort_values('日期')
                
                # 确保换手率数据是数值类型
                turnover_rates = pd.to_numeric(outside_data['换手率'], errors='coerce').fillna(0)
                
                fig.add_trace(
                    go.Scatter(
                        x=outside_data['日期'],
                        y=turnover_rates,
                        mode='lines+markers',
                        name='换手率',
                        line=dict(color=self.color_palette[3] if len(self.color_palette) > 3 else '#FFA500', width=2),
                        hovertemplate='<b>换手率</b><br>' +
                                     '日期: %{x}<br>' +
                                     '换手率: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    ),
                    row=5, col=1
                )
                
                # 添加换手率均值线
                if len(turnover_rates) > 0:
                    mean_turnover = turnover_rates.mean()
                    fig.add_hline(
                        y=mean_turnover,
                        line=dict(color='red', width=1, dash='dash'),
                        annotation_text=f'均值: {mean_turnover:.2f}%',
                        annotation_position='top right',
                        row=5, col=1
                    )
            
            fig.update_layout(
                height=1500,  # 调整高度以适应5个子图
                showlegend=True,
                title_text="ETF综合分析图表"
            )
            
            fig.update_yaxes(title_text="价格 (元)", row=1, col=1)
            fig.update_yaxes(title_text="成交额 (亿元)", row=2, col=1)
            fig.update_yaxes(title_text="涨跌幅 (%)", row=3, col=1)
            fig.update_yaxes(title_text="净流入 (亿元)", row=4, col=1)
            fig.update_yaxes(title_text="换手率 (%)", row=5, col=1)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建综合ETF图表失败: {e}")
            return go.Figure()
    
    def create_net_inflow_chart(self, fund_flow_data: pd.DataFrame) -> go.Figure:
        """
        创建净流入趋势图
        :param fund_flow_data: 资金流向数据
        :return: Plotly图表对象
        """
        try:
            if fund_flow_data.empty or '净流入' not in fund_flow_data.columns:
                return go.Figure()
            
            # 确保日期列存在并排序
            if '日期' in fund_flow_data.columns:
                fund_flow_data['日期'] = pd.to_datetime(fund_flow_data['日期'])
                fund_flow_data = fund_flow_data.sort_values('日期')
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=['净流入趋势 (柱状图)', '累计净流入趋势'],
                vertical_spacing=0.1
            )
            
            # 将净流入转换为亿元单位
            net_inflow_in_billions = fund_flow_data['净流入'] / 1e8
            
            # 净流入柱状图：红色表示净流入，绿色表示净流出
            colors = ['#FF4444' if x >= 0 else '#00C851' for x in net_inflow_in_billions]
            
            fig.add_trace(
                go.Bar(
                    x=fund_flow_data['日期'],
                    y=net_inflow_in_billions,
                    name='日净流入',
                    marker_color=colors,
                    hovertemplate='<b>日净流入</b><br>' +
                                 '日期: %{x}<br>' +
                                 '净流入: %{y:.2f}亿元<br>' +
                                 '<extra></extra>'
                ),
                row=1, col=1
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
            
            # 累计净流入趋势线
            if '累计净流入' in fund_flow_data.columns:
                cumulative_inflow = fund_flow_data['累计净流入'] / 1e8
                
                fig.add_trace(
                    go.Scatter(
                        x=fund_flow_data['日期'],
                        y=cumulative_inflow,
                        mode='lines+markers',
                        name='累计净流入',
                        line=dict(color='#2196F3', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(33, 150, 243, 0.1)',
                        hovertemplate='<b>累计净流入</b><br>' +
                                     '日期: %{x}<br>' +
                                     '累计净流入: %{y:.2f}亿元<br>' +
                                     '<extra></extra>'
                    ),
                    row=2, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
            
            fig.update_layout(
                height=800,
                showlegend=True,
                title_text="ETF净流入分析"
            )
            
            fig.update_yaxes(title_text="净流入 (亿元)", row=1, col=1)
            fig.update_yaxes(title_text="累计净流入 (亿元)", row=2, col=1)
            fig.update_xaxes(title_text="日期", row=2, col=1)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建净流入趋势图失败: {e}")
            return go.Figure()
    
    def create_price_change_chart(self, outside_data: pd.DataFrame) -> go.Figure:
        """
        创建价格涨跌幅图表（中国股市颜色习惯）
        :param outside_data: 场外市场数据
        :return: Plotly图表对象
        """
        try:
            if outside_data.empty or '涨跌幅' not in outside_data.columns:
                return go.Figure()
            
            # 确保日期列存在并排序
            if '日期' in outside_data.columns:
                outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                outside_data = outside_data.sort_values('日期')
            
            fig = go.Figure()
            
            # 中国股市颜色习惯：红色表示上涨，绿色表示下跌
            colors = ['#FF4444' if x >= 0 else '#00C851' for x in outside_data['涨跌幅']]
            
            fig.add_trace(
                go.Bar(
                    x=outside_data['日期'],
                    y=outside_data['涨跌幅'],
                    name='涨跌幅',
                    marker_color=colors,
                    hovertemplate='<b>涨跌幅</b><br>' +
                                 '日期: %{x}<br>' +
                                 '涨跌幅: %{y:.2f}%<br>' +
                                 '<extra></extra>'
                )
            )
            
            # 添加零基准线
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            
            # 添加统计信息
            avg_change = outside_data['涨跌幅'].mean()
            max_change = outside_data['涨跌幅'].max()
            min_change = outside_data['涨跌幅'].min()
            
            fig.add_hline(
                y=avg_change,
                line=dict(color='blue', width=1, dash='dot'),
                annotation_text=f'平均: {avg_change:.2f}%',
                annotation_position='top right'
            )
            
            fig.update_layout(
                title="ETF涨跌幅分析（红涨绿跌）",
                xaxis_title="日期",
                yaxis_title="涨跌幅 (%)",
                height=500,
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建价格涨跌幅图表失败: {e}")
            return go.Figure()
    
    def create_price_trend_chart(self, outside_data: pd.DataFrame) -> go.Figure:
        """
        创建价格趋势图表（收盘价和均线）
        :param outside_data: 场外市场数据
        :return: Plotly图表对象
        """
        try:
            if outside_data.empty or '收盘' not in outside_data.columns:
                return go.Figure()
            
            # 确保日期列存在并排序
            if '日期' in outside_data.columns:
                outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                outside_data = outside_data.sort_values('日期')
            
            fig = go.Figure()
            
            # 收盘价线图
            fig.add_trace(
                go.Scatter(
                    x=outside_data['日期'],
                    y=outside_data['收盘'],
                    mode='lines+markers',
                    name='收盘价',
                    line=dict(color='#2196F3', width=3),
                    fill='tonexty',
                    fillcolor='rgba(33, 150, 243, 0.1)',
                    hovertemplate='<b>收盘价</b><br>' +
                                 '日期: %{x}<br>' +
                                 '收盘价: %{y:.3f}元<br>' +
                                 '<extra></extra>'
                )
            )
            
            # 添加移动平均线
            if len(outside_data) >= 5:
                ma5 = outside_data['收盘'].rolling(window=5, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=outside_data['日期'],
                        y=ma5,
                        mode='lines',
                        name='5日均线',
                        line=dict(color='#FF9800', width=2, dash='dash'),
                        hovertemplate='<b>5日均线</b><br>' +
                                     '日期: %{x}<br>' +
                                     '均价: %{y:.3f}元<br>' +
                                     '<extra></extra>'
                    )
                )
            
            if len(outside_data) >= 10:
                ma10 = outside_data['收盘'].rolling(window=10, min_periods=1).mean()
                fig.add_trace(
                    go.Scatter(
                        x=outside_data['日期'],
                        y=ma10,
                        mode='lines',
                        name='10日均线',
                        line=dict(color='#9C27B0', width=2, dash='dot'),
                        hovertemplate='<b>10日均线</b><br>' +
                                     '日期: %{x}<br>' +
                                     '均价: %{y:.3f}元<br>' +
                                     '<extra></extra>'
                    )
                )
            
            # 添加统计信息
            current_price = outside_data['收盘'].iloc[-1]
            max_price = outside_data['收盘'].max()
            min_price = outside_data['收盘'].min()
            
            fig.update_layout(
                title="ETF价格趋势分析",
                xaxis_title="日期",
                yaxis_title="价格 (元)",
                height=500,
                showlegend=True,
                annotations=[
                    dict(
                        x=0.02, y=0.98,
                        xref='paper', yref='paper',
                        text=f'当前价格: {current_price:.3f}元<br>期间最高: {max_price:.3f}元<br>期间最低: {min_price:.3f}元',
                        showarrow=False,
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='gray',
                        borderwidth=1
                    )
                ]
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建价格趋势图表失败: {e}")
            return go.Figure()


# 工厂函数
def create_etf_visualizer() -> ETFVisualizer:
    """创建ETF数据可视化器实例"""
    return ETFVisualizer()