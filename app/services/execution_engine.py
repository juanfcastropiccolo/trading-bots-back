from datetime import datetime


SLIPPAGE_PCT = 0.0005  # 0.05%
FEE_PCT = 0.001  # 0.1%


def simulate_trade(
    signal: dict,
    current_price: float,
    portfolio: dict,
    agent_config: dict,
    features: dict | None = None,
) -> dict | None:
    direction = signal["direction"]
    max_trade = agent_config.get("max_trade_usd", 10.0)
    budget = agent_config.get("budget_usd", 100.0)
    risk_per_trade_pct = agent_config.get("risk_per_trade_pct", 0.02)

    if direction == "BUY":
        # ATR-based position sizing: risk_amount = budget * risk_pct
        atr = features.get("atr", 0) if features else 0
        sl_mult = agent_config.get("stop_loss_atr_mult", 2.0)

        if atr > 0 and sl_mult > 0:
            risk_amount = budget * risk_per_trade_pct
            # How many units can we risk?
            risk_per_unit = atr * sl_mult
            optimal_qty = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
            optimal_usd = optimal_qty * current_price
            trade_usd = min(max_trade, optimal_usd, portfolio["cash"] * 0.95)
        else:
            trade_usd = min(max_trade, portfolio["cash"] * 0.95)

        if trade_usd < 1.0:
            return None

        slippage = current_price * SLIPPAGE_PCT
        exec_price = current_price + slippage
        fee = trade_usd * FEE_PCT
        net_usd = trade_usd - fee
        quantity = net_usd / exec_price

        new_cash = portfolio["cash"] - trade_usd
        old_qty = portfolio.get("position_qty", 0.0)
        old_entry = portfolio.get("entry_price", 0.0)
        new_qty = old_qty + quantity

        if new_qty > 0:
            new_entry = (old_entry * old_qty + exec_price * quantity) / new_qty
        else:
            new_entry = exec_price

        return {
            "side": "buy",
            "quantity": round(quantity, 8),
            "price": round(exec_price, 2),
            "fee": round(fee, 4),
            "slippage": round(slippage, 2),
            "total_cost": round(trade_usd, 2),
            "status": "filled",
            "mode": "paper",
            "portfolio_update": {
                "cash": round(new_cash, 2),
                "position_qty": round(new_qty, 8),
                "entry_price": round(new_entry, 2),
                "side": "long",
            },
            "created_at": datetime.now().isoformat(),
        }

    elif direction == "SELL":
        position_qty = portfolio.get("position_qty", 0.0)
        if position_qty <= 0:
            return None

        slippage = current_price * SLIPPAGE_PCT
        exec_price = current_price - slippage
        quantity = position_qty  # Sell entire position
        gross_usd = quantity * exec_price
        fee = gross_usd * FEE_PCT
        net_usd = gross_usd - fee

        entry_price = portfolio.get("entry_price", 0.0)
        realized_pnl = (exec_price - entry_price) * quantity - fee

        new_cash = portfolio["cash"] + net_usd

        return {
            "side": "sell",
            "quantity": round(quantity, 8),
            "price": round(exec_price, 2),
            "fee": round(fee, 4),
            "slippage": round(slippage, 2),
            "total_cost": round(gross_usd, 2),
            "status": "filled",
            "mode": "paper",
            "realized_pnl": round(realized_pnl, 4),
            "portfolio_update": {
                "cash": round(new_cash, 2),
                "position_qty": 0.0,
                "entry_price": 0.0,
                "side": "flat",
            },
            "created_at": datetime.now().isoformat(),
        }

    return None
