from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.config import settings


LLM_INSTRUCTION = """You are a crypto trading advisor analyzing multi-indicator market data.

Current market state:
- Price: {current_price}
- EMA-9: {features[ema_fast]} | EMA-21: {features[ema_slow]} | EMA-50: {features[ema_50]}
- RSI-14: {features[rsi]}
- MACD: line={features[macd_line]}, signal={features[macd_signal]}, hist={features[macd_hist]}
- Stochastic: K={features[stoch_k]}, D={features[stoch_d]}
- ATR-14: {features[atr]}
- Bollinger: upper={features[bb_upper]}, mid={features[bb_middle]}, lower={features[bb_lower]}, %B={features[bb_pct]}
- ADX: {features[adx]}, +DI={features[plus_di]}, -DI={features[minus_di]}
- Volume ratio: {features[vol_ratio]}, OBV delta: {features[obv_delta]}
- PSAR: {features[psar]}
- Fib levels: 38.2%={features[fib_382]}, 50%={features[fib_500]}, 61.8%={features[fib_618]}

Ensemble signal: {signal[direction]} (confidence: {signal[confidence]}, score: {signal[ensemble_score]})
Reason: {signal[reason]}

Provide a JSON response with:
1. "agree": true/false - whether you agree with the ensemble signal
2. "confidence_adjustment": float from -0.3 to +0.3 — how much to adjust the signal's confidence
3. "reasoning": brief explanation (2-3 sentences max)
4. "recommendation": "BUY", "SELL", or "HOLD"
5. "suggested_sl_mult": float 1.5-3.0 — stop-loss ATR multiplier suggestion
6. "suggested_tp_mult": float 2.0-4.0 — take-profit ATR multiplier suggestion

Respond ONLY with valid JSON."""


def create_llm_reasoner() -> Agent:
    return Agent(
        name="llm_reasoner",
        model=LiteLlm(model=settings.llm_model),
        instruction=LLM_INSTRUCTION,
        description="LLM advisor that reasons about trading signals and suggests SL/TP",
        output_key="llm_reasoning",
        include_contents="none",
    )
