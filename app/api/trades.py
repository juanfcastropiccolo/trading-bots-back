from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order
from app.schemas.schemas import TradeResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/agents", tags=["trades"])


@router.get("/{agent_id}/trades", response_model=list[TradeResponse])
def get_trades(
    agent_id: int,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    orders = (
        db.query(Order)
        .filter(Order.agent_id == agent_id)
        .order_by(Order.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return orders
