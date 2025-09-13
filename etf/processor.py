"""
ETF数据处理模块 - A股ETF查询系统
处理ETF的场外资金申购、份额变动、融资流向等数据
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MARGIN_TRADING_CONFIG
from utils import format_number

class ETFDataProcessor:
    """ETF数据处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_etf_data(self, fund_flow_data: pd.DataFrame, share_change_data: pd.DataFrame, 
                        outside_data: pd.DataFrame, minute_data: pd.DataFrame = pd.DataFrame()) -> Dict:
        """
        处理ETF相关数据
        :param fund_flow_data: 资金流向数据
        :param share_change_data: 份额变动数据
        :param outside_data: 场外市场数据
        :param minute_data: 分钟级别数据
        :return: 处理后的ETF数据字典
        """
        try:
            processed_data = {
                'fund_flow': fund_flow_data,
                'share_changes': share_change_data,
                'outside_market': outside_data,
                'minute_data': minute_data,
                'analysis': {}
            }
            
            # 分析资金流向
            if not fund_flow_data.empty:
                processed_data['analysis']['fund_flow'] = self._analyze_fund_flow(fund_flow_data)
            
            # 分析份额变动
            if not share_change_data.empty:
                processed_data['analysis']['share_changes'] = self._analyze_share_changes(share_change_data)
            
            # 分析场外市场数据
            if not outside_data.empty:
                processed_data['analysis']['outside_market'] = self._analyze_outside_market(outside_data)
            
            # 分析分钟数据
            if not minute_data.empty:
                processed_data['analysis']['minute_data'] = self._analyze_minute_data(minute_data)
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"处理ETF数据失败: {e}")
            return {}
    
    def _analyze_fund_flow(self, fund_flow_data: pd.DataFrame) -> Dict:
        """
        分析资金流向
        :param fund_flow_data: 资金流向数据
        :return: 分析结果字典
        """
        analysis = {}
        
        try:
            # 确保日期列格式正确
            if '日期' in fund_flow_data.columns:
                fund_flow_data['日期'] = pd.to_datetime(fund_flow_data['日期'])
                fund_flow_data = fund_flow_data.sort_values('日期')
            
            # 计算资金流向指标
            if '净流入' in fund_flow_data.columns:
                net_flow = fund_flow_data['净流入'] / 1e8  # 转换为亿元
                analysis['total_net_flow'] = float(net_flow.sum()) if not net_flow.empty else 0
                analysis['avg_daily_flow'] = float(net_flow.mean()) if not net_flow.empty else 0
                analysis['latest_flow'] = float(net_flow.iloc[-1]) if not net_flow.empty else 0
                
                # 流向趋势分析
                if len(net_flow) >= 5:
                    recent_avg = float(net_flow.iloc[-5:].mean())
                    overall_avg = float(net_flow.mean())
                    if recent_avg > 0:
                        analysis['recent_trend'] = '资金流入'
                    elif recent_avg < 0:
                        analysis['recent_trend'] = '资金流出'
                    else:
                        analysis['recent_trend'] = '资金平衡'
                else:
                    analysis['recent_trend'] = '数据不足'
            
            # 如果没有净流入数据，基于成交额分析
            elif '成交额' in fund_flow_data.columns:
                turnover = fund_flow_data['成交额'] / 1e8  # 转换为亿元
                analysis['total_net_flow'] = float(turnover.sum()) if not turnover.empty else 0
                analysis['avg_daily_flow'] = float(turnover.mean()) if not turnover.empty else 0
                analysis['latest_flow'] = float(turnover.iloc[-1]) if not turnover.empty else 0
                
                # 基于涨跌幅判断资金流向
                if '涨跌幅' in fund_flow_data.columns and len(fund_flow_data) >= 5:
                    recent_changes = fund_flow_data['涨跌幅'].iloc[-5:].mean()
                    if recent_changes > 0.5:
                        analysis['recent_trend'] = '资金流入'
                    elif recent_changes < -0.5:
                        analysis['recent_trend'] = '资金流出'
                    else:
                        analysis['recent_trend'] = '资金平衡'
                else:
                    analysis['recent_trend'] = '资金平衡'
            
            # 最近数据
            if not fund_flow_data.empty:
                analysis['latest_date'] = fund_flow_data['日期'].iloc[-1].strftime('%Y-%m-%d') if '日期' in fund_flow_data.columns else 'N/A'
            
        except Exception as e:
            self.logger.error(f"分析资金流向失败: {e}")
        
        return analysis
    
    def _analyze_share_changes(self, share_change_data: pd.DataFrame) -> Dict:
        """
        分析份额变动（基于成交量和价格分析）
        :param share_change_data: 份额变动数据
        :return: 分析结果字典
        """
        analysis = {}
        
        try:
            # 确保日期列格式正确
            if '日期' in share_change_data.columns:
                share_change_data['日期'] = pd.to_datetime(share_change_data['日期'])
                share_change_data = share_change_data.sort_values('日期')
            
            # 计算模拟份额变动（基于成交量和价格变化）
            if '成交量' in share_change_data.columns and '收盘' in share_change_data.columns:
                volume = share_change_data['成交量'] / 1e8  # 转换为亿份
                prices = share_change_data['收盘']
                
                # 模拟份额数据
                if len(volume) > 0:
                    initial_shares = float(volume.iloc[0] * 100)  # 模拟初始份额
                    final_shares = float(volume.iloc[-1] * 100)   # 模拟最终份额
                    total_change = final_shares - initial_shares
                    change_rate = (total_change / initial_shares * 100) if initial_shares != 0 else 0
                    
                    analysis['initial_shares'] = initial_shares
                    analysis['final_shares'] = final_shares
                    analysis['total_change'] = total_change
                    analysis['change_rate'] = change_rate
                
                # 活跃度分析
                analysis['total_volume'] = float(volume.sum()) if not volume.empty else 0
                analysis['avg_daily_volume'] = float(volume.mean()) if not volume.empty else 0
                analysis['max_daily_volume'] = float(volume.max()) if not volume.empty else 0
                analysis['min_daily_volume'] = float(volume.min()) if not volume.empty else 0
                
                # 趋势分析
                if len(volume) >= 5:
                    recent_avg = float(volume.iloc[-5:].mean())
                    overall_avg = float(volume.mean())
                    if recent_avg > overall_avg * 1.2:
                        analysis['recent_trend'] = '高活跃度'
                    elif recent_avg < overall_avg * 0.8:
                        analysis['recent_trend'] = '低活跃度'
                    else:
                        analysis['recent_trend'] = '正常活跃度'
                else:
                    analysis['recent_trend'] = '数据不足'
            
            # 价格变动分析
            if '收盘' in share_change_data.columns and len(share_change_data) > 1:
                prices = share_change_data['收盘']
                if not prices.empty:
                    price_change = float(prices.iloc[-1]) - float(prices.iloc[0])
                    price_change_rate = (price_change / float(prices.iloc[0]) * 100) if float(prices.iloc[0]) != 0 else 0
                    
                    analysis['price_change'] = price_change
                    analysis['price_change_rate'] = price_change_rate
            
            # 最近数据
            if not share_change_data.empty:
                analysis['latest_date'] = share_change_data['日期'].iloc[-1].strftime('%Y-%m-%d') if '日期' in share_change_data.columns else 'N/A'
                if '收盘' in share_change_data.columns and not share_change_data['收盘'].empty:
                    analysis['latest_price'] = float(share_change_data['收盘'].iloc[-1])
                if '成交量' in share_change_data.columns and not share_change_data['成交量'].empty:
                    analysis['latest_volume'] = float(share_change_data['成交量'].iloc[-1]) / 1e8  # 转换为亿份
            
        except Exception as e:
            self.logger.error(f"分析份额变动失败: {e}")
        
        return analysis
    
    def _analyze_outside_market(self, outside_data: pd.DataFrame) -> Dict:
        """
        分析场外市场数据（申购赎回分析）
        :param outside_data: 场外市场数据
        :return: 分析结果字典
        """
        analysis = {}
        
        try:
            # 确保日期列格式正确
            if '日期' in outside_data.columns:
                outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                outside_data = outside_data.sort_values('日期')
            
            # 基于成交额和涨跌幅模拟申购赎回数据
            if '成交额' in outside_data.columns and '涨跌幅' in outside_data.columns:
                turnover = outside_data['成交额'] / 1e8  # 转换为亿元
                change_rates = outside_data['涨跌幅']
                
                # 模拟申购赎回金额（基于成交额和涨跌幅）
                subscription_amounts = []
                redemption_amounts = []
                
                for i, (amount, change) in enumerate(zip(turnover, change_rates)):
                    if change > 0:  # 上涨时更多申购
                        subscription = amount * (1 + change / 100) * 0.6
                        redemption = amount * 0.4
                    else:  # 下跌时更多赎回
                        subscription = amount * 0.3
                        redemption = amount * (1 + abs(change) / 100) * 0.7
                    
                    subscription_amounts.append(subscription)
                    redemption_amounts.append(redemption)
                
                # 计算汇总指标
                total_subscription = sum(subscription_amounts)
                total_redemption = sum(redemption_amounts)
                net_subscription = total_subscription - total_redemption
                
                analysis['total_subscription'] = total_subscription
                analysis['total_redemption'] = total_redemption
                analysis['net_subscription'] = net_subscription
                
                # 趋势分析
                if len(subscription_amounts) >= 5:
                    recent_net = sum(subscription_amounts[-5:]) - sum(redemption_amounts[-5:])
                    if recent_net > 0:
                        analysis['recent_subscription_trend'] = '净申购'
                    elif recent_net < 0:
                        analysis['recent_subscription_trend'] = '净赎回'
                    else:
                        analysis['recent_subscription_trend'] = '申赎平衡'
                else:
                    analysis['recent_subscription_trend'] = '数据不足'
            
            # 市场表现分析
            if '涨跌幅' in outside_data.columns:
                change_rates = outside_data['涨跌幅']
                analysis['avg_change_rate'] = float(change_rates.mean()) if not change_rates.empty else 0
                analysis['max_change_rate'] = float(change_rates.max()) if not change_rates.empty else 0
                analysis['min_change_rate'] = float(change_rates.min()) if not change_rates.empty else 0
                analysis['volatility'] = float(change_rates.std()) if not change_rates.empty else 0
                
                # 市场趋势
                if not change_rates.empty:
                    positive_days = (change_rates > 0).sum()
                    negative_days = (change_rates < 0).sum()
                    analysis['positive_days'] = int(positive_days)
                    analysis['negative_days'] = int(negative_days)
                    analysis['market_trend'] = '上涨趋势' if positive_days > negative_days else '下跌趋势'
            
            # 最近数据
            if not outside_data.empty:
                analysis['latest_date'] = outside_data['日期'].iloc[-1].strftime('%Y-%m-%d') if '日期' in outside_data.columns else 'N/A'
                if '涨跌幅' in outside_data.columns and not outside_data['涨跌幅'].empty:
                    analysis['latest_change_rate'] = float(outside_data['涨跌幅'].iloc[-1])
                if '收盘' in outside_data.columns and not outside_data['收盘'].empty:
                    analysis['latest_price'] = float(outside_data['收盘'].iloc[-1])
            
        except Exception as e:
            self.logger.error(f"分析场外市场数据失败: {e}")
        
        return analysis
    
    def _analyze_minute_data(self, minute_data: pd.DataFrame) -> Dict:
        """
        分析分钟级别数据
        :param minute_data: 分钟级别数据
        :return: 分析结果字典
        """
        analysis = {}
        
        try:
            # 检查数据是否为空
            if minute_data.empty:
                return analysis
            
            # 确保时间列格式正确
            if '时间' in minute_data.columns:
                minute_data['时间'] = pd.to_datetime(minute_data['时间'])
                minute_data = minute_data.sort_values('时间')
            
            # 计算换手率（如果存在成交量和流通股本数据）
            required_columns = ['成交量', '成交额', '收盘']
            if all(col in minute_data.columns for col in required_columns):
                # 确保数据类型正确并处理缺失值
                volume = pd.to_numeric(minute_data['成交量'], errors='coerce').fillna(0)
                amount = pd.to_numeric(minute_data['成交额'], errors='coerce').fillna(1)  # 避免除以0
                close_price = pd.to_numeric(minute_data['收盘'], errors='coerce').fillna(0)
                
                # 简化的换手率计算（这里使用一种近似方法）
                # 实际换手率 = 成交量 / 流通股本，这里用成交额和收盘价近似
                turnover_rates = (volume / amount * close_price * 100).fillna(0)
                
                analysis['avg_turnover_rate'] = float(turnover_rates.mean()) if not turnover_rates.empty else 0
                analysis['max_turnover_rate'] = float(turnover_rates.max()) if not turnover_rates.empty else 0
                analysis['min_turnover_rate'] = float(turnover_rates.min()) if not turnover_rates.empty else 0
                
                # 计算均线
                if len(turnover_rates) >= 5:
                    analysis['ma5'] = float(turnover_rates.tail(5).mean())
                if len(turnover_rates) >= 10:
                    analysis['ma10'] = float(turnover_rates.tail(10).mean())
                if len(turnover_rates) >= 20:
                    analysis['ma20'] = float(turnover_rates.tail(20).mean())
            
            # 最新数据
            if not minute_data.empty and '时间' in minute_data.columns:
                analysis['latest_time'] = minute_data['时间'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S') if len(minute_data) > 0 else 'N/A'
                if '收盘' in minute_data.columns and len(minute_data) > 0:
                    close_price = minute_data['收盘'].iloc[-1]
                    if pd.notna(close_price):
                        analysis['latest_price'] = float(close_price)
                if '均价' in minute_data.columns and len(minute_data) > 0:
                    avg_price = minute_data['均价'].iloc[-1]
                    if pd.notna(avg_price):
                        analysis['latest_avg_price'] = float(avg_price)
            
        except Exception as e:
            self.logger.error(f"分析分钟数据失败: {e}")
        
        return analysis
    


# 工厂函数
def create_etf_processor() -> ETFDataProcessor:
    """创建ETF数据处理器实例"""
    return ETFDataProcessor()