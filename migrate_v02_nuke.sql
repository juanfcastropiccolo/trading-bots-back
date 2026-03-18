-- ============================================================
-- Crypto Trading Mission Control v0.2.0 — FULL RESET
-- ============================================================
-- WARNING: This drops ALL tables and data, then recreates.
-- The backend auto-seeds BTC + ETH agents on startup.
-- Run this in Supabase SQL Editor.
-- ============================================================

-- 1. Drop tables in FK-safe order (children first)
DROP TABLE IF EXISTS rl_models CASCADE;
DROP TABLE IF EXISTS portfolio_snapshots CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS risk_checks CASCADE;
DROP TABLE IF EXISTS llm_decisions CASCADE;
DROP TABLE IF EXISTS strategy_votes CASCADE;
DROP TABLE IF EXISTS features_extended CASCADE;
DROP TABLE IF EXISTS features CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS market_snapshots CASCADE;
DROP TABLE IF EXISTS agent_configs CASCADE;

-- 2. Recreate all tables (v0.2.0 schema)

CREATE TABLE agent_configs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT 'BTC/USDT',
    strategy TEXT NOT NULL DEFAULT 'trend_following',
    budget_usd DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    max_trade_usd DOUBLE PRECISION NOT NULL DEFAULT 10.0,
    mode TEXT NOT NULL DEFAULT 'paper',
    is_active BOOLEAN DEFAULT TRUE,
    -- Risk profile
    max_position_pct DOUBLE PRECISION DEFAULT 0.50,
    drawdown_limit_pct DOUBLE PRECISION DEFAULT 0.20,
    daily_loss_limit_pct DOUBLE PRECISION DEFAULT 0.05,
    cooldown_minutes INTEGER DEFAULT 2,
    max_consecutive_losses INTEGER DEFAULT 3,
    rsi_buy_max DOUBLE PRECISION DEFAULT 70.0,
    rsi_sell_min DOUBLE PRECISION DEFAULT 30.0,
    -- v0.2: Advanced strategy config
    strategy_weights TEXT DEFAULT NULL,          -- JSON: {"ema_crossover": 1.5, ...}
    stop_loss_atr_mult DOUBLE PRECISION DEFAULT 2.0,
    take_profit_atr_mult DOUBLE PRECISION DEFAULT 3.0,
    risk_per_trade_pct DOUBLE PRECISION DEFAULT 0.02,
    enable_rl BOOLEAN DEFAULT FALSE,
    -- Lifecycle
    is_protected BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE market_snapshots (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    ema_fast DOUBLE PRECISION,
    ema_slow DOUBLE PRECISION,
    rsi DOUBLE PRECISION,
    atr DOUBLE PRECISION,
    close DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE features_extended (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    -- Moving averages
    ema_9 DOUBLE PRECISION,
    ema_21 DOUBLE PRECISION,
    ema_50 DOUBLE PRECISION,
    -- Momentum
    rsi DOUBLE PRECISION,
    stoch_k DOUBLE PRECISION,
    stoch_d DOUBLE PRECISION,
    macd_line DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    macd_hist DOUBLE PRECISION,
    -- Volatility
    atr DOUBLE PRECISION,
    bb_upper DOUBLE PRECISION,
    bb_middle DOUBLE PRECISION,
    bb_lower DOUBLE PRECISION,
    bb_width DOUBLE PRECISION,
    bb_pct DOUBLE PRECISION,
    psar DOUBLE PRECISION,
    -- Trend
    adx DOUBLE PRECISION,
    plus_di DOUBLE PRECISION,
    minus_di DOUBLE PRECISION,
    donchian_high DOUBLE PRECISION,
    donchian_low DOUBLE PRECISION,
    -- Volume
    obv DOUBLE PRECISION,
    obv_delta DOUBLE PRECISION,
    vol_sma_20 DOUBLE PRECISION,
    vol_ratio DOUBLE PRECISION,
    -- Fibonacci
    fib_382 DOUBLE PRECISION,
    fib_500 DOUBLE PRECISION,
    fib_618 DOUBLE PRECISION,
    fib_proximity DOUBLE PRECISION,
    -- Close
    close DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    direction TEXT NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    reason TEXT,
    ensemble_score DOUBLE PRECISION DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE strategy_votes (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    signal_id INTEGER REFERENCES signals(id),
    strategy_name TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    weight DOUBLE PRECISION DEFAULT 1.0,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE llm_decisions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    signal_id INTEGER REFERENCES signals(id),
    model_used TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DOUBLE PRECISION DEFAULT 0.0,
    reasoning TEXT,
    recommendation TEXT,
    confidence_adjustment DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE risk_checks (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    signal_id INTEGER REFERENCES signals(id),
    approved BOOLEAN NOT NULL,
    max_trade_ok BOOLEAN DEFAULT TRUE,
    max_position_ok BOOLEAN DEFAULT TRUE,
    drawdown_ok BOOLEAN DEFAULT TRUE,
    daily_loss_ok BOOLEAN DEFAULT TRUE,
    cooldown_ok BOOLEAN DEFAULT TRUE,
    consecutive_loss_ok BOOLEAN DEFAULT TRUE,
    data_complete_ok BOOLEAN DEFAULT TRUE,
    rejection_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    signal_id INTEGER REFERENCES signals(id),
    side TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    fee DOUBLE PRECISION DEFAULT 0.0,
    slippage DOUBLE PRECISION DEFAULT 0.0,
    total_cost DOUBLE PRECISION NOT NULL,
    status TEXT DEFAULT 'filled',
    mode TEXT DEFAULT 'paper',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    side TEXT NOT NULL,
    entry_price DOUBLE PRECISION DEFAULT 0.0,
    quantity DOUBLE PRECISION DEFAULT 0.0,
    unrealized_pnl DOUBLE PRECISION DEFAULT 0.0,
    realized_pnl DOUBLE PRECISION DEFAULT 0.0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    cash DOUBLE PRECISION NOT NULL,
    equity DOUBLE PRECISION NOT NULL,
    total_pnl DOUBLE PRECISION DEFAULT 0.0,
    total_pnl_pct DOUBLE PRECISION DEFAULT 0.0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    max_drawdown DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE rl_models (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    model_type TEXT NOT NULL DEFAULT 'q_learning',
    model_data BYTEA,
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Performance indexes
CREATE INDEX idx_market_snapshots_agent_id ON market_snapshots(agent_id);
CREATE INDEX idx_features_agent_id ON features(agent_id);
CREATE INDEX idx_features_extended_agent_id ON features_extended(agent_id);
CREATE INDEX idx_signals_agent_id ON signals(agent_id);
CREATE INDEX idx_strategy_votes_signal_id ON strategy_votes(signal_id);
CREATE INDEX idx_orders_agent_id ON orders(agent_id);
CREATE INDEX idx_portfolio_snapshots_agent_id ON portfolio_snapshots(agent_id);
CREATE INDEX idx_rl_models_agent_id ON rl_models(agent_id);
