"""
ETF数据处理模块 - A股ETF查询系统
处理ETF的场外资金申购、份额变动、融资流向等数据
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from config import MARGIN_TRADING_CONFIG
from utils import format_number

class ETFDataProcessor:
    """ETF数据处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_etf_data(self, fund_flow_data: pd.DataFrame, share_change_data: pd.DataFrame, 
                        outside_data: pd.DataFrame, minute_data: pd.DataFrame = pd.DataFrame(), 
                        margin_data: pd.DataFrame = pd.DataFrame()) -> Dict:
        """
        处理ETF相关数据
        :param fund_flow_data: 资金流向数据
        :param share_change_data: 份额变动数据
        :param outside_data: 场外市场数据
        :param minute_data: 分钟级别数据
        :param margin_data: 融资买入数据
        :return: 处理后的ETF数据字典
        """
        try:
            processed_data = {
                'fund_flow': fund_flow_data,
                'share_changes': share_change_data,
                'outside_market': outside_data,
                'minute_data': minute_data,
                'margin_data': margin_data,
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
            
            # 分析融资买入数据
            if not margin_data.empty:
                processed_data['analysis']['margin_data'] = self._analyze_margin_data(margin_data)
            
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
            
            # 主要指标计算
            if '成交额' in fund_flow_data.columns:
                turnover = fund_flow_data['成交额']
                analysis['total_turnover'] = float(turnover.sum()) if not turnover.empty else 0  # 总成交额
                analysis['avg_daily_turnover'] = float(turnover.mean()) if not turnover.empty else 0  # 日均成交额
                analysis['max_daily_turnover'] = float(turnover.max()) if not turnover.empty else 0   # 单日最大成交额
                analysis['min_daily_turnover'] = float(turnover.min()) if not turnover.empty else 0   # 单日最小成交额
                
                # 资金流向趋势
                if len(turnover) > 1:
                    recent_avg = float(turnover.iloc[-5:].mean()) if len(turnover) >= 5 else float(turnover.iloc[-1])
                    overall_avg = float(turnover.mean())
                    analysis['recent_trend'] = '资金流入' if recent_avg > overall_avg else '资金流出'
                    analysis['trend_strength'] = '强' if recent_avg > overall_avg * 1.2 else '弱'
            
            # 最近数据
            if not fund_flow_data.empty:
                analysis['latest_date'] = fund_flow_data['日期'].iloc[-1].strftime('%Y-%m-%d') if '日期' in fund_flow_data.columns else 'N/A'
                if '成交额' in fund_flow_data.columns:
                    analysis['latest_turnover'] = float(fund_flow_data['成交额'].iloc[-1]) if not fund_flow_data['成交额'].empty else 0
            
        except Exception as e:
            self.logger.error(f"分析资金流向失败: {e}")
        
        return analysis
    
    def _analyze_share_changes(self, share_change_data: pd.DataFrame) -> Dict:
        """
        分析份额变动（基于成交量分析）
        :param share_change_data: 份额变动数据
        :return: 分析结果字典
        """
        analysis = {}
        
        try:
            # 确保日期列格式正确
            if '日期' in share_change_data.columns:
                share_change_data['日期'] = pd.to_datetime(share_change_data['日期'])
                share_change_data = share_change_data.sort_values('日期')
            
            # 主要指标计算 - 基于成交量分析份额变动趋势
            if '成交量' in share_change_data.columns:
                volume = share_change_data['成交量']
                analysis['total_volume'] = float(volume.sum()) if not volume.empty else 0  # 总成交量
                analysis['avg_daily_volume'] = float(volume.mean()) if not volume.empty else 0  # 日均成交量
                analysis['max_daily_volume'] = float(volume.max()) if not volume.empty else 0   # 单日最大成交量
                analysis['min_daily_volume'] = float(volume.min()) if not volume.empty else 0   # 单日最小成交量
                
                # 成交量趋势（作为份额变动的代理指标）
                if len(volume) > 1:
                    recent_avg = float(volume.iloc[-5:].mean()) if len(volume) >= 5 else float(volume.iloc[-1])
                    overall_avg = float(volume.mean())
                    analysis['recent_trend'] = '高活跃度' if recent_avg > overall_avg else '低活跃度'
                    analysis['trend_strength'] = '强' if recent_avg > overall_avg * 1.2 else '弱'
            
            # 价格变动分析（作为份额价值变动的参考）
            if '收盘' in share_change_data.columns and len(share_change_data) > 1:
                prices = share_change_data['收盘']
                price_change = float(prices.iloc[-1]) - float(prices.iloc[0]) if not prices.empty else 0
                price_change_rate = (price_change / float(prices.iloc[0]) * 100) if float(prices.iloc[0]) != 0 and not prices.empty else 0
                
                analysis['price_change'] = price_change
                analysis['price_change_rate'] = price_change_rate
            
            # 最近数据
            if not share_change_data.empty:
                analysis['latest_date'] = share_change_data['日期'].iloc[-1].strftime('%Y-%m-%d') if '日期' in share_change_data.columns else 'N/A'
                if '收盘' in share_change_data.columns:
                    analysis['latest_price'] = float(share_change_data['收盘'].iloc[-1]) if not share_change_data['收盘'].empty else 0
                if '成交量' in share_change_data.columns:
                    analysis['latest_volume'] = float(share_change_data['成交量'].iloc[-1]) if not share_change_data['成交量'].empty else 0
            
        except Exception as e:
            self.logger.error(f"分析份额变动失败: {e}")
        
        return analysis
    
    def _analyze_outside_market(self, outside_data: pd.DataFrame) -> Dict:
        """
        分析场外市场数据
        :param outside_data: 场外市场数据
        :return: 分析结果字典
        """
        analysis = {}
        
        try:
            # 确保日期列格式正确
            if '日期' in outside_data.columns:
                outside_data['日期'] = pd.to_datetime(outside_data['日期'])
                outside_data = outside_data.sort_values('日期')
            
            # 主要指标计算
            if '涨跌幅' in outside_data.columns:
                change_rates = outside_data['涨跌幅']
                analysis['avg_change_rate'] = float(change_rates.mean()) if not change_rates.empty else 0  # 平均涨跌幅
                analysis['max_change_rate'] = float(change_rates.max()) if not change_rates.empty else 0   # 最大涨幅
                analysis['min_change_rate'] = float(change_rates.min()) if not change_rates.empty else 0   # 最大跌幅
                analysis['volatility'] = float(change_rates.std()) if not change_rates.empty else 0        # 波动率
                
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
    
    def _analyze_margin_data(self, margin_data: pd.DataFrame) -> Dict:
        """
        分析融资买入数据
        :param margin_data: 融资买入数据
        :return: 分析结果字典
        """
        analysis = {}
        
        try:
            # 检查数据是否为空
            if margin_data.empty:
                return analysis
            
            # 分析融资买入数据
            if not margin_data.empty and len(margin_data) > 0:
                # 获取融资买入相关字段
                if '融资买入额' in margin_data.columns:
                    margin_buy_amount = margin_data['融资买入额'].iloc[0] if len(margin_data) > 0 else None
                    if pd.notna(margin_buy_amount) and margin_buy_amount != '' and margin_buy_amount is not None:
                        try:
                            analysis['margin_buy_amount'] = float(margin_buy_amount)
                        except (ValueError, TypeError):
                            analysis['margin_buy_amount'] = 0
                    else:
                        analysis['margin_buy_amount'] = 0
                
                if '融资余额' in margin_data.columns:
                    margin_balance = margin_data['融资余额'].iloc[0] if len(margin_data) > 0 else None
                    if pd.notna(margin_balance) and margin_balance != '' and margin_balance is not None:
                        try:
                            analysis['margin_balance'] = float(margin_balance)
                        except (ValueError, TypeError):
                            analysis['margin_balance'] = 0
                    else:
                        analysis['margin_balance'] = 0
                
                if '融券卖出量' in margin_data.columns:
                    short_sell_volume = margin_data['融券卖出量'].iloc[0] if len(margin_data) > 0 else None
                    if pd.notna(short_sell_volume) and short_sell_volume != '' and short_sell_volume is not None:
                        try:
                            analysis['short_sell_volume'] = float(short_sell_volume)
                        except (ValueError, TypeError):
                            analysis['short_sell_volume'] = 0
                    else:
                        analysis['short_sell_volume'] = 0
                
                if '融券余量' in margin_data.columns:
                    short_balance_volume = margin_data['融券余量'].iloc[0] if len(margin_data) > 0 else None
                    if pd.notna(short_balance_volume) and short_balance_volume != '' and short_balance_volume is not None:
                        try:
                            analysis['short_balance_volume'] = float(short_balance_volume)
                        except (ValueError, TypeError):
                            analysis['short_balance_volume'] = 0
                    else:
                        analysis['short_balance_volume'] = 0
                
                # 添加证券信息
                if '证券代码' in margin_data.columns and len(margin_data) > 0:
                    security_code = margin_data['证券代码'].iloc[0] if len(margin_data) > 0 else 'N/A'
                    if pd.notna(security_code) and security_code != '' and security_code is not None:
                        analysis['security_code'] = str(security_code)
                    else:
                        analysis['security_code'] = 'N/A'
                if '证券简称' in margin_data.columns and len(margin_data) > 0:
                    security_name = margin_data['证券简称'].iloc[0] if len(margin_data) > 0 else 'N/A'
                    if pd.notna(security_name) and security_name != '' and security_name is not None:
                        analysis['security_name'] = str(security_name)
                    else:
                        analysis['security_name'] = 'N/A'
            
        except Exception as e:
            self.logger.error(f"分析融资买入数据失败: {e}")
        
        return analysis

# 工厂函数
def create_etf_processor() -> ETFDataProcessor:
    """创建ETF数据处理器实例"""
    return ETFDataProcessor()