import logging
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from app.services.exchange import exchange_service
from app.database import SessionLocal
from app.models import MarketSnapshot

logger = logging.getLogger(__name__)

# Load 1h data from DB every N ticks (avoid extra API calls)
HOURLY_REFRESH_INTERVAL = 60  # Every 60 ticks (~1 hour at 60s intervals)


class DataIngestionAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        config = ctx.session.state.get("agent_config", {})
        symbol = config.get("symbol", "BTC/USDT")
        timeframe = config.get("timeframe", "1m")
        agent_id = config.get("id", 1)

        try:
            df = exchange_service.fetch_ohlcv(symbol, timeframe, limit=50)
            ticker = exchange_service.fetch_ticker(symbol)

            # Store serializable data in state (drop timestamp col — stored separately)
            ohlcv = df.drop(columns=["timestamp"]).to_dict(orient="list")
            # Convert numpy types to native Python for JSON serialization
            ctx.session.state["ohlcv_data"] = {
                k: [float(v) for v in vals] for k, vals in ohlcv.items()
            }
            ctx.session.state["ohlcv_timestamps"] = [
                t.isoformat() for t in df["timestamp"]
            ]
            ctx.session.state["current_price"] = float(ticker["last"])
            ctx.session.state["tick_error"] = None

            logger.info(f"Ingested {len(df)} candles for {symbol}, price={ticker['last']}")

            # Multi-timeframe: load 1h candles from DB periodically
            tick_count = ctx.session.state.get("_tick_count", 0) + 1
            ctx.session.state["_tick_count"] = tick_count

            if tick_count % HOURLY_REFRESH_INTERVAL == 1:  # First tick + every N ticks
                self._load_hourly_from_db(ctx, agent_id)

        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            ctx.session.state["tick_error"] = str(e)
            # Preserve last known price if available, otherwise keep default
            if "current_price" not in ctx.session.state:
                ctx.session.state["current_price"] = 0.0

        state = ctx.session.state
        delta = {
            "current_price": state.get("current_price", 0.0),
            "ohlcv_data": state.get("ohlcv_data"),
            "ohlcv_timestamps": state.get("ohlcv_timestamps"),
            "ohlcv_1h_data": state.get("ohlcv_1h_data"),
            "tick_error": state.get("tick_error"),
            "_tick_count": state.get("_tick_count"),
        }
        yield Event(author=self.name, actions=EventActions(state_delta=delta))

    def _load_hourly_from_db(self, ctx, agent_id: int):
        """Load last 50 hourly candles from market_snapshots table."""
        db = SessionLocal()
        try:
            snapshots = (
                db.query(MarketSnapshot)
                .filter(MarketSnapshot.agent_id == agent_id)
                .order_by(MarketSnapshot.id.desc())
                .limit(50)
                .all()
            )
            if len(snapshots) >= 30:
                snapshots = list(reversed(snapshots))
                ctx.session.state["ohlcv_1h_data"] = {
                    "open": [float(s.open) for s in snapshots],
                    "high": [float(s.high) for s in snapshots],
                    "low": [float(s.low) for s in snapshots],
                    "close": [float(s.close) for s in snapshots],
                    "volume": [float(s.volume) for s in snapshots],
                }
                logger.info(f"Loaded {len(snapshots)} historical candles for 1h features")
            else:
                ctx.session.state["ohlcv_1h_data"] = None
        except Exception as e:
            logger.warning(f"Failed to load hourly data: {e}")
            ctx.session.state["ohlcv_1h_data"] = None
        finally:
            db.close()
