# conservative_trading.py
from typing import Dict, List
import time
import logging
from datetime import datetime

from config import CONFIG
from conservative_core import ConservativeQualityFilter, ConservativeGrokFilter, SmartHighLeverageRiskManager

logger = logging.getLogger(__name__)

class ConservativeTradingPipeline:
    """Консервативный торговый пайплайн"""

    def __init__(self, trader, technical_analyzer, social_guard, position_manager):
        self.trader = trader
        self.technical_analyzer = technical_analyzer
        self.social_guard = social_guard
        self.position_manager = position_manager

        # Инициализация консервативных компонентов
        self.quality_filter = ConservativeQualityFilter(CONFIG)
        self.risk_manager = SmartHighLeverageRiskManager(CONFIG)
        self.grok_filter = ConservativeGrokFilter(CONFIG.GROK_API_KEY, CONFIG)

        # Статистика
        self.symbol_trade_count = {}
        self.executed_trades = []
        self.last_trade_day = datetime.now().date()

        logger.info("✅ Консервативный торговый пайплайн инициализирован")

    def process_trade_decision(self, symbol: str) -> Dict:
        """Консервативный процесс принятия решений"""

        try:
            # Проверка дневного лимита
            can_trade, reason = self.risk_manager.can_trade_today(symbol)
            if not can_trade:
                return {'action': 'HOLD', 'reason': reason, 'confidence': 0}

            # Получение данных анализа
            technical_data = self.technical_analyzer.get_multi_timeframe_analysis(symbol, self.trader.exchange)
            primary_trend = self.grok_filter.analyze_primary_trend(symbol, technical_data)
            entry_signal = technical_data['entry']

            # СТРОГАЯ проверка качества
            should_enter, quality_reason = self.quality_filter.should_enter_trade(
                symbol, technical_data, primary_trend, entry_signal
            )

            if not should_enter:
                logger.info(f"🚫 {symbol} - Качество не пройдено: {quality_reason}")
                return {'action': 'HOLD', 'reason': quality_reason, 'confidence': entry_signal['confidence']}

            # Проверка социальных настроений
            should_avoid, social_reason = self.social_guard.should_avoid_trade(
                symbol, {
                    'action': entry_signal['action'],
                    'primary_trend': primary_trend,
                    'confidence': entry_signal['confidence']
                }
            )

            if should_avoid:
                logger.info(f"🚫 {symbol} - Соц. защита: {social_reason}")
                return {'action': 'HOLD', 'reason': social_reason, 'confidence': entry_signal['confidence']}

            # Исполнение сделки
            trade_result = self.execute_conservative_trade(symbol, technical_data, primary_trend, entry_signal)

            if trade_result['executed']:
                self.record_trade_execution(symbol, trade_result['pnl'])
                return {
                    'action': 'EXECUTED', 
                    'trade': trade_result, 
                    'confidence': entry_signal['confidence'],
                    'reason': '✅ Качественная сделка исполнена'
                }
            else:
                return {
                    'action': 'HOLD', 
                    'reason': trade_result.get('reason', 'Ошибка исполнения'), 
                    'confidence': entry_signal['confidence']
                }

        except Exception as e:
            logger.error(f"❌ Ошибка в торговом пайплайне {symbol}: {e}")
            return {'action': 'HOLD', 'reason': f'Ошибка пайплайна: {str(e)}', 'confidence': 0}

    def execute_conservative_trade(self, symbol: str, technical_data: Dict, 
                                 primary_trend: Dict, entry_signal: Dict) -> Dict:
        """Исполнение консервативной сделки"""
        try:
            # Обновляем баланс для риск-менеджера
            account_info = self.trader.get_account_info()
            self.risk_manager.set_account_balance(account_info['total_balance'])

            execution_data = technical_data['execution']
            risk_data = technical_data['risk']

            # Расчет размера позиции
            position_size_usdt = self.risk_manager.calculate_position_size(
                symbol=symbol,
                atr=risk_data['atr'],
                current_price=execution_data['current_price'],
                confidence=entry_signal['confidence'],
                quality_score=1.0  # Максимальное качество, т.к. прошли фильтры
            )

            current_price = execution_data['current_price']
            atr = risk_data['atr']

            # Установка плеча
            self.trader.set_leverage(symbol, CONFIG.LEVERAGE)

            # Расчет стоп-лосса и тейк-профита
            if entry_signal['action'] == 'BUY':
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3.0)
                side = 'buy'
            else:
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3.0)
                side = 'sell'

            # Проверка минимального размера
            if position_size_usdt < 10:
                return {
                    'executed': False, 
                    'reason': f'Слишком маленький размер позиции: {position_size_usdt:.2f} USDT'
                }

            position_size = position_size_usdt / current_price

            logger.info(f"💰 {symbol} - Размер позиции: {position_size_usdt:.2f} USDT ({CONFIG.POSITION_SIZE_PERCENT}%)")
            logger.info(f"📊 {symbol} - Параметры: {side} {position_size:.4f} @ {current_price:.4f}")

            # Создание ордера
            order = self.trader.create_order(
                symbol, 'market', side, position_size,
                take_profit=take_profit,
                stop_loss=stop_loss
            )

            if order:
                trade_info = {
                    'symbol': symbol,
                    'side': side,
                    'size': position_size,
                    'size_usdt': position_size_usdt,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'leverage': CONFIG.LEVERAGE,
                    'timestamp': datetime.now().isoformat(),
                    'confidence': entry_signal['confidence'],
                    'trend': primary_trend['trend']
                }

                self.executed_trades.append(trade_info)

                # Расчет предполагаемого PnL для риск-менеджера
                estimated_pnl = position_size_usdt * 0.02  # Ожидаемая прибыль 2%

                return {
                    'executed': True,
                    'trade': trade_info,
                    'pnl': estimated_pnl,
                    'position_size_usdt': position_size_usdt
                }
            else:
                return {'executed': False, 'reason': 'Ошибка создания ордера'}

        except Exception as e:
            logger.error(f"❌ Ошибка исполнения сделки {symbol}: {e}")
            return {'executed': False, 'reason': f'Ошибка исполнения: {str(e)}'}

    def record_trade_execution(self, symbol: str, pnl: float):
        """Запись исполненной сделки"""
        self.risk_manager.update_trade_result(pnl)

        # Обновление счетчика по символу
        self.symbol_trade_count[symbol] = self.symbol_trade_count.get(symbol, 0) + 1

        logger.info(f"📊 Сделка записана. {symbol}: {self.symbol_trade_count[symbol]}/2 сделок")

    def get_pipeline_stats(self) -> Dict:
        """Получение статистики пайплайна"""
        risk_summary = self.risk_manager.get_risk_summary()

        return {
            'daily_trades': f"{risk_summary['daily_trades']}/{CONFIG.DAILY_TRADE_LIMIT}",
            'daily_pnl': risk_summary['daily_pnl'],
            'consecutive_losses': risk_summary['consecutive_losses'],
            'total_executed_trades': len(self.executed_trades),
            'symbol_trades': self.symbol_trade_count,
            'account_balance': risk_summary['account_balance']
        }

    def reset_daily_stats(self):
        """Сброс дневной статистики"""
        today = datetime.now().date()
        if today != self.last_trade_day:
            self.risk_manager.reset_daily_stats()
            self.symbol_trade_count = {}
            self.last_trade_day = today
            logger.info("🔄 Дневная статистика сброшена")
