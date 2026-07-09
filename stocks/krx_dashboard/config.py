import json
from pathlib import Path

from .models import Config


DEFAULT_CONFIG_PATH = Path("stocks/krx_dashboard/config.json")


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    return Config(
        host=raw.get("host", "0.0.0.0"),
        port=int(raw.get("port", 8765)),
        update_times=list(raw.get("update_times", ["09:20", "12:30", "16:00"])),
        market_index=raw.get("market_index", "KOSPI"),
        manual_universe_csv=raw.get("manual_universe_csv", "data/krx_universe.csv"),
        snapshots_csv=raw.get("snapshots_csv", "data/krx_snapshots.csv"),
        scores_csv=raw.get("scores_csv", "data/krx_scores.csv"),
        events_csv=raw.get("events_csv", "data/krx_events.csv"),
        min_trading_value_krw=int(raw.get("min_trading_value_krw", 5_000_000_000)),
        weights=dict(raw.get("weights", {})),
    )

