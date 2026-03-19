import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load .env into process environment BEFORE any other imports use it (LiteLLM needs this)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Configure LiteLLM retries for transient errors (Anthropic 529 overloaded)
import litellm
litellm.num_retries = 3
litellm.retry_after = 5  # seconds between retries

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, _is_sqlite
from app.websocket_manager import ws_manager
from app.adk.agents.persistence import set_ws_manager
from app.adk.loop import start_loop, request_shutdown
from app.adk.session import init_session_service, close_session_service
from app.api import agents, auth, trades, signals, market, ws

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

RL_RETRAIN_INTERVAL_SECONDS = 6 * 3600  # Every 6 hours


async def _rl_retrain_loop():
    """Background task: retrain RL models every 6 hours."""
    from app.database import SessionLocal
    from app.models import AgentConfig

    while True:
        await asyncio.sleep(RL_RETRAIN_INTERVAL_SECONDS)
        try:
            db = SessionLocal()
            agents_list = (
                db.query(AgentConfig)
                .filter(
                    AgentConfig.is_active.is_(True),
                    AgentConfig.is_deleted.is_(False),
                    AgentConfig.enable_rl.is_(True),
                )
                .all()
            )
            agent_ids = [a.id for a in agents_list]
            db.close()

            if not agent_ids:
                continue

            from app.services.rl.trainer import RLTrainer
            from app.services.rl.model_store import ModelStore

            for agent_id in agent_ids:
                try:
                    trainer = RLTrainer(agent_id)
                    rl_agent = trainer.train_from_history(epochs=5)
                    ModelStore.save(agent_id, rl_agent)
                    logger.info(f"[RL] Retrained model for agent {agent_id}")
                except Exception as e:
                    logger.error(f"[RL] Retrain failed for agent {agent_id}: {e}")

        except Exception as e:
            logger.error(f"[RL] Retrain loop error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if _is_sqlite:
        logger.info("Creating database tables (SQLite)...")
        Base.metadata.create_all(bind=engine)
    else:
        logger.info("Using PostgreSQL — tables managed via schema.sql")

    # Initialize ADK session service (must be before start_loop)
    await init_session_service()

    # Wire up WebSocket manager to persistence agent
    set_ws_manager(ws_manager)

    # Start trading loop
    logger.info("Starting trading loop...")
    loop_task = start_loop()

    # Start RL retrain background task
    rl_task = asyncio.create_task(_rl_retrain_loop())

    yield

    # Shutdown
    logger.info("Shutting down trading loop...")
    request_shutdown()
    loop_task.cancel()
    rl_task.cancel()
    await close_session_service()


app = FastAPI(
    title="Crypto Trading Mission Control",
    version="0.2.0",
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGIN", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(trades.router)
app.include_router(signals.router)
app.include_router(market.router)
app.include_router(ws.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
