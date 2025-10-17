 config.py
from typing import Dict, Any

class TradingConfig:
    """Конфигурация торговли с настраиваемыми параметрами"""

    def __init__(self):
        # 🔧 НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ (можно менять перед запуском)
        self.LEVERAGE = 8                    # Плечо 5-10x
        self.POSITION_SIZE_PERCENT = 25      # Размер позиции 20-30% от депозита
        self.MAX_DAILY_LOSS_PERCENT = 5      # Макс дневная просадка 5%
        self.DAILY_TRADE_LIMIT = 3           # Макс 3 сделки в день
        self.MIN_CONFIDENCE = 0.65           # Минимальная уверенность сигнала
        self.MIN_ADX = 20                    # Минимальный ADX для тренда

        # Торговые пары
        self.TRADING_PAIRS = [
            'BTC/USDT:USDT',
            'ETH/USDT:USDT', 
            'SOL/USDT:USDT',
            'BNB/USDT:USDT'
        ]

        # API ключи
        self.BYBIT_API_KEY = ""
        self.BYBIT_SECRET = ""
        self.GROK_API_KEY = ""

    def update_config(self, **kwargs):
        """Обновление конфигурации"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Конфигурация обновлена: {key} = {value}")

    def get_config_summary(self) -> Dict[str, Any]:
        """Получение сводки конфигурации"""
        return {
            'leverage': self.LEVERAGE,
            'position_size_percent': self.POSITION_SIZE_PERCENT,
            'max_daily_loss_percent': self.MAX_DAILY_LOSS_PERCENT,
            'daily_trade_limit': self.DAILY_TRADE_LIMIT,
            'min_confidence': self.MIN_CONFIDENCE,
            'min_adx': self.MIN_ADX,
            'trading_pairs': self.TRADING_PAIRS
        }

# Глобальный объект конфигурации
CONFIG = TradingConfig()
