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
    
    def create_fund_flow_chart(self, fund_flow_data: pd.DataFrame) -> go.Figure:
        """
        创建资金流向图表
        :param fund_flow_data: 资金流向数据
        :return: Plotly图表对象
        """
        try:
            if fund_flow_data.empty:
                return go.Figure()
            
            # 确保日期列格式正确
            if '日期' in fund_flow_data.columns:
                fund_flow_data['日期'] = pd.to_datetime(fund_flow_data['日期'])
                fund_flow_data = fund_flow_data.sort_values('日期')
            
            fig = go.Figure()
            
            # 添加成交额数据
            if '成交额' in fund_flow_data.columns:
                # 将成交额转换为亿元单位
                turnover_in_billions = fund_flow_data['成交额'] / 1e8
                fig.add_trace(go.Scatter(
                    x=fund_flow_data['日期'],
                    y=turnover_in_billions,
                    mode='lines+markers',
                    name='成交额',
                    line=dict(color=self.color_palette[0], width=2),
                    fill='tozeroy',
                    fillcolor=f'rgba{tuple(list(px.colors.hex_to_rgb(self.color_palette[0])) + [0.3])}',
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                 '日期: %{x}<br>' +
                                 '成交额: %{y:.2f}亿元<br>' +
                                 '<extra></extra>'
                ))
            
            # 添加零线
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            
            fig.update_layout(
                title="ETF成交额趋势",
                xaxis_title="日期",
                yaxis_title="成交额 (亿元)",
                height=400,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建资金流向图表失败: {e}")
            return go.Figure()
    
    def create_share_change_chart(self, share_change_data: pd.DataFrame) -> go.Figure:
        """
        创建份额变动图表（基于成交量分析）
        :param share_change_data: 份额变动数据
        :return: Plotly图表对象
        """
        try:
            if share_change_data.empty:
                return go.Figure()
            
            # 确保日期列格式正确
            if '日期' in share_change_data.columns:
                share_change_data['日期'] = pd.to_datetime(share_change_data['日期'])
                share_change_data = share_change_data.sort_values('日期')
            
            fig = go.Figure()
            
            # 添加成交量数据（作为份额活跃度的代理指标）
            if '成交量' in share_change_data.columns:
                # 将成交量转换为万手单位
                volume_in_millions = share_change_data['成交量'] / 1e6
                fig.add_trace(go.Scatter(
                    x=share_change_data['日期'],
                    y=volume_in_millions,
                    mode='lines+markers',
                    name='成交量',
                    line=dict(color=self.color_palette[1], width=2),
                    fill='tozeroy',
                    fillcolor=f'rgba{tuple(list(px.colors.hex_to_rgb(self.color_palette[1])) + [0.3])}',
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                 '日期: %{x}<br>' +
                                 '成交量: %{y:.2f}万手<br>' +
                                 '<extra></extra>'
                ))
            
            fig.update_layout(
                title="ETF份额活跃度趋势（基于成交量）",
                xaxis_title="日期",
                yaxis_title="成交量 (万手)",
                height=400,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建份额变动图表失败: {e}")
            return go.Figure()
    
    def create_subscription_redemption_chart(self, outside_data: pd.DataFrame) -> go.Figure:
        """
        创建涨跌幅图表
        :param outside_data: 场外市场数据
        :return: Plotly图表对象
        """
        try:
            if outside_data.empty:
                return go.Figure()
            
            # 确保日期列格式正确
            if '日期' in outside_data.columns:
                outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                outside_data = outside_data.sort_values('日期')
            
            fig = go.Figure()
            
            # 添加涨跌幅数据
            if '涨跌幅' in outside_data.columns:
                fig.add_trace(go.Bar(
                    x=outside_data['日期'],
                    y=outside_data['涨跌幅'],
                    name='涨跌幅',
                    marker_color=[self.color_palette[2] if x >= 0 else self.color_palette[0] for x in outside_data['涨跌幅']],
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                 '日期: %{x}<br>' +
                                 '涨跌幅: %{y:.2f}%<br>' +
                                 '<extra></extra>'
                ))
            
            # 添加零线
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            
            fig.update_layout(
                title="ETF涨跌幅情况",
                xaxis_title="日期",
                yaxis_title="涨跌幅 (%)",
                height=400,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建涨跌幅图表失败: {e}")
            return go.Figure()
    
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
                rows=3, cols=1,
                subplot_titles=['成交额趋势', '份额活跃度趋势（基于成交量）', '涨跌幅'],
                vertical_spacing=0.08
            )
            
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
                    row=1, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
            
            # 份额活跃度趋势子图（基于成交量）
            if not share_change_data.empty and '成交量' in share_change_data.columns:
                if '日期' in share_change_data.columns:
                    share_change_data['日期'] = pd.to_datetime(share_change_data['日期'])
                    share_change_data = share_change_data.sort_values('日期')
                
                # 将成交量转换为万手单位
                volume_in_millions = share_change_data['成交量'] / 1e6
                fig.add_trace(
                    go.Scatter(
                        x=share_change_data['日期'],
                        y=volume_in_millions,
                        mode='lines+markers',
                        name='成交量',
                        line=dict(color=self.color_palette[1], width=2),
                        fill='tozeroy',
                        fillcolor=f'rgba{tuple(list(px.colors.hex_to_rgb(self.color_palette[1])) + [0.3])}'
                    ),
                    row=2, col=1
                )
            
            # 涨跌幅子图
            if not outside_data.empty and '涨跌幅' in outside_data.columns:
                if '日期' in outside_data.columns:
                    outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                    outside_data = outside_data.sort_values('日期')
                
                fig.add_trace(
                    go.Bar(
                        x=outside_data['日期'],
                        y=outside_data['涨跌幅'],
                        name='涨跌幅',
                        marker_color=[self.color_palette[2] if x >= 0 else self.color_palette[0] for x in outside_data['涨跌幅']]
                    ),
                    row=3, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)
            
            fig.update_layout(
                height=900,
                showlegend=True,
                title_text="ETF综合分析图表"
            )
            
            fig.update_yaxes(title_text="成交额 (亿元)", row=1, col=1)
            fig.update_yaxes(title_text="成交量 (万手)", row=2, col=1)
            fig.update_yaxes(title_text="涨跌幅 (%)", row=3, col=1)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建综合ETF图表失败: {e}")
            return go.Figure()
    
    def create_etf_realtime_valuation_chart(self, minute_data: pd.DataFrame) -> go.Figure:
        """
        创建ETF实时估值与最近价格变化趋势图
        :param minute_data: 分钟级别数据
        :return: Plotly图表对象
        """
        try:
            if minute_data.empty:
                self.logger.warning("分钟数据为空，无法创建实时估值图表")
                # 创建一个空图表提示
                fig = go.Figure()
                fig.add_annotation(
                    x=0.5, y=0.5,
                    xref="paper", yref="paper",
                    text="暂无分钟级别数据",
                    showarrow=False,
                    font=dict(size=16)
                )
                fig.update_layout(
                    title="ETF实时估值与价格变化趋势",
                    height=400
                )
                return fig
            
            # 确保时间列格式正确
            if '时间' in minute_data.columns:
                minute_data['时间'] = pd.to_datetime(minute_data['时间'])
                minute_data = minute_data.sort_values('时间')
            
            # 只保留当天数据
            today = pd.Timestamp.now().normalize()
            if '时间' in minute_data.columns:
                minute_data = minute_data[minute_data['时间'].dt.date == today.date()]
            
            # 过滤掉休市时间（11:30-13:00）
            if '时间' in minute_data.columns and not minute_data.empty:
                # 创建上午和下午两个时间段的掩码
                morning_mask = minute_data['时间'].dt.time <= pd.Timestamp("11:30").time()
                afternoon_mask = minute_data['时间'].dt.time >= pd.Timestamp("13:00").time()
                # 只保留上午和下午的数据，过滤掉休市时间
                minute_data = minute_data[morning_mask | afternoon_mask]
            
            # 获取日期用于标题显示
            display_date = today.strftime('%Y-%m-%d') if not minute_data.empty else today.strftime('%Y-%m-%d')
            
            fig = go.Figure()
            
            # 添加收盘价数据
            if '收盘' in minute_data.columns and not minute_data.empty:
                # 确保数据类型正确
                close_prices = pd.to_numeric(minute_data['收盘'], errors='coerce').dropna()
                times = minute_data.loc[close_prices.index, '时间'] if not close_prices.empty else []
                
                if not close_prices.empty and not times.empty:
                    fig.add_trace(go.Scatter(
                        x=times,
                        y=close_prices,
                        mode='lines+markers',
                        name='收盘价',
                        line=dict(color=self.color_palette[0], width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '时间: %{x}<br>' +
                                     '价格: %{y:.4f}元<br>' +
                                     '<extra></extra>'
                    ))
            
            # 添加均价数据（作为实时估值的近似）
            if '均价' in minute_data.columns and not minute_data.empty:
                # 确保数据类型正确
                avg_prices = pd.to_numeric(minute_data['均价'], errors='coerce').dropna()
                times = minute_data.loc[avg_prices.index, '时间'] if not avg_prices.empty else []
                
                if not avg_prices.empty and not times.empty:
                    fig.add_trace(go.Scatter(
                        x=times,
                        y=avg_prices,
                        mode='lines+markers',
                        name='均价（实时估值）',
                        line=dict(color=self.color_palette[1], width=2, dash='dash'),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '时间: %{x}<br>' +
                                     '价格: %{y:.4f}元<br>' +
                                     '<extra></extra>'
                    ))
            
            # 设置横轴时间格式，只显示到分钟级别
            xaxis_format = dict(
                type='date',
                tickformat='%H:%M',
                dtick=300000,  # 5分钟间隔（300000毫秒）
                tickangle=45
            )
            
            fig.update_layout(
                title=f"ETF实时估值与价格变化趋势 ({display_date})",
                xaxis_title="时间",
                yaxis_title="价格 (元)",
                height=400,
                showlegend=True,
                xaxis=xaxis_format
            )
            
            # 如果没有任何数据，添加提示信息
            if len(fig.data) == 0:
                fig.add_annotation(
                    x=0.5, y=0.5,
                    xref="paper", yref="paper",
                    text="暂无有效数据",
                    showarrow=False,
                    font=dict(size=16)
                )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建实时估值图表失败: {e}")
            # 返回错误提示图表
            fig = go.Figure()
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text="图表生成失败",
                showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(
                title="ETF实时估值与价格变化趋势",
                height=400
            )
            return fig
    
    def create_turnover_rate_chart(self, minute_data: pd.DataFrame) -> go.Figure:
        """
        创建换手率变化曲线图（按日聚合）
        :param minute_data: 分钟级别数据
        :return: Plotly图表对象
        """
        try:
            if minute_data.empty:
                self.logger.warning("分钟数据为空，无法创建换手率图表")
                # 创建一个空图表提示
                fig = go.Figure()
                fig.add_annotation(
                    x=0.5, y=0.5,
                    xref="paper", yref="paper",
                    text="暂无分钟级别数据",
                    showarrow=False,
                    font=dict(size=16)
                )
                fig.update_layout(
                    title="ETF换手率变化曲线",
                    height=400
                )
                return fig
            
            # 确保时间列格式正确
            if '时间' in minute_data.columns:
                minute_data['时间'] = pd.to_datetime(minute_data['时间'])
                minute_data = minute_data.sort_values('时间')
            
            # 按日期聚合数据，计算每日换手率
            if '时间' in minute_data.columns and all(col in minute_data.columns for col in ['成交量', '成交额', '收盘']):
                # 按日期分组
                minute_data['日期'] = minute_data['时间'].dt.date
                daily_data = minute_data.groupby('日期').agg({
                    '成交量': 'sum',
                    '成交额': 'sum',
                    '收盘': 'last'  # 取当日最后收盘价
                }).reset_index()
                
                # 计算每日换手率
                daily_turnover_rates = []
                dates = []
                
                for _, row in daily_data.iterrows():
                    volume = row['成交量']
                    amount = row['成交额']
                    close_price = row['收盘']
                    
                    # 避免除以0
                    if amount != 0 and close_price != 0:
                        # 换手率 = 成交量 / (成交额 / 收盘价) * 100%
                        turnover_rate = (volume / (amount / close_price)) * 100
                        daily_turnover_rates.append(turnover_rate)
                        dates.append(row['日期'])
                
                if daily_turnover_rates:
                    fig = go.Figure()
                    
                    # 添加换手率数据
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=daily_turnover_rates,
                        mode='lines+markers',
                        name='换手率',
                        line=dict(color=self.color_palette[0], width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '换手率: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    ))
                    
                    # 计算并添加均值虚线
                    mean_turnover = sum(daily_turnover_rates) / len(daily_turnover_rates)
                    fig.add_hline(
                        y=mean_turnover,
                        line=dict(color='red', width=1, dash='dash'),
                        annotation_text=f'均值: {mean_turnover:.2f}%',
                        annotation_position='bottom right'
                    )
                    
                    fig.update_layout(
                        title="ETF换手率变化曲线",
                        xaxis_title="日期",
                        yaxis_title="换手率 (%)",
                        height=400,
                        showlegend=True
                    )
                    
                    return fig
            
            # 如果缺少必要的列或无法计算换手率，显示提示信息
            fig = go.Figure()
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text="数据不足，无法计算换手率",
                showarrow=False,
                font=dict(size=16)
            )
            
            fig.update_layout(
                title="ETF换手率变化曲线",
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建换手率图表失败: {e}")
            # 返回错误提示图表
            fig = go.Figure()
            fig.add_annotation(
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                text="图表生成失败",
                showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(
                title="ETF换手率变化曲线",
                height=400
            )
            return fig
    


# 工厂函数
def create_etf_visualizer() -> ETFVisualizer:
    """创建ETF数据可视化器实例"""
    return ETFVisualizer()