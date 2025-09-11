"""
Web界面 - A股两融交易查询系统
基于Streamlit的Web应用程序
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import MARGIN_TRADING_CONFIG
from utils import setup_logging, ensure_directories, format_number
from data_fetcher import create_margin_fetcher
from data_processor import create_margin_processor
from visualizer import create_margin_visualizer

# 页面配置
st.set_page_config(
    page_title="A股两融交易查询系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class MarginTradingWebApp:
    """两融交易Web应用"""
    
    def __init__(self):
        self._initialize_app()
        if 'app_initialized' not in st.session_state:
            st.session_state.app_initialized = True
    
    def _initialize_app(self):
        """初始化应用"""
        # 设置日志
        self.logger = setup_logging()
        
        # 确保目录存在
        ensure_directories()
        
        # 初始化组件
        self.data_fetcher = create_margin_fetcher()
        self.data_processor = create_margin_processor()
        self.visualizer = create_margin_visualizer()
        
        # 初始化session state
        if 'margin_data' not in st.session_state:
            st.session_state.margin_data = pd.DataFrame()
        if 'processed_data' not in st.session_state:
            st.session_state.processed_data = pd.DataFrame()
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = {}
    
    def show_header(self):
        """显示页面头部"""
        st.markdown('<div class="main-header">📊 A股两融交易查询系统</div>', 
                   unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
            <h4>🎯 系统功能</h4>
            <ul>
                <li>📈 查询A股市场两融交易数据</li>
                <li>📊 分析两融余额趋势和占比</li>
                <li>📉 生成专业的数据可视化图表</li>
                <li>📋 导出详细的分析报告</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    def show_sidebar(self):
        """显示侧边栏配置"""
        st.sidebar.header("🔧 查询配置")
        
        # 日期范围选择
        st.sidebar.subheader("📅 日期范围")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=30),
                max_value=datetime.now()
            )
        
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
                max_value=datetime.now()
            )
        
        # 查询选项
        st.sidebar.subheader("⚙️ 查询选项")
        
        use_cache = st.sidebar.checkbox("使用缓存数据", value=True, 
                                       help="使用缓存可以加快查询速度")
        
        export_format = st.sidebar.selectbox(
            "导出格式",
            ["CSV", "Excel", "JSON"],
            index=0
        )
        
        # 图表选项
        st.sidebar.subheader("📊 图表选项")
        
        show_balance_chart = st.sidebar.checkbox("余额趋势图", value=True)
        show_ratio_chart = st.sidebar.checkbox("占比分析图", value=True)
        show_correlation = st.sidebar.checkbox("相关性分析", value=False)
        show_dashboard = st.sidebar.checkbox("交互式仪表板", value=True)
        
        # 查询按钮
        query_button = st.sidebar.button("🚀 开始查询", type="primary")
        
        return {
            'start_date': start_date.strftime('%Y%m%d'),
            'end_date': end_date.strftime('%Y%m%d'),
            'use_cache': use_cache,
            'export_format': export_format.lower(),
            'show_balance_chart': show_balance_chart,
            'show_ratio_chart': show_ratio_chart,
            'show_correlation': show_correlation,
            'show_dashboard': show_dashboard,
            'query_button': query_button
        }
    
    def query_data(self, config):
        """查询数据"""
        try:
            with st.spinner("正在获取两融数据..."):
                # 获取两融数据
                margin_data = self.data_fetcher.get_margin_trading_summary(
                    config['start_date'], 
                    config['end_date'],
                    use_cache=config['use_cache']
                )
                
                if margin_data.empty:
                    st.error("❌ 未获取到数据，请检查网络连接或数据源")
                    return False
                
                st.session_state.margin_data = margin_data
                
            with st.spinner("正在获取市场数据..."):
                # 获取市场数据
                market_data = self.data_fetcher.get_market_turnover(
                    config['start_date'], 
                    config['end_date']
                )
                
            with st.spinner("正在处理数据..."):
                # 处理数据
                processed_data = self.data_processor.process_margin_summary(
                    margin_data, market_data
                )
                st.session_state.processed_data = processed_data
                
                # 生成分析结果
                analysis_result = self.data_processor.analyze_margin_trends(processed_data)
                st.session_state.analysis_result = analysis_result
                
            st.success(f"✅ 成功获取并处理了 {len(processed_data)} 条数据记录")
            return True
            
        except Exception as e:
            st.error(f"❌ 查询失败: {str(e)}")
            return False
    
    def show_summary_metrics(self):
        """显示汇总指标"""
        if st.session_state.analysis_result:
            st.subheader("📊 数据概览")
            
            analysis = st.session_state.analysis_result
            
            # 创建指标列
            col1, col2, col3, col4 = st.columns(4)
            
            # 数据概况
            if '数据概况' in analysis:
                overview = analysis['数据概况']
                with col1:
                    st.metric(
                        label="📅 数据天数",
                        value=f"{overview.get('数据天数', 0)} 天"
                    )
            
            # 两融余额
            if '两融余额分析' in analysis:
                balance = analysis['两融余额分析']
                with col2:
                    st.metric(
                        label="💰 最新余额",
                        value=balance.get('最新余额', 'N/A')
                    )
                
                with col3:
                    st.metric(
                        label="📈 最高余额",
                        value=balance.get('最高余额', 'N/A')
                    )
                
                with col4:
                    st.metric(
                        label="📊 波动率",
                        value=balance.get('余额波动率', 'N/A')
                    )
            
            # 结构分析
            if '融资融券结构' in analysis:
                st.subheader("🏗️ 融资融券结构")
                structure = analysis['融资融券结构']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="💼 融资余额",
                        value=structure.get('融资余额', 'N/A')
                    )
                
                with col2:
                    st.metric(
                        label="📉 融券余额", 
                        value=structure.get('融券余额', 'N/A')
                    )
                
                with col3:
                    financing_ratio = structure.get('融资占比', '0%')
                    st.metric(
                        label="📊 融资占比",
                        value=financing_ratio
                    )
            
            # 趋势和风险
            col1, col2 = st.columns(2)
            
            if '趋势分析' in analysis:
                with col1:
                    trend = analysis['趋势分析']
                    st.metric(
                        label="📈 近期趋势",
                        value=trend.get('趋势判断', 'N/A'),
                        delta=trend.get('近5日平均变化率', 'N/A')
                    )
            
            if '风险评估' in analysis:
                with col2:
                    risk = analysis['风险评估']
                    rsi_value = risk.get('RSI指标', '50')
                    risk_level = risk.get('风险等级', 'N/A')
                    
                    st.metric(
                        label="⚠️ 风险评估",
                        value=risk_level,
                        delta=f"RSI: {rsi_value}"
                    )
    
    def show_charts(self, config):
        """显示图表"""
        if st.session_state.processed_data.empty:
            return
        
        df = st.session_state.processed_data
        
        # 确保dates变量总是被定义
        dates = pd.to_datetime(df['交易日期']) if '交易日期' in df.columns else list(range(len(df)))
        
        # 余额趋势图
        if config['show_balance_chart']:
            st.subheader("📈 两融交易数据趋势分析")
            
            fig = make_subplots(
                rows=4, cols=1,
                subplot_titles=['两融余额趋势', '两融余额日变化率', '净融资额趋势', '维持担保比例'],
                vertical_spacing=0.08
            )
            
            # 初始化纵轴范围变量
            y1_min, y1_max = None, None
            y2_min, y2_max = None, None
            y3_min, y3_max = None, None
            
            # 1. 两融余额趋势 - 显示绝对值，增强可见性
            if '两融余额' in df.columns:
                # 计算统计信息
                balance_values = df['两融余额'] / 1e12  # 转换为万亿
                mean_balance = balance_values.mean()
                min_balance = balance_values.min()
                max_balance = balance_values.max()
                balance_range = max_balance - min_balance
                
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=balance_values,
                        name='两融余额',
                        line=dict(color='#FF6B6B', width=3),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '两融余额: %{y:.2f}万亿<br>' +
                                     '<extra></extra>'
                    ),
                    row=1, col=1
                )
                
                # 添加均值参考线
                fig.add_hline(y=mean_balance, line_dash="dash", line_color="gray", 
                            annotation_text=f"均值线 ({mean_balance:.2f}万亿)", row=1, col=1)
                
                # 自定义纵轴范围
                margin = balance_range * 0.05
                y1_min = max(0, min_balance - margin)
                y1_max = max_balance + margin
            
            # 2. 两融余额日变化率 - 显示绝对值
            if '两融余额_日变化率' in df.columns:
                # 计算统计信息
                change_rate = df['两融余额_日变化率']
                mean_change = change_rate.mean()
                min_change = change_rate.min()
                max_change = change_rate.max()
                change_range = max_change - min_change
                
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=change_rate,
                        name='日变化率',
                        line=dict(color='#9370DB', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(147, 112, 219, 0.3)',
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '日变化率: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    ),
                    row=2, col=1
                )
                
                # 添加零基准线和均值线
                fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                            annotation_text="零变化线", row=2, col=1)
                fig.add_hline(y=mean_change, line_dash="dot", line_color="blue", 
                            annotation_text=f"均值线 ({mean_change:.2f}%)", row=2, col=1)
                
                # 自定义纵轴范围
                margin = change_range * 0.1 if change_range > 0 else 0.1
                y2_min = min_change - margin
                y2_max = max_change + margin
            
            # 3. 净融资额趋势 - 显示绝对值
            if '净融资额' in df.columns:
                # 计算统计信息
                net_values = df['净融资额'] / 1e12  # 转换为万亿
                mean_net = net_values.mean()
                min_net = net_values.min()
                max_net = net_values.max()
                net_range = max_net - min_net
                
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=net_values,
                        name='净融资额',
                        line=dict(color='#4ECDC4', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(78, 205, 196, 0.3)',
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '净融资额: %{y:.2f}万亿<br>' +
                                     '<extra></extra>'
                    ),
                    row=3, col=1
                )
                
                # 添加零基准线和均值线
                fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                            annotation_text="零基准线", row=3, col=1)
                fig.add_hline(y=mean_net, line_dash="dot", line_color="blue", 
                            annotation_text=f"均值线 ({mean_net:.2f}万亿)", row=3, col=1)
                
                # 自定义纵轴范围
                margin = net_range * 0.1 if net_range > 0 else 0.1
                y3_min = min_net - margin
                y3_max = max_net + margin
            
            # 4. 市场整体维持担保比例
            if '市场整体维持担保比例' in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=df['市场整体维持担保比例'],
                        name='维持担保比例',
                        line=dict(color='#45B7D1', width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '担保比例: %{y:.1f}%<br>' +
                                     '<extra></extra>'
                    ),
                    row=4, col=1
                )
                
                # 添加风险参考线
                fig.add_hline(y=130, line_dash="dash", line_color="red", 
                            annotation_text="最低风险线(130%)", row=4, col=1)
                fig.add_hline(y=150, line_dash="dash", line_color="orange", 
                            annotation_text="警戒线(150%)", row=4, col=1)
                fig.add_hline(y=200, line_dash="dash", line_color="green", 
                            annotation_text="安全线(200%)", row=4, col=1)
            
            fig.update_layout(
                height=1200,  # 增加高度以适应四个子图
                showlegend=True,
                title_text="两融交易数据趋势分析",
                title_x=0.5
            )
            
            # 为每个子图设置自定义纵轴范围
            if '两融余额' in df.columns and y1_min is not None and y1_max is not None:
                fig.update_yaxes(title_text="两融余额 (万亿)", range=[y1_min, y1_max], row=1, col=1)
            else:
                fig.update_yaxes(title_text="两融余额 (万亿)", row=1, col=1)
            
            if '两融余额_日变化率' in df.columns and y2_min is not None and y2_max is not None:
                fig.update_yaxes(title_text="日变化率 (%)", range=[y2_min, y2_max], row=2, col=1)
            else:
                fig.update_yaxes(title_text="日变化率 (%)", row=2, col=1)
            
            if '净融资额' in df.columns and y3_min is not None and y3_max is not None:
                fig.update_yaxes(title_text="净融资额 (万亿)", range=[y3_min, y3_max], row=3, col=1)
            else:
                fig.update_yaxes(title_text="净融资额 (万亿)", row=3, col=1)
                
            fig.update_yaxes(title_text="担保比例 (%)", row=4, col=1)
            
            # 添加说明文字
            st.info("💡 **图表说明**：\n" +
                   "• **两融余额**：显示实际余额数值（万亿），纵轴范围已优化以突出变化\n" +
                   "• **日变化率**：两融余额相比前一日的变化百分比，显示实际波动幅度\n" +
                   "• **净融资额**：融资余额减去融券余额（万亿），反映市场做多情绪强度\n" +
                   "• **维持担保比例**：衡量市场整体杠杆风险的安全垫指标，130%为最低要求\n" +
                   "• 所有图表纵轴范围均已优化至实际数据范围，鼠标悬停可查看详细数值")
            
            st.plotly_chart(fig, width='stretch')
        
        # 占比分析图
        if config['show_ratio_chart']:
            st.subheader("📊 融资占比趋势分析")
            
            if '融资余额' in df.columns and '融券余额' in df.columns and len(df) > 0:
                # 计算融资占比
                total_balance = df['融资余额'] + df['融券余额']
                financing_ratio = (df['融资余额'] / total_balance * 100)
                
                # 计算统计信息
                mean_financing_ratio = financing_ratio.mean()
                min_ratio = financing_ratio.min()
                max_ratio = financing_ratio.max()
                ratio_range = max_ratio - min_ratio
                
                # 创建单个图表
                fig_ratio = go.Figure()
                
                # 融资占比趋势 - 显示绝对值
                fig_ratio.add_trace(
                    go.Scatter(
                        x=dates,
                        y=financing_ratio,
                        name='融资占比',
                        line=dict(color='#FF6B6B', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(255, 107, 107, 0.2)',
                        hovertemplate='<b>融资占比</b><br>' +
                                     '日期: %{x}<br>' +
                                     '融资占比: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    )
                )
                
                # 添加均值参考线
                fig_ratio.add_hline(y=mean_financing_ratio, line_dash="dash", line_color="gray", 
                                   annotation_text=f"均值线 ({mean_financing_ratio:.2f}%)")
                
                # 自定义纵轴范围：从最小值到最大值，留一点边距
                margin = ratio_range * 0.05  # 5%的边距
                y_min = max(0, min_ratio - margin)  # 确保不小于0
                y_max = min(100, max_ratio + margin)  # 确保不大于100
                
                # 更新布局
                fig_ratio.update_layout(
                    height=400,
                    showlegend=True,
                    title_text="融资占比时间序列分析",
                    title_x=0.5,
                    yaxis_title="融资占比 (%)",
                    yaxis=dict(
                        range=[y_min, y_max],
                        tickformat='.2f'
                    )
                )
                
                # 添加说明信息
                st.info("💡 **图表说明**：\n" +
                       f"• **融资占比范围**: {min_ratio:.2f}% ~ {max_ratio:.2f}%\n" +
                       f"• **均值**: {mean_financing_ratio:.2f}%\n" +
                       f"• **波动幅度**: {ratio_range:.2f}个百分点\n" +
                       "• 纵轴范围已优化至实际数据范围，突出变化幅度\n" +
                       "• 鼠标悬停可查看详细数据")
                
                st.plotly_chart(fig_ratio, width='stretch')
            
            # RSI相对强弱指标
            if '两融余额_RSI' in df.columns:
                fig_rsi = go.Figure()
                
                fig_rsi.add_trace(go.Scatter(
                    x=dates, y=df['两融余额_RSI'],
                    name='RSI', line=dict(color='#45B7D1', width=2)
                ))
                
                # 添加参考线
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", 
                                annotation_text="超买线")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", 
                                annotation_text="超卖线")
                fig_rsi.add_hline(y=50, line_dash="dash", line_color="gray", 
                                annotation_text="中位线")
                
                fig_rsi.update_layout(
                    title="RSI相对强弱指标",
                    yaxis_title="RSI",
                    height=400,
                    yaxis=dict(range=[0, 100])
                )
                
                st.plotly_chart(fig_rsi, width='stretch')
        
        # 相关性分析
        if config['show_correlation']:
            st.subheader("🔗 相关性分析")
            
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            exclude_patterns = ['_日变化', '_周变化', '_月变化', 'MA', 'RSI', '布林']
            filtered_columns = [col for col in numeric_columns 
                              if not any(pattern in col for pattern in exclude_patterns)]
            
            if len(filtered_columns) >= 2:
                corr_matrix = df[filtered_columns].corr()
                
                fig_heatmap = px.imshow(
                    corr_matrix,
                    labels=dict(color="相关系数"),
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    color_continuous_scale='RdBu_r',
                    aspect="auto"
                )
                
                fig_heatmap.update_layout(
                    title="数据相关性热力图",
                    height=500
                )
                
                st.plotly_chart(fig_heatmap, width='stretch')
    
    def show_data_table(self):
        """显示数据表格"""
        if not st.session_state.processed_data.empty:
            st.subheader("📋 详细数据")
            
            # 选择要显示的列
            all_columns = st.session_state.processed_data.columns.tolist()
            
            # 默认显示的重要列
            default_columns = []
            important_patterns = ['交易日期', '融资余额', '融券余额', '两融余额', '变化率', '占比']
            
            for pattern in important_patterns:
                matching_cols = [col for col in all_columns if pattern in col]
                default_columns.extend(matching_cols)
            
            # 去重并保持顺序
            default_columns = list(dict.fromkeys(default_columns))
            
            selected_columns = st.multiselect(
                "选择要显示的列:",
                options=all_columns,
                default=default_columns[:10]  # 最多显示10列
            )
            
            if selected_columns:
                display_df = st.session_state.processed_data[selected_columns].copy()
                
                # 格式化数值列
                for col in display_df.columns:
                    if display_df[col].dtype in ['float64', 'int64']:
                        if '余额' in col:
                            display_df[col] = display_df[col].apply(lambda x: format_number(x) if pd.notna(x) else 'N/A')
                        elif '率' in col or '比' in col:
                            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else 'N/A')
                
                st.dataframe(display_df, width='stretch', height=400)
                
                # 下载按钮
                if st.button("📥 下载数据"):
                    csv = st.session_state.processed_data.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载CSV文件",
                        data=csv,
                        file_name=f"margin_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
    
    def run(self):
        """运行Web应用"""
        # 显示头部
        self.show_header()
        
        # 显示侧边栏并获取配置
        config = self.show_sidebar()
        
        # 如果点击查询按钮
        if config['query_button']:
            success = self.query_data(config)
            
            if success:
                # 重新运行以显示结果
                st.rerun()
        
        # 如果有数据，显示结果
        if not st.session_state.processed_data.empty:
            # 显示汇总指标
            self.show_summary_metrics()
            
            # 显示图表
            self.show_charts(config)
            
            # 显示数据表格
            with st.expander("📋 查看详细数据", expanded=False):
                self.show_data_table()
        
        # 显示帮助信息
        with st.expander("❓ 使用帮助", expanded=False):
            st.markdown("""
            ### 📖 使用说明
            
            1. **设置查询参数**: 在左侧边栏选择日期范围和查询选项
            2. **开始查询**: 点击"开始查询"按钮获取数据
            3. **查看结果**: 查看汇总指标、图表和详细数据
            4. **导出数据**: 在数据表格部分可以下载CSV文件
            
            ### 📊 指标说明
            
            - **两融余额**: 融资余额和融券余额的总和
            - **融资占比**: 融资余额在两融余额中的占比
            - **RSI指标**: 相对强弱指标，用于判断超买超卖
            - **波动率**: 衡量价格变化的剧烈程度
            
            ### ⚠️ 注意事项
            
            - 数据来源于公开的金融数据接口
            - 建议查询时间范围不超过1年，以确保查询效率
            - 首次查询可能需要较长时间，后续查询会使用缓存加速
            """)

def main():
    """主函数"""
    app = MarginTradingWebApp()
    app.run()

if __name__ == '__main__':
    main()