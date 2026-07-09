from collections import defaultdict
from datetime import datetime
from statistics import mean

from .models import Config, StockSnapshot
from .storage import read_csv_rows


def _num(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _latest_by_ticker(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    latest = {}
    for row in rows:
        ticker = row.get("ticker", "")
        if ticker:
            latest[ticker] = row
    return latest


def calculate_scores(config: Config, snapshots: list[StockSnapshot]) -> list[dict[str, object]]:
    history_rows = read_csv_rows(config.snapshots_csv)
    universe = _latest_by_ticker(read_csv_rows(config.manual_universe_csv))
    by_ticker: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in history_rows:
        if row.get("ticker"):
            by_ticker[row["ticker"]].append(row)

    market_change = _market_change_proxy(snapshots, config)
    scored = []
    for snapshot in snapshots:
        manual = universe.get(snapshot.ticker, {})
        ticker_history = by_ticker.get(snapshot.ticker, [])
        trading_value_score = _trading_value_score(snapshot, ticker_history, config)
        relative_strength = _relative_strength_score(snapshot.change_rate, market_change)
        growth_score = _clamp(_num(manual.get("growth_score"), 50))
        etf_exposure_score = _clamp(_num(manual.get("etf_exposure_score"), 30))
        risk_score = _risk_score(snapshot, trading_value_score, manual.get("risk_note", ""))
        weights = config.weights
        final_score = (
            relative_strength * weights.get("relative_strength", 0.3)
            + trading_value_score * weights.get("trading_value", 0.2)
            + etf_exposure_score * weights.get("etf_exposure", 0.2)
            + growth_score * weights.get("growth_evidence", 0.2)
            - risk_score * weights.get("risk", 0.1)
        )
        scored.append(
            {
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "date": snapshot.date,
                "ticker": snapshot.ticker,
                "name": snapshot.name,
                "market": snapshot.market,
                "sector": manual.get("sector", ""),
                "close": round(snapshot.close, 2),
                "change_rate": round(snapshot.change_rate, 2),
                "volume": snapshot.volume,
                "trading_value": snapshot.trading_value,
                "market_change_proxy": round(market_change, 2),
                "relative_strength_score": round(relative_strength, 1),
                "trading_value_score": round(trading_value_score, 1),
                "etf_exposure_score": round(etf_exposure_score, 1),
                "growth_score": round(growth_score, 1),
                "risk_score": round(risk_score, 1),
                "final_score": round(_clamp(final_score), 1),
                "risk_note": manual.get("risk_note", ""),
                "thesis": manual.get("thesis", ""),
            }
        )
    scored.sort(key=lambda row: (-float(row["final_score"]), row["ticker"]))
    return scored


def _market_change_proxy(snapshots: list[StockSnapshot], config: Config) -> float:
    large = [snapshot.change_rate for snapshot in snapshots if snapshot.trading_value >= config.min_trading_value_krw]
    if len(large) >= 20:
        return mean(large)
    values = [snapshot.change_rate for snapshot in snapshots]
    return mean(values) if values else 0.0


def _relative_strength_score(stock_change: float, market_change: float) -> float:
    spread = stock_change - market_change
    return _clamp(50 + spread * 8)


def _trading_value_score(snapshot: StockSnapshot, history: list[dict[str, str]], config: Config) -> float:
    if snapshot.trading_value <= 0:
        return 35.0
    historic_values = [_num(row.get("trading_value")) for row in history[-120:] if _num(row.get("trading_value")) > 0]
    baseline = mean(historic_values) if historic_values else config.min_trading_value_krw
    maintenance = snapshot.trading_value / baseline if baseline else 0
    liquidity = snapshot.trading_value / config.min_trading_value_krw if config.min_trading_value_krw else 0
    return _clamp(40 + min(maintenance, 2.0) * 25 + min(liquidity, 3.0) * 10)


def _risk_score(snapshot: StockSnapshot, trading_value_score: float, risk_note: str) -> float:
    risk = 0.0
    if snapshot.change_rate <= -7:
        risk += 25
    if trading_value_score < 45:
        risk += 20
    if risk_note.strip():
        risk += 15
    return _clamp(risk)

