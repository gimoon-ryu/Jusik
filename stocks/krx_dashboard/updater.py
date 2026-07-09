from datetime import datetime

from .config import load_config
from .fetcher import fetch_krx_stock_snapshot, fetch_quote_fallback_snapshot, load_manual_universe
from .scoring import calculate_scores
from .storage import append_csv_rows, write_csv_rows


SNAPSHOT_FIELDS = ["date", "ticker", "name", "market", "close", "change_rate", "volume", "trading_value"]
SCORE_FIELDS = [
    "updated_at",
    "date",
    "ticker",
    "name",
    "market",
    "sector",
    "close",
    "change_rate",
    "volume",
    "trading_value",
    "market_change_proxy",
    "relative_strength_score",
    "trading_value_score",
    "etf_exposure_score",
    "growth_score",
    "risk_score",
    "final_score",
    "risk_note",
    "thesis",
]
EVENT_FIELDS = ["updated_at", "status", "message", "count"]


def run_update(config_path: str = "stocks/krx_dashboard/config.json") -> list[dict[str, object]]:
    config = load_config(config_path)
    status = "ok"
    message = "KRX snapshot downloaded"
    try:
        snapshots = fetch_krx_stock_snapshot(config)
        if not snapshots:
            raise RuntimeError("KRX returned no stock rows")
    except Exception as exc:
        krx_error = exc
        try:
            snapshots = fetch_quote_fallback_snapshot(config)
            if not snapshots:
                raise RuntimeError("quote fallback returned no rows")
            status = "quote_fallback"
            message = f"KRX download failed; using quote fallback for manual universe: {krx_error}"
        except Exception as fallback_exc:
            status = "fallback"
            message = f"KRX and quote fallback failed; using manual universe: {krx_error}; {fallback_exc}"
            snapshots = load_manual_universe(config)

    snapshot_rows = [
        {
            "date": item.date,
            "ticker": item.ticker,
            "name": item.name,
            "market": item.market,
            "close": item.close,
            "change_rate": item.change_rate,
            "volume": item.volume,
            "trading_value": item.trading_value,
        }
        for item in snapshots
    ]
    append_csv_rows(config.snapshots_csv, snapshot_rows, SNAPSHOT_FIELDS)
    scores = calculate_scores(config, snapshots)
    write_csv_rows(config.scores_csv, scores, SCORE_FIELDS)
    append_csv_rows(
        config.events_csv,
        [
            {
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "status": status,
                "message": message,
                "count": len(scores),
            }
        ],
        EVENT_FIELDS,
    )
    return scores
