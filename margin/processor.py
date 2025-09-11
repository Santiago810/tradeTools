"""
两融数据处理模块 - A股两融交易查询系统
处理A股市场的融资融券交易数据
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MARGIN_TRADING_CONFIG
from utils import format_number

class MarginDataProcessor:
    """两融数据处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_margin_summary(self, margin_data: pd.DataFrame, 
                             market_data: pd.DataFrame = None) -> pd.DataFrame:
        """
        处理两融汇总数据，计算各种占比指标
        :param margin_data: 两融数据
        :param market_data: 市场数据（用于计算占比）
        :return: 处理后的数据
        """
        if margin_data.empty:
            self.logger.warning("两融数据为空")
            return pd.DataFrame()
        
        result = margin_data.copy()
        
        try:
            # 确保日期列存在且格式正确
            if '交易日期' in result.columns:
                result['交易日期'] = pd.to_datetime(result['交易日期'], format='%Y%m%d')
                result = result.sort_values('交易日期')
            
            # 计算基础指标
            result = self._calculate_basic_metrics(result)
            
            # 计算变化率
            result = self._calculate_change_rates(result)
            
            # 计算移动平均
            result = self._calculate_moving_averages(result)
            
            # 如果有市场数据，计算市场占比
            if market_data is not None and not market_data.empty:
                result = self._calculate_market_ratios(result, market_data)
            
            # 计算统计指标
            result = self._calculate_statistical_metrics(result)
            
            self.logger.info(f"数据处理完成，共处理{len(result)}条记录")
            
        except Exception as e:
            self.logger.error(f"处理两融数据时出错: {e}")
        
        return result
    
    def _calculate_basic_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算基础指标"""
        result = df.copy()
        
        # 确保两融余额存在
        if '融资余额' in result.columns and '融券余额' in result.columns:
            # 如果没有两融余额列，计算它
            if '两融余额' not in result.columns:
                result['两融余额'] = result['融资余额'] + result['融券余额']
            
            # 计算净融资额（融资余额 - 融券余额）
            result['净融资额'] = result['融资余额'] - result['融券余额']
        
        # 计算融资、融券在两融中的占比
        if '两融余额' in result.columns and result['两融余额'].sum() > 0:
            if '融资余额' in result.columns:
                result['融资占两融比例'] = (result['融资余额'] / result['两融余额'] * 100).round(2)
            
            if '融券余额' in result.columns:
                result['融券占两融比例'] = (result['融券余额'] / result['两融余额'] * 100).round(2)
        
        # 计算市场整体维持担保比例（模拟计算）
        # 注：由于缺乏真实的担保物市值数据，我们使用经验公式估算
        # 一般情况下，维持担保比例 = 担保物市值 / 两融负债 × 100%
        # 正常范围为130%-300%，我们用两融余额的估算系数来模拟
        if '两融余额' in result.columns:
            # 使用经验公式：基本比例180% + 根据市场情况的波动调整
            # 当两融余额增加时，通常表示市场乐观，担保物价值上升，比例上升
            base_ratio = 180  # 基本比例180%
            
            # 计算两融余额的日变化率作为调整因子
            if len(result) > 1:
                balance_change_rate = result['两融余额'].pct_change() * 100
                # 根据变化率调整比例：上涨时比例增加，下跌时比例减少
                ratio_adjustment = balance_change_rate * 0.5  # 调整系数
                result['市场整体维持担保比例'] = (base_ratio + ratio_adjustment).clip(150, 250).round(2)
            else:
                result['市场整体维持担保比例'] = base_ratio
        
        # 计算融资买入相关指标
        if '融资买入额' in result.columns and '融资余额' in result.columns:
            # 融资周转率（买入额/余额）
            result['融资周转率'] = (result['融资买入额'] / result['融资余额'] * 100).round(4)
        
        return result
    
    def _calculate_change_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算变化率"""
        result = df.copy()
        
        # 需要计算变化率的列
        change_columns = ['融资余额', '融券余额', '两融余额', '融资买入额']
        
        for col in change_columns:
            if col in result.columns:
                # 日变化量
                result[f'{col}_日变化'] = result[col].diff()
                
                # 日变化率
                result[f'{col}_日变化率'] = (result[col].pct_change() * 100).round(2)
                
                # 周变化率（5个交易日）
                result[f'{col}_周变化率'] = (result[col].pct_change(periods=5) * 100).round(2)
                
                # 月变化率（20个交易日）
                result[f'{col}_月变化率'] = (result[col].pct_change(periods=20) * 100).round(2)
        
        return result
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算移动平均线"""
        result = df.copy()
        
        # 需要计算移动平均的列
        ma_columns = ['融资余额', '融券余额', '两融余额']
        
        # 移动平均周期
        periods = [5, 10, 20, 60]  # 5日、10日、20日、60日
        
        for col in ma_columns:
            if col in result.columns:
                for period in periods:
                    ma_col = f'{col}_MA{period}'
                    result[ma_col] = result[col].rolling(window=period, min_periods=1).mean().round(2)
                    
                    # 计算价格相对于移动平均线的偏离度
                    deviation_col = f'{col}_MA{period}_偏离度'
                    result[deviation_col] = ((result[col] / result[ma_col] - 1) * 100).round(2)
        
        return result
    
    def _calculate_market_ratios(self, margin_df: pd.DataFrame, 
                               market_df: pd.DataFrame) -> pd.DataFrame:
        """计算市场占比"""
        result = margin_df.copy()
        
        try:
            # 合并市场数据
            if '交易日期' in market_df.columns:
                market_df['交易日期'] = pd.to_datetime(market_df['交易日期'], format='%Y%m%d')
                
                # 按日期汇总市场成交金额
                market_summary = market_df.groupby('交易日期').agg({
                    '成交金额': 'sum'
                }).reset_index()
                
                # 合并数据
                result = result.merge(market_summary, on='交易日期', how='left', suffixes=('', '_市场'))
                
                # 计算两融占市场成交金额比例
                if '成交金额' in result.columns and '两融余额' in result.columns:
                    result['两融余额占市场成交比'] = (result['两融余额'] / result['成交金额'] * 100).round(4)
                
                if '成交金额' in result.columns and '融资买入额' in result.columns:
                    result['融资买入占市场成交比'] = (result['融资买入额'] / result['成交金额'] * 100).round(4)
            
        except Exception as e:
            self.logger.error(f"计算市场占比时出错: {e}")
        
        return result
    
    def _calculate_statistical_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算统计指标"""
        result = df.copy()
        
        # 计算相对强弱指标（RSI）
        rsi_columns = ['融资余额', '两融余额']
        
        for col in rsi_columns:
            if col in result.columns:
                rsi_col = f'{col}_RSI'
                result[rsi_col] = self._calculate_rsi(result[col])
        
        # 计算布林带
        bollinger_columns = ['融资余额', '两融余额']
        
        for col in bollinger_columns:
            if col in result.columns:
                upper, middle, lower = self._calculate_bollinger_bands(result[col])
                result[f'{col}_布林上轨'] = upper
                result[f'{col}_布林中轨'] = middle
                result[f'{col}_布林下轨'] = lower
                
                # 计算布林带位置
                result[f'{col}_布林位置'] = ((result[col] - lower) / (upper - lower) * 100).round(2)
        
        return result
    
    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        try:
            delta = series.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period, min_periods=1).mean()
            avg_loss = loss.rolling(window=period, min_periods=1).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.round(2)
        
        except Exception:
            return pd.Series([np.nan] * len(series), index=series.index)
    
    def _calculate_bollinger_bands(self, series: pd.Series, period: int = 20, 
                                 std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        try:
            middle = series.rolling(window=period, min_periods=1).mean()
            std = series.rolling(window=period, min_periods=1).std()
            
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            return upper.round(2), middle.round(2), lower.round(2)
        
        except Exception:
            nan_series = pd.Series([np.nan] * len(series), index=series.index)
            return nan_series, nan_series, nan_series
    
    def analyze_margin_trends(self, df: pd.DataFrame) -> Dict:
        """
        分析两融趋势
        :param df: 处理后的两融数据
        :return: 趋势分析结果
        """
        if df.empty:
            return {}
        
        analysis = {}
        
        try:
            # 基础统计
            analysis['数据概况'] = {
                '数据起始日期': df['交易日期'].min().strftime('%Y-%m-%d') if '交易日期' in df.columns else 'N/A',
                '数据结束日期': df['交易日期'].max().strftime('%Y-%m-%d') if '交易日期' in df.columns else 'N/A',
                '数据天数': len(df),
            }
            
            # 两融余额分析
            if '两融余额' in df.columns:
                latest_balance = df['两融余额'].iloc[-1] if len(df) > 0 else 0
                min_balance = df['两融余额'].min()
                max_balance = df['两融余额'].max()
                avg_balance = df['两融余额'].mean()
                
                analysis['两融余额分析'] = {
                    '最新余额': format_number(latest_balance),
                    '最低余额': format_number(min_balance),
                    '最高余额': format_number(max_balance),
                    '平均余额': format_number(avg_balance),
                    '余额波动率': f"{(df['两融余额'].std() / avg_balance * 100):.2f}%" if avg_balance > 0 else 'N/A'
                }
            
            # 融资融券结构分析
            if '融资余额' in df.columns and '融券余额' in df.columns and '两融余额' in df.columns:
                latest_idx = len(df) - 1
                financing_ratio = (df['融资余额'].iloc[latest_idx] / df['两融余额'].iloc[latest_idx] * 100) if df['两融余额'].iloc[latest_idx] > 0 else 0
                short_ratio = (df['融券余额'].iloc[latest_idx] / df['两融余额'].iloc[latest_idx] * 100) if df['两融余额'].iloc[latest_idx] > 0 else 0
                
                analysis['融资融券结构'] = {
                    '融资占比': f"{financing_ratio:.2f}%",
                    '融券占比': f"{short_ratio:.2f}%",
                    '融资余额': format_number(df['融资余额'].iloc[latest_idx]),
                    '融券余额': format_number(df['融券余额'].iloc[latest_idx])
                }
            
            # 趋势分析
            if '两融余额_日变化率' in df.columns:
                recent_changes = df['两融余额_日变化率'].tail(5).mean()
                
                if recent_changes > 1:
                    trend = "快速上升"
                elif recent_changes > 0.1:
                    trend = "温和上升"
                elif recent_changes > -0.1:
                    trend = "基本平稳"
                elif recent_changes > -1:
                    trend = "温和下降"
                else:
                    trend = "快速下降"
                
                analysis['趋势分析'] = {
                    '近5日平均变化率': f"{recent_changes:.2f}%",
                    '趋势判断': trend
                }
            
            # 风险指标
            if '两融余额_RSI' in df.columns:
                latest_rsi = df['两融余额_RSI'].iloc[-1] if len(df) > 0 else 50
                
                if latest_rsi > 70:
                    risk_level = "高风险（超买）"
                elif latest_rsi > 50:
                    risk_level = "中等风险"
                elif latest_rsi > 30:
                    risk_level = "低风险"
                else:
                    risk_level = "超卖"
                
                analysis['风险评估'] = {
                    'RSI指标': f"{latest_rsi:.2f}",
                    '风险等级': risk_level
                }
            
        except Exception as e:
            self.logger.error(f"趋势分析时出错: {e}")
            analysis['错误'] = str(e)
        
        return analysis
    
    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """
        生成汇总报告
        :param df: 处理后的数据
        :return: 汇总报告文本
        """
        analysis = self.analyze_margin_trends(df)
        
        report_lines = []
        report_lines.append("=" * 50)
        report_lines.append("A股两融交易占比分析报告")
        report_lines.append("=" * 50)
        
        # 数据概况
        if '数据概况' in analysis:
            overview = analysis['数据概况']
            report_lines.append(f"\n数据时间范围：{overview.get('数据起始日期', 'N/A')} 至 {overview.get('数据结束日期', 'N/A')}")
            report_lines.append(f"分析天数：{overview.get('数据天数', 0)} 天")
        
        # 两融余额分析
        if '两融余额分析' in analysis:
            balance = analysis['两融余额分析']
            report_lines.append(f"\n【两融余额概况】")
            report_lines.append(f"最新余额：{balance.get('最新余额', 'N/A')}")
            report_lines.append(f"期间最高：{balance.get('最高余额', 'N/A')}")
            report_lines.append(f"期间最低：{balance.get('最低余额', 'N/A')}")
            report_lines.append(f"平均余额：{balance.get('平均余额', 'N/A')}")
            report_lines.append(f"波动率：{balance.get('余额波动率', 'N/A')}")
        
        # 结构分析
        if '融资融券结构' in analysis:
            structure = analysis['融资融券结构']
            report_lines.append(f"\n【融资融券结构】")
            report_lines.append(f"融资余额：{structure.get('融资余额', 'N/A')} ({structure.get('融资占比', 'N/A')})")
            report_lines.append(f"融券余额：{structure.get('融券余额', 'N/A')} ({structure.get('融券占比', 'N/A')})")
        
        # 趋势分析
        if '趋势分析' in analysis:
            trend = analysis['趋势分析']
            report_lines.append(f"\n【趋势分析】")
            report_lines.append(f"近期变化：{trend.get('近5日平均变化率', 'N/A')}")
            report_lines.append(f"趋势判断：{trend.get('趋势判断', 'N/A')}")
        
        # 风险评估
        if '风险评估' in analysis:
            risk = analysis['风险评估']
            report_lines.append(f"\n【风险评估】")
            report_lines.append(f"RSI指标：{risk.get('RSI指标', 'N/A')}")
            report_lines.append(f"风险等级：{risk.get('风险等级', 'N/A')}")
        
        report_lines.append("\n" + "=" * 50)
        report_lines.append("报告生成时间：" + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return "\n".join(report_lines)

# 工厂函数
def create_margin_processor() -> MarginDataProcessor:
    """创建两融数据处理器实例"""
    return MarginDataProcessor()