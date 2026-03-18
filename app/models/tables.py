from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from app.database import Base


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False, default="BTC/USDT")
    strategy = Column(String(50), nullable=False, default="trend_following")
    budget_usd = Column(Float, nullable=False, default=100.0)
    max_trade_usd = Column(Float, nullable=False, default=10.0)
    mode = Column(String(20), nullable=False, default="paper")
    is_active = Column(Boolean, default=True)
    # Risk profile
    max_position_pct = Column(Float, default=0.50)
    drawdown_limit_pct = Column(Float, default=0.20)
    daily_loss_limit_pct = Column(Float, default=0.05)
    cooldown_minutes = Column(Integer, default=2)
    max_consecutive_losses = Column(Integer, default=3)
    rsi_buy_max = Column(Float, default=70.0)
    rsi_sell_min = Column(Float, default=30.0)
    # Advanced strategy config
    strategy_weights = Column(Text, default=None)  # JSON: {"ema_crossover": 1.5, ...}
    stop_loss_atr_mult = Column(Float, default=2.0)
    take_profit_atr_mult = Column(Float, default=3.0)
    risk_per_trade_pct = Column(Float, default=0.02)
    enable_rl = Column(Boolean, default=False)
    # Lifecycle
    is_protected = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    ema_fast = Column(Float)
    ema_slow = Column(Float)
    rsi = Column(Float)
    atr = Column(Float)
    close = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class FeatureExtended(Base):
    __tablename__ = "features_extended"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    # Moving averages
    ema_9 = Column(Float)
    ema_21 = Column(Float)
    ema_50 = Column(Float)
    # Momentum
    rsi = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)
    macd_line = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    # Volatility
    atr = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_width = Column(Float)
    bb_pct = Column(Float)
    psar = Column(Float)
    # Trend
    adx = Column(Float)
    plus_di = Column(Float)
    minus_di = Column(Float)
    donchian_high = Column(Float)
    donchian_low = Column(Float)
    # Volume
    obv = Column(Float)
    obv_delta = Column(Float)
    vol_sma_20 = Column(Float)
    vol_ratio = Column(Float)
    # Fibonacci
    fib_382 = Column(Float)
    fib_500 = Column(Float)
    fib_618 = Column(Float)
    fib_proximity = Column(Float)
    # Close
    close = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    direction = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, default=0.0)
    reason = Column(Text)
    ensemble_score = Column(Float, default=None)
    created_at = Column(DateTime, server_default=func.now())


class StrategyVoteRecord(Base):
    __tablename__ = "strategy_votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    strategy_name = Column(String(50), nullable=False)
    score = Column(Float, nullable=False)
    weight = Column(Float, default=1.0)
    reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class LLMDecision(Base):
    __tablename__ = "llm_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    model_used = Column(String(100))
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    reasoning = Column(Text)
    recommendation = Column(String(20))
    confidence_adjustment = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())


class RiskCheck(Base):
    __tablename__ = "risk_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    approved = Column(Boolean, nullable=False)
    max_trade_ok = Column(Boolean, default=True)
    max_position_ok = Column(Boolean, default=True)
    drawdown_ok = Column(Boolean, default=True)
    daily_loss_ok = Column(Boolean, default=True)
    cooldown_ok = Column(Boolean, default=True)
    consecutive_loss_ok = Column(Boolean, default=True)
    data_complete_ok = Column(Boolean, default=True)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    side = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
    total_cost = Column(Float, nullable=False)
    status = Column(String(20), default="filled")
    mode = Column(String(20), default="paper")
    created_at = Column(DateTime, server_default=func.now())


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    side = Column(String(10), nullable=False)  # long, flat
    entry_price = Column(Float, default=0.0)
    quantity = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    cash = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    total_pnl = Column(Float, default=0.0)
    total_pnl_pct = Column(Float, default=0.0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    max_drawdown = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())


class RLModel(Base):
    __tablename__ = "rl_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=False)
    model_type = Column(String(50), nullable=False, default="q_learning")
    model_data = Column(LargeBinary)
    metadata_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
