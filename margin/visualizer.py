"""
两融数据可视化模块 - A股两融交易查询系统
生成两融交易数据的图表和仪表板
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CHART_CONFIG, MARGIN_TRADING_CONFIG, STORAGE_CONFIG
from utils import format_number, ensure_directories

# 设置中文字体 - macOS优化
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
# 设置字体大小
plt.rcParams['font.size'] = 10

class MarginDataVisualizer:
    """两融数据可视化器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        from config import STORAGE_CONFIG
        self.output_dir = STORAGE_CONFIG['output_dir']
        ensure_directories()
        
        # 设置绘图风格
        plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
        sns.set_palette(CHART_CONFIG['color_palette'])
    
    def create_margin_balance_chart(self, df: pd.DataFrame, 
                                  save_path: Optional[str] = None) -> str:
        """
        创建两融余额趋势图
        :param df: 包含两融数据的DataFrame
        :param save_path: 保存路径
        :return: 图表文件路径
        """
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=CHART_CONFIG['figure_size'], 
                                         dpi=CHART_CONFIG['dpi'])
            
            # 确保日期列为datetime类型
            if '交易日期' in df.columns:
                df['交易日期'] = pd.to_datetime(df['交易日期'])
                dates = df['交易日期']
            else:
                dates = range(len(df))
            
            # 第一个子图：两融余额趋势
            if '两融余额' in df.columns:
                ax1.plot(dates, df['两融余额'] / 1e8, label='两融余额', 
                        linewidth=2, color='#FF6B6B')
            
            if '融资余额' in df.columns:
                ax1.plot(dates, df['融资余额'] / 1e8, label='融资余额', 
                        linewidth=1.5, color='#4ECDC4', alpha=0.8)
            
            if '融券余额' in df.columns:
                ax1.plot(dates, df['融券余额'] / 1e8, label='融券余额', 
                        linewidth=1.5, color='#45B7D1', alpha=0.8)
            
            ax1.set_title('A股两融余额趋势图', fontsize=16, fontweight='bold')
            ax1.set_ylabel('余额 (亿元)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 第二个子图：两融余额变化率
            if '两融余额_日变化率' in df.columns:
                ax2.bar(dates, df['两融余额_日变化率'], 
                       color=['green' if x > 0 else 'red' for x in df['两融余额_日变化率']],
                       alpha=0.7, width=0.8)
                ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            ax2.set_title('两融余额日变化率', fontsize=14)
            ax2.set_ylabel('变化率 (%)', fontsize=12)
            ax2.set_xlabel('日期', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            # 格式化日期轴
            if '交易日期' in df.columns:
                for ax in [ax1, ax2]:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # 保存图表
            if save_path is None:
                save_path = os.path.join(self.output_dir, 
                                       f"margin_balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            plt.savefig(save_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.logger.info(f"两融余额趋势图已保存: {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"创建两融余额趋势图失败: {e}")
            return ""
    
    def create_margin_ratio_chart(self, df: pd.DataFrame, 
                                save_path: Optional[str] = None) -> str:
        """
        创建两融占比分析图
        :param df: 包含占比数据的DataFrame
        :param save_path: 保存路径
        :return: 图表文件路径
        """
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12), 
                                                        dpi=CHART_CONFIG['dpi'])
            
            dates = pd.to_datetime(df['交易日期']) if '交易日期' in df.columns else range(len(df))
            
            # 融资融券结构占比
            if '融资占两融比例' in df.columns and '融券占两融比例' in df.columns:
                ax1.fill_between(dates, 0, df['融资占两融比例'], 
                               label='融资占比', color='#FF6B6B', alpha=0.7)
                ax1.fill_between(dates, df['融资占两融比例'], 100, 
                               label='融券占比', color='#4ECDC4', alpha=0.7)
                ax1.set_title('融资融券结构占比', fontsize=14, fontweight='bold')
                ax1.set_ylabel('占比 (%)', fontsize=12)
                ax1.legend()
                ax1.grid(True, alpha=0.3)
            
            # 两融余额移动平均线
            ma_columns = [col for col in df.columns if '两融余额_MA' in col and '偏离度' not in col]
            if ma_columns and '两融余额' in df.columns:
                ax2.plot(dates, df['两融余额'] / 1e8, label='两融余额', 
                        linewidth=2, color='black')
                
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                for i, col in enumerate(ma_columns[:4]):
                    ax2.plot(dates, df[col] / 1e8, 
                           label=col.replace('两融余额_', ''), 
                           linewidth=1, color=colors[i % len(colors)], alpha=0.8)
                
                ax2.set_title('两融余额与移动平均线', fontsize=14, fontweight='bold')
                ax2.set_ylabel('余额 (亿元)', fontsize=12)
                ax2.legend()
                ax2.grid(True, alpha=0.3)
            
            # RSI指标
            if '两融余额_RSI' in df.columns:
                ax3.plot(dates, df['两融余额_RSI'], linewidth=2, color='#45B7D1')
                ax3.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='超买线(70)')
                ax3.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='超卖线(30)')
                ax3.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='中位线(50)')
                ax3.fill_between(dates, 70, 100, alpha=0.2, color='red', label='超买区')
                ax3.fill_between(dates, 0, 30, alpha=0.2, color='green', label='超卖区')
                
                ax3.set_title('两融余额RSI指标', fontsize=14, fontweight='bold')
                ax3.set_ylabel('RSI', fontsize=12)
                ax3.set_ylim(0, 100)
                ax3.legend()
                ax3.grid(True, alpha=0.3)
            
            # 布林带
            bollinger_cols = [col for col in df.columns if '两融余额_布林' in col]
            if len(bollinger_cols) >= 3 and '两融余额' in df.columns:
                # 找到上轨、中轨、下轨
                upper_col = next((col for col in bollinger_cols if '上轨' in col), None)
                middle_col = next((col for col in bollinger_cols if '中轨' in col), None)
                lower_col = next((col for col in bollinger_cols if '下轨' in col), None)
                
                if all([upper_col, middle_col, lower_col]):
                    ax4.plot(dates, df['两融余额'] / 1e8, label='两融余额', 
                           linewidth=2, color='black')
                    ax4.plot(dates, df[upper_col] / 1e8, label='布林上轨', 
                           linewidth=1, color='red', linestyle='--', alpha=0.8)
                    ax4.plot(dates, df[middle_col] / 1e8, label='布林中轨', 
                           linewidth=1, color='blue', alpha=0.8)
                    ax4.plot(dates, df[lower_col] / 1e8, label='布林下轨', 
                           linewidth=1, color='green', linestyle='--', alpha=0.8)
                    
                    # 填充布林带
                    ax4.fill_between(dates, df[upper_col] / 1e8, df[lower_col] / 1e8, 
                                   alpha=0.1, color='gray')
                    
                    ax4.set_title('两融余额布林带', fontsize=14, fontweight='bold')
                    ax4.set_ylabel('余额 (亿元)', fontsize=12)
                    ax4.legend()
                    ax4.grid(True, alpha=0.3)
            
            # 格式化日期轴
            if '交易日期' in df.columns:
                for ax in [ax1, ax2, ax3, ax4]:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # 保存图表
            if save_path is None:
                save_path = os.path.join(self.output_dir, 
                                       f"margin_ratio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            plt.savefig(save_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.logger.info(f"两融占比分析图已保存: {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"创建两融占比分析图失败: {e}")
            return ""
    
    def create_interactive_dashboard(self, df: pd.DataFrame, 
                                   save_path: Optional[str] = None) -> str:
        """
        创建交互式仪表板
        :param df: 数据DataFrame
        :param save_path: 保存路径
        :return: HTML文件路径
        """
        try:
            # 创建子图
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=['两融余额趋势', '融资融券结构', 
                              '余额变化率', 'RSI指标',
                              '成交占比', '移动平均偏离度'],
                specs=[[{"secondary_y": False}, {"type": "pie"}],
                       [{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            dates = pd.to_datetime(df['交易日期']) if '交易日期' in df.columns else list(range(len(df)))
            
            # 1. 两融余额趋势
            if '两融余额' in df.columns:
                fig.add_trace(
                    go.Scatter(x=dates, y=df['两融余额']/1e8, 
                             name='两融余额', line=dict(color='#FF6B6B', width=2)),
                    row=1, col=1
                )
            
            if '融资余额' in df.columns:
                fig.add_trace(
                    go.Scatter(x=dates, y=df['融资余额']/1e8, 
                             name='融资余额', line=dict(color='#4ECDC4', width=1.5)),
                    row=1, col=1
                )
            
            # 2. 融资融券结构饼图（使用最新数据）
            if '融资余额' in df.columns and '融券余额' in df.columns and len(df) > 0:
                latest_financing = df['融资余额'].iloc[-1]
                latest_shorting = df['融券余额'].iloc[-1]
                
                fig.add_trace(
                    go.Pie(labels=['融资', '融券'], 
                          values=[latest_financing, latest_shorting],
                          marker_colors=['#FF6B6B', '#4ECDC4']),
                    row=1, col=2
                )
            
            # 3. 余额变化率
            if '两融余额_日变化率' in df.columns:
                colors = ['green' if x > 0 else 'red' for x in df['两融余额_日变化率']]
                fig.add_trace(
                    go.Bar(x=dates, y=df['两融余额_日变化率'], 
                          name='日变化率', marker_color=colors),
                    row=2, col=1
                )
            
            # 4. RSI指标
            if '两融余额_RSI' in df.columns:
                fig.add_trace(
                    go.Scatter(x=dates, y=df['两融余额_RSI'], 
                             name='RSI', line=dict(color='#45B7D1', width=2)),
                    row=2, col=2
                )
                
                # 添加RSI基准线
                fig.add_hline(y=70, line_dash="dash", line_color="red", 
                            annotation_text="超买线", row=2, col=2)
                fig.add_hline(y=30, line_dash="dash", line_color="green", 
                            annotation_text="超卖线", row=2, col=2)
            
            # 5. 成交占比（如果有市场数据）
            if '两融余额占市场成交比' in df.columns:
                fig.add_trace(
                    go.Scatter(x=dates, y=df['两融余额占市场成交比'], 
                             name='两融占市场成交比', line=dict(color='#96CEB4', width=2)),
                    row=3, col=1
                )
            
            # 6. 移动平均偏离度
            deviation_cols = [col for col in df.columns if 'MA20_偏离度' in col]
            if deviation_cols:
                col_name = deviation_cols[0]
                fig.add_trace(
                    go.Scatter(x=dates, y=df[col_name], 
                             name='MA20偏离度', line=dict(color='#FFEAA7', width=2)),
                    row=3, col=2
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=2)
            
            # 更新布局
            fig.update_layout(
                title='A股两融交易分析仪表板',
                title_x=0.5,
                height=1200,
                showlegend=True,
                template='plotly_white'
            )
            
            # 更新y轴标签
            fig.update_yaxes(title_text="余额 (亿元)", row=1, col=1)
            fig.update_yaxes(title_text="变化率 (%)", row=2, col=1)
            fig.update_yaxes(title_text="RSI", row=2, col=2)
            fig.update_yaxes(title_text="占比 (%)", row=3, col=1)
            fig.update_yaxes(title_text="偏离度 (%)", row=3, col=2)
            
            # 保存HTML文件
            if save_path is None:
                save_path = os.path.join(self.output_dir, 
                                       f"margin_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
            
            fig.write_html(save_path)
            
            self.logger.info(f"交互式仪表板已保存: {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"创建交互式仪表板失败: {e}")
            return ""
    
    def create_correlation_heatmap(self, df: pd.DataFrame, 
                                 save_path: Optional[str] = None) -> str:
        """
        创建相关性热力图
        :param df: 数据DataFrame
        :param save_path: 保存路径
        :return: 图表文件路径
        """
        try:
            # 选择数值列
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            
            # 过滤掉一些不需要的列
            exclude_patterns = ['_日变化', '_周变化', '_月变化', 'MA', 'RSI', '布林']
            filtered_columns = []
            
            for col in numeric_columns:
                if not any(pattern in col for pattern in exclude_patterns):
                    filtered_columns.append(col)
            
            if len(filtered_columns) < 2:
                self.logger.warning("数值列不足，无法创建相关性热力图")
                return ""
            
            # 计算相关性矩阵
            corr_matrix = df[filtered_columns].corr()
            
            # 创建热力图
            plt.figure(figsize=(10, 8), dpi=CHART_CONFIG['dpi'])
            
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
            
            sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='RdYlBu_r', 
                       center=0, square=True, linewidths=0.5, 
                       cbar_kws={"shrink": .8}, fmt='.2f')
            
            plt.title('两融数据相关性分析', fontsize=16, fontweight='bold')
            plt.tight_layout()
            
            # 保存图表
            if save_path is None:
                save_path = os.path.join(self.output_dir, 
                                       f"margin_correlation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            plt.savefig(save_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.logger.info(f"相关性热力图已保存: {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"创建相关性热力图失败: {e}")
            return ""
    
    def create_summary_chart(self, analysis_result: Dict, 
                           save_path: Optional[str] = None) -> str:
        """
        创建汇总图表
        :param analysis_result: 分析结果字典
        :param save_path: 保存路径
        :return: 图表文件路径
        """
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12), 
                                                        dpi=CHART_CONFIG['dpi'])
            
            # 1. 两融余额概况
            if '两融余额分析' in analysis_result:
                balance_data = analysis_result['两融余额分析']
                labels = ['最低余额', '平均余额', '最高余额', '最新余额']
                values = []
                
                for label in labels:
                    value_str = balance_data.get(label.replace('余额', ''), '0')
                    # 提取数字部分
                    if '亿' in value_str:
                        value = float(value_str.replace('亿', '').replace(',', ''))
                    elif '万' in value_str:
                        value = float(value_str.replace('万', '').replace(',', '')) / 10000
                    else:
                        value = float(value_str.replace(',', '')) / 1e8 if value_str.replace(',', '').replace('.', '').isdigit() else 0
                    values.append(value)
                
                bars = ax1.bar(labels, values, color=CHART_CONFIG['color_palette'][:4])
                ax1.set_title('两融余额概况 (亿元)', fontsize=14, fontweight='bold')
                ax1.set_ylabel('余额 (亿元)', fontsize=12)
                
                # 添加数值标签
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                           f'{value:.1f}', ha='center', va='bottom')
            
            # 2. 融资融券结构
            if '融资融券结构' in analysis_result:
                structure_data = analysis_result['融资融券结构']
                financing_ratio = float(structure_data.get('融资占比', '0%').replace('%', ''))
                shorting_ratio = float(structure_data.get('融券占比', '0%').replace('%', ''))
                
                sizes = [financing_ratio, shorting_ratio]
                labels = ['融资', '融券']
                colors = ['#FF6B6B', '#4ECDC4']
                
                wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors, 
                                                  autopct='%1.1f%%', startangle=90)
                ax2.set_title('融资融券结构占比', fontsize=14, fontweight='bold')
            
            # 3. 趋势分析
            if '趋势分析' in analysis_result:
                trend_data = analysis_result['趋势分析']
                change_rate = trend_data.get('近5日平均变化率', '0%').replace('%', '')
                try:
                    change_value = float(change_rate)
                except:
                    change_value = 0
                
                color = 'green' if change_value > 0 else 'red' if change_value < 0 else 'gray'
                ax3.bar(['近5日平均变化率'], [change_value], color=color, alpha=0.7)
                ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                ax3.set_title('趋势分析', fontsize=14, fontweight='bold')
                ax3.set_ylabel('变化率 (%)', fontsize=12)
                
                # 添加趋势判断文本
                trend_judgment = trend_data.get('趋势判断', '')
                ax3.text(0, change_value + (abs(change_value) * 0.1 if change_value != 0 else 0.1), 
                        trend_judgment, ha='center', va='bottom', fontsize=12, fontweight='bold')
            
            # 4. 风险评估
            if '风险评估' in analysis_result:
                risk_data = analysis_result['风险评估']
                rsi_value = risk_data.get('RSI指标', '50')
                try:
                    rsi = float(rsi_value)
                except:
                    rsi = 50
                
                # RSI表盘
                theta = np.linspace(0, 2 * np.pi, 100)
                r = np.ones_like(theta)
                
                # 绘制RSI表盘背景
                ax4.plot(theta, r, 'k-', alpha=0.3)
                
                # 标记RSI值
                rsi_angle = (rsi / 100) * 2 * np.pi
                ax4.plot([rsi_angle, rsi_angle], [0, 1], 'r-', linewidth=4)
                ax4.plot(rsi_angle, 1, 'ro', markersize=10)
                
                # 添加标签
                ax4.text(0, 0, f'RSI: {rsi:.1f}', ha='center', va='center', 
                        fontsize=16, fontweight='bold')
                ax4.text(0, -0.3, risk_data.get('风险等级', ''), ha='center', va='center', 
                        fontsize=12)
                
                ax4.set_xlim(-1.5, 1.5)
                ax4.set_ylim(-1.5, 1.5)
                ax4.set_aspect('equal')
                ax4.axis('off')
                ax4.set_title('风险评估 (RSI)', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            
            # 保存图表
            if save_path is None:
                save_path = os.path.join(self.output_dir, 
                                       f"margin_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            plt.savefig(save_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.logger.info(f"汇总图表已保存: {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"创建汇总图表失败: {e}")
            return ""

# 工厂函数
def create_margin_visualizer() -> MarginDataVisualizer:
    """创建两融数据可视化器实例"""
    return MarginDataVisualizer()