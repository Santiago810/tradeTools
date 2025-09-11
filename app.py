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
from margin.fetcher import create_margin_fetcher
from margin.processor import create_margin_processor
from margin.visualizer import create_margin_visualizer

# 页面配置
st.set_page_config(
    page_title="A股金融数据分析系统",
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
    .feature-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 15px;
    }
    .feature-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 10px;
        color: #1f77b4;
    }
    .feature-description {
        color: #666;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

class MarginTradingWebApp:
    """两融交易Web应用"""
    
    def __init__(self):
        self._initialize_app()
        # 初始化页面状态管理
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "main"
    
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
    
    def show_main_page(self):
        """显示主页"""
        st.markdown('<div class="main-header">📊 A股金融数据分析系统</div>', 
                   unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
            <h3>欢迎使用A股金融数据分析系统</h3>
            <p>本系统提供专业的A股市场数据分析功能，帮助投资者做出更明智的投资决策。</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 创建功能卡片布局
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <div class="feature-title">两融交易查询</div>
                <div class="feature-description">查询和分析A股市场的融资融券交易数据，包括余额趋势、占比分析等</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("进入两融交易查询", type="primary", use_container_width=True):
                st.session_state.current_page = "margin"
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">💰</div>
                <div class="feature-title">ETF基金查询</div>
                <div class="feature-description">查询和分析ETF基金的资金流向、份额变动、申购赎回情况</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("进入ETF基金查询", type="primary", use_container_width=True):
                st.session_state.current_page = "etf"
                st.rerun()
        
        # 系统介绍
        st.markdown("### 📊 系统功能介绍")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 两融交易分析功能
            - **数据查询**：从多个数据源获取A股两融交易数据
            - **趋势分析**：计算两融余额变化趋势和技术指标
            - **占比计算**：分析融资融券在市场中的占比情况
            - **数据可视化**：生成专业的图表和交互式仪表板
            """)
        
        with col2:
            st.markdown("""
            #### ETF基金分析功能
            - **资金流向**：分析ETF基金的净申购赎回情况
            - **份额变动**：跟踪ETF基金总份额的变化情况
            - **申购赎回**：监控场外投资者申购和赎回ETF的情况
            - **综合分析**：提供ETF基金的全面数据分析报告
            """)
        
        st.markdown("### ⚠️ 使用说明")
        st.markdown("""
        1. 点击上方功能按钮进入相应的查询界面
        2. 每个功能模块完全独立，互不影响
        3. 首次查询可能需要较长时间，请耐心等待
        4. 建议查询时间范围不超过1年，以确保查询效率
        """)
    
    def show_margin_trading_page(self):
        """显示两融交易查询页面"""
        # 页面标题和返回按钮
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← 返回主页"):
                st.session_state.current_page = "main"
                st.rerun()
        with col2:
            st.markdown('<div class="main-header">📈 A股两融交易查询</div>', 
                       unsafe_allow_html=True)
        
        # 显示侧边栏并获取配置
        config = self.show_margin_sidebar()
        
        # 如果点击查询按钮
        if config['query_button']:
            success = self.query_margin_data(config)
            
            if success:
                st.rerun()
        
        # 如果有数据，显示结果
        if 'processed_data' in st.session_state and not st.session_state.processed_data.empty:
            # 显示汇总指标
            self.show_summary_metrics()
            
            # 显示图表
            self.show_margin_charts(config)
            
            # 显示数据表格
            with st.expander("📋 查看详细数据", expanded=False):
                self.show_margin_data_table()
    
    def show_etf_page(self):
        """显示ETF查询页面"""
        # 页面标题和返回按钮
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← 返回主页"):
                st.session_state.current_page = "main"
                st.rerun()
        with col2:
            st.markdown('<div class="main-header">💰 ETF基金查询</div>', 
                       unsafe_allow_html=True)
        
        # ETF查询配置
        st.sidebar.header("🔧 ETF查询配置")
        
        # ETF代码输入
        etf_code = st.sidebar.text_input("请输入ETF代码", value="510310", 
                                        help="例如：510310 (沪深300ETF), 510050 (上证50ETF)")
        
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
        
        # 图表选项
        st.sidebar.subheader("📊 图表选项")
        
        show_fund_flow_chart = st.sidebar.checkbox("资金流向图", value=True)
        show_share_change_chart = st.sidebar.checkbox("份额变动图", value=True)
        show_subscription_chart = st.sidebar.checkbox("申购赎回图", value=True)
        show_comprehensive_chart = st.sidebar.checkbox("综合分析图", value=True)
        
        # 查询按钮
        query_button = st.sidebar.button("🚀 开始查询", type="primary")
        
        config = {
            'etf_code': etf_code,
            'start_date': start_date.strftime('%Y%m%d'),
            'end_date': end_date.strftime('%Y%m%d'),
            'use_cache': use_cache,
            'show_fund_flow_chart': show_fund_flow_chart,
            'show_share_change_chart': show_share_change_chart,
            'show_subscription_chart': show_subscription_chart,
            'show_comprehensive_chart': show_comprehensive_chart,
            'query_button': query_button
        }
        
        # 如果点击查询按钮
        if config['query_button']:
            success = self.query_etf_data(config)
            
            if success:
                st.rerun()
        
        # 如果有数据，显示结果
        if 'etf_data' in st.session_state and st.session_state.etf_data:
            # 显示ETF基本信息
            self.show_etf_info(st.session_state.etf_data.get('info', {}))
            
            # 显示汇总指标
            self.show_etf_summary_metrics(st.session_state.etf_data.get('analysis', {}))
            
            # 显示图表
            self.show_etf_charts(config, st.session_state.etf_data)
            
            # 显示数据表格
            with st.expander("📋 查看详细数据", expanded=False):
                self.show_etf_data_table(st.session_state.etf_data)
    
    def show_margin_sidebar(self):
        """显示两融交易查询侧边栏配置"""
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
    
    def query_margin_data(self, config):
        """查询两融数据"""
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
    
    def query_etf_data(self, config):
        """查询ETF数据"""
        try:
            # 初始化ETF组件
            from etf.fetcher import create_etf_fetcher
            from etf.processor import create_etf_processor
            from etf.visualizer import create_etf_visualizer
            
            etf_fetcher = create_etf_fetcher()
            etf_processor = create_etf_processor()
            etf_visualizer = create_etf_visualizer()
            
            with st.spinner("正在获取ETF基本信息..."):
                # 获取ETF基本信息
                etf_info = etf_fetcher.get_etf_info(config['etf_code'])
            
            with st.spinner("正在获取ETF资金流向数据..."):
                # 获取ETF资金流向数据
                fund_flow_data = etf_fetcher.get_etf_fund_flow(
                    config['etf_code'], 
                    config['start_date'], 
                    config['end_date']
                )
                
            with st.spinner("正在获取ETF份额变动数据..."):
                # 获取ETF份额变动数据
                share_change_data = etf_fetcher.get_etf_share_changes(
                    config['etf_code'], 
                    config['start_date'], 
                    config['end_date']
                )
                
            with st.spinner("正在获取ETF场外市场数据..."):
                # 获取ETF场外市场数据
                outside_data = etf_fetcher.get_etf_outside_market_data(
                    config['etf_code'], 
                    config['start_date'], 
                    config['end_date']
                )
                
            with st.spinner("正在获取ETF分钟数据..."):
                # 获取ETF分钟数据（用于实时估值和换手率分析）
                minute_data = etf_fetcher.get_etf_minute_data(config['etf_code'])
                
            with st.spinner("正在获取ETF融资买入数据..."):
                # 获取ETF融资买入数据
                margin_data = etf_fetcher.get_etf_margin_data(
                    config['etf_code'], 
                    config['start_date'], 
                    config['end_date']
                )
                
            with st.spinner("正在处理ETF数据..."):
                # 处理ETF数据
                processed_etf_data = etf_processor.process_etf_data(
                    fund_flow_data, share_change_data, outside_data, minute_data, margin_data
                )
                
                # 添加基本信息
                processed_etf_data['info'] = etf_info
                
                # 保存到session state
                st.session_state.etf_data = processed_etf_data
            
            st.success(f"✅ 成功获取并处理了ETF {config['etf_code']} 的数据")
            return True
            
        except Exception as e:
            st.error(f"❌ ETF查询失败: {str(e)}")
            return False
    
    def show_summary_metrics(self):
        """显示两融汇总指标"""
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
    
    def show_etf_info(self, etf_info: dict):
        """显示ETF基本信息"""
        if etf_info:
            st.subheader("📈 ETF基本信息")
            
            # 显示基金名称和代码
            fund_name = etf_info.get('基金简称', f'ETF-{etf_info.get("基金代码", "N/A")}')
            fund_code = etf_info.get('基金代码', 'N/A')
            st.markdown(f"### {fund_name} ({fund_code})")
            
            # 显示基本信息
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="📅 成立日期",
                    value=etf_info.get('成立日期', 'N/A')
                )
            
            with col2:
                st.metric(
                    label="💰 基金规模",
                    value=etf_info.get('基金规模', 'N/A')
                )
            
            with col3:
                st.metric(
                    label="📊 跟踪标的",
                    value=etf_info.get('跟踪标的', 'N/A')
                )
    
    def show_etf_summary_metrics(self, analysis: dict):
        """显示ETF汇总指标"""
        if analysis:
            st.subheader("📊 ETF数据概览")
            
            # 资金流向分析
            if 'fund_flow' in analysis:
                fund_flow = analysis['fund_flow']
                st.markdown("#### 💰 资金流向分析")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        label="总净流入",
                        value=f"{fund_flow.get('total_net_flow', 0):,.2f}万元"
                    )
                
                with col2:
                    st.metric(
                        label="日均净流入",
                        value=f"{fund_flow.get('avg_daily_flow', 0):,.2f}万元"
                    )
                
                with col3:
                    st.metric(
                        label="最新流向",
                        value=f"{fund_flow.get('latest_flow', 0):,.2f}万元"
                    )
                
                with col4:
                    st.metric(
                        label="近期趋势",
                        value=fund_flow.get('recent_trend', 'N/A')
                    )
            
            # 份额变动分析
            if 'share_changes' in analysis:
                share_changes = analysis['share_changes']
                st.markdown("#### 📈 份额变动分析")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        label="期初份额",
                        value=f"{share_changes.get('initial_shares', 0):,.2f}万份"
                    )
                
                with col2:
                    st.metric(
                        label="期末份额",
                        value=f"{share_changes.get('final_shares', 0):,.2f}万份"
                    )
                
                with col3:
                    st.metric(
                        label="总变动",
                        value=f"{share_changes.get('total_change', 0):,.2f}万份"
                    )
                
                with col4:
                    st.metric(
                        label="变动率",
                        value=f"{share_changes.get('change_rate', 0):.2f}%"
                    )
            
            # 场外市场分析
            if 'outside_market' in analysis:
                outside_market = analysis['outside_market']
                st.markdown("#### 🏦 场外市场分析")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        label="总申购",
                        value=f"{outside_market.get('total_subscription', 0):,.2f}万元"
                    )
                
                with col2:
                    st.metric(
                        label="总赎回",
                        value=f"{outside_market.get('total_redemption', 0):,.2f}万元"
                    )
                
                with col3:
                    st.metric(
                        label="净申购",
                        value=f"{outside_market.get('net_subscription', 0):,.2f}万元"
                    )
                
                with col4:
                    st.metric(
                        label="近期趋势",
                        value=outside_market.get('recent_subscription_trend', 'N/A')
                    )
    
    def show_margin_charts(self, config):
        """显示两融图表"""
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
    
    def show_etf_charts(self, config, etf_data):
        """显示ETF图表"""
        # 初始化ETF可视化器
        from etf.visualizer import create_etf_visualizer
        etf_visualizer = create_etf_visualizer()
        
        # 获取数据
        fund_flow_data = etf_data.get('fund_flow', pd.DataFrame())
        share_change_data = etf_data.get('share_changes', pd.DataFrame())
        outside_data = etf_data.get('outside_market', pd.DataFrame())
        minute_data = etf_data.get('minute_data', pd.DataFrame())
        margin_data = etf_data.get('margin_data', pd.DataFrame())
        
        # 创建标签页
        tab1, tab2, tab3, tab4 = st.tabs(["基础图表", "实时估值分析", "换手率分析", "融资买入分析"])
        
        # 基础图表标签页
        with tab1:
            # 资金流向图
            if config['show_fund_flow_chart'] and not fund_flow_data.empty:
                st.subheader("💰 ETF资金流向趋势")
                fund_flow_fig = etf_visualizer.create_fund_flow_chart(fund_flow_data)
                st.plotly_chart(fund_flow_fig, width='stretch')
            
            # 份额变动图
            if config['show_share_change_chart'] and not share_change_data.empty:
                st.subheader("📈 ETF份额变动趋势")
                share_change_fig = etf_visualizer.create_share_change_chart(share_change_data)
                st.plotly_chart(share_change_fig, width='stretch')
            
            # 申购赎回图
            if config['show_subscription_chart'] and not outside_data.empty:
                st.subheader("🏦 ETF申购赎回情况")
                subscription_fig = etf_visualizer.create_subscription_redemption_chart(outside_data)
                st.plotly_chart(subscription_fig, width='stretch')
            
            # 综合分析图
            if config['show_comprehensive_chart'] and (not fund_flow_data.empty or 
                                                      not share_change_data.empty or 
                                                      not outside_data.empty):
                st.subheader("📊 ETF综合分析图表")
                comprehensive_fig = etf_visualizer.create_comprehensive_etf_chart(
                    fund_flow_data, share_change_data, outside_data)
                st.plotly_chart(comprehensive_fig, width='stretch')
        
        # 实时估值分析标签页
        with tab2:
            st.subheader("📈 ETF实时估值与价格变化趋势")
            if not minute_data.empty:
                realtime_fig = etf_visualizer.create_etf_realtime_valuation_chart(minute_data)
                st.plotly_chart(realtime_fig, width='stretch')
                
                # 添加说明
                st.info("💡 **图表说明**：\n" +
                       "• **收盘价**：ETF在每个时间点的收盘价格\n" +
                       "• **均价**：作为实时估值的近似值，反映ETF的平均交易价格\n" +
                       "• 图表显示了ETF在查询当天的价格变化趋势")
            else:
                st.info("暂无分钟级别数据，无法显示实时估值分析")
        
        # 换手率分析标签页
        with tab3:
            st.subheader("🔄 ETF换手率变化曲线")
            if not minute_data.empty:
                turnover_fig = etf_visualizer.create_turnover_rate_chart(minute_data)
                st.plotly_chart(turnover_fig, width='stretch')
                
                # 添加说明
                st.info("💡 **图表说明**：\n" +
                       "• **换手率**：反映ETF的交易活跃程度，按日计算\n" +
                       "• **均值线**：换手率的历史均值参考线\n" +
                       "• 图表显示了ETF每日的换手率变化趋势")
            else:
                st.info("暂无分钟级别数据，无法显示换手率分析")
        
        # 融资买入分析标签页
        with tab4:
            st.subheader("💼 ETF融资买入数据变化曲线")
            margin_fig = etf_visualizer.create_margin_trading_chart(margin_data)
            st.plotly_chart(margin_fig, width='stretch')
            
            # 添加说明
            if margin_data.empty:
                st.info("💡 **说明**：\n" +
                       "• 该ETF暂无融资买入数据，可能不是融资融券标的\n" +
                       "• 融资买入数据通常只对特定的融资融券标的ETF可用")
            else:
                st.info("💡 **图表说明**：\n" +
                       "• **融资买入额**：投资者通过融资方式买入该ETF的金额\n" +
                       "• **融资余额**：当前未偿还的融资金额\n" +
                       "• 数据反映了市场对该ETF的杠杆交易需求")
    
    def show_margin_data_table(self):
        """显示两融数据表格"""
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
    
    def show_etf_data_table(self, etf_data):
        """显示ETF数据表格"""
        if etf_data:
            st.subheader("📋 ETF详细数据")
            
            # 创建标签页显示不同类型的数据
            tab1, tab2, tab3 = st.tabs(["资金流向", "份额变动", "场外市场"])
            
            with tab1:
                fund_flow_data = etf_data.get('fund_flow', pd.DataFrame())
                if not fund_flow_data.empty:
                    st.dataframe(fund_flow_data, width='stretch', height=400)
                    
                    # 下载按钮
                    if st.button("📥 下载资金流向数据"):
                        csv = fund_flow_data.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name=f"etf_fund_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("暂无资金流向数据")
            
            with tab2:
                share_change_data = etf_data.get('share_changes', pd.DataFrame())
                if not share_change_data.empty:
                    st.dataframe(share_change_data, width='stretch', height=400)
                    
                    # 下载按钮
                    if st.button("📥 下载份额变动数据"):
                        csv = share_change_data.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name=f"etf_share_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("暂无份额变动数据")
            
            with tab3:
                outside_data = etf_data.get('outside_market', pd.DataFrame())
                if not outside_data.empty:
                    st.dataframe(outside_data, width='stretch', height=400)
                    
                    # 下载按钮
                    if st.button("📥 下载场外市场数据"):
                        csv = outside_data.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name=f"etf_outside_market_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("暂无场外市场数据")
    
    def run(self):
        """运行Web应用"""
        # 根据当前页面显示不同内容
        if st.session_state.current_page == "main":
            self.show_main_page()
        elif st.session_state.current_page == "margin":
            self.show_margin_trading_page()
        elif st.session_state.current_page == "etf":
            self.show_etf_page()

def main():
    """主函数"""
    app = MarginTradingWebApp()
    app.run()

if __name__ == '__main__':
    main()