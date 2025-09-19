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
                rows=3, cols=1,
                subplot_titles=['成交额趋势', '涨跌幅', '换手率变化'],
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
                    row=2, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
            
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
                    row=3, col=1
                )
                
                # 添加换手率均值线
                if len(turnover_rates) > 0:
                    mean_turnover = turnover_rates.mean()
                    fig.add_hline(
                        y=mean_turnover,
                        line=dict(color='red', width=1, dash='dash'),
                        annotation_text=f'均值: {mean_turnover:.2f}%',
                        annotation_position='top right',
                        row=3, col=1
                    )
            
            fig.update_layout(
                height=900,  # 调整高度以适应3个子图
                showlegend=True,
                title_text="ETF综合分析图表"
            )
            
            fig.update_yaxes(title_text="成交额 (亿元)", row=1, col=1)
            fig.update_yaxes(title_text="涨跌幅 (%)", row=2, col=1)
            fig.update_yaxes(title_text="换手率 (%)", row=3, col=1)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"创建综合ETF图表失败: {e}")
            return go.Figure()
    

    

    


# 工厂函数
def create_etf_visualizer() -> ETFVisualizer:
    """创建ETF数据可视化器实例"""
    return ETFVisualizer()