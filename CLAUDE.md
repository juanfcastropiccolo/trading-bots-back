# Backend — Trading Bots

FastAPI + Google ADK multi-agent trading system con paper trading.

## Stack

- **Framework**: FastAPI 0.115+
- **Agents**: Google ADK (SequentialAgent + BaseAgent)
- **LLM**: Claude 3 Haiku via LiteLLM
- **Exchange**: CCXT (Binance US) con rate limiting (5s min, 10/min cap)
- **DB**: SQLAlchemy (SQLite dev, PostgreSQL prod)
- **Deploy**: Railway (Procfile)

## Estructura

```
app/
├── main.py                  # Lifespan, CORS, routers
├── config.py                # Pydantic settings (.env)
├── database.py              # Engine + SessionLocal
├── websocket_manager.py     # Broadcast a clientes WS
├── models/tables.py         # 9 modelos ORM
├── schemas/schemas.py       # Pydantic request/response
├── services/
│   ├── exchange.py          # CCXT Binance US + RateLimiter
│   ├── feature_engine.py    # EMA(9/21), RSI(14), ATR(14)
│   ├── strategy_engine.py   # Trend following (EMA crossover)
│   ├── risk_manager.py      # 7-point risk validation
│   ├── execution_engine.py  # Paper trade simulation
│   └── portfolio_manager.py # P&L, drawdown, equity
├── adk/
│   ├── pipeline.py          # 7-agent SequentialAgent
│   ├── loop.py              # Multi-agent orchestrator
│   └── agents/              # 7 agentes individuales
└── api/
    ├── agents.py            # CRUD + hot-add/remove
    ├── trades.py            # Trade history
    ├── signals.py           # Signals + LLM context
    ├── market.py            # Candles + snapshots
    └── ws.py                # WebSocket /ws/live
```

## Pipeline de Agentes (por tick)

```
1. DataIngestionAgent  → ohlcv_data, current_price
2. FeatureCalcAgent    → features (ema_fast, ema_slow, rsi, atr)
3. StrategyEvalAgent   → signal (BUY/SELL/HOLD + confidence)
4. LLMReasonerAgent    → llm_reasoning (Claude advisory, JSON)
5. RiskCheckAgent      → risk_approval (7 checks)
6. ExecutionAgent      → trade_result (paper order)
7. PersistenceAgent    → DB save + WebSocket broadcast
```

Los agentes comparten `ctx.session.state`. Si `tick_error` se setea, los BaseAgent downstream hacen skip. El LLMReasoner usa templates ADK `{current_price}`, `{features[...]}`, `{signal[...]}` que se resuelven ANTES de ejecutar el agente — por eso el session state debe tener defaults para estas variables.

## Estado del Session (defaults en loop.py)

```python
state = {
    "agent_config": {...},
    "portfolio": {...},
    "current_price": 0.0,            # Default requerido por template LLM
    "features": {ema_fast, ema_slow, rsi, atr, close},  # Idem
    "signal": {direction, confidence, reason},            # Idem
    "tick_error": None,
    "risk_approval": None,
    "trade_result": None,
    "llm_reasoning": None,
}
```

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET/POST | `/api/agents` | Listar / crear agentes |
| DELETE | `/api/agents/{id}` | Soft delete |
| PATCH | `/api/agents/{id}/toggle` | Pausar/reanudar |
| POST | `/api/agents/{id}/add-funds` | Agregar fondos |
| GET | `/api/agents/{id}/trades` | Historial de trades |
| GET | `/api/agents/{id}/signals` | Historial de signals |
| GET | `/api/market/{symbol}/candles` | Candles con cache |
| GET | `/api/agents/{id}/snapshots` | Portfolio history |
| WS | `/ws/live` | Ticks en tiempo real |

## Comandos

```bash
# Dev
uvicorn app.main:app --reload --port 8000

# Deps
pip install -e ".[dev]"
# o
pip install -r requirements.txt
```

## Notas Importantes

- Railway usa servidores en US → usar `ccxt.binanceus()`, NO `ccxt.binance()` (HTTP 451)
- El LLMReasoner es un `Agent` ADK (no BaseAgent), sus templates se resuelven antes de `_run_async_impl` → siempre inicializar las variables del template en el state
- Los agentes protegidos (BTC/ETH) se seedean automáticamente al iniciar
- Portfolio se restaura de DB al reiniciar (no se pierde estado)
- Rate limiter compartido para todas las llamadas a Binance
