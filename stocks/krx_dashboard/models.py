from dataclasses import dataclass


@dataclass
class Config:
    host: str
    port: int
    update_times: list[str]
    market_index: str
    manual_universe_csv: str
    snapshots_csv: str
    scores_csv: str
    events_csv: str
    min_trading_value_krw: int
    weights: dict[str, float]


@dataclass
class StockSnapshot:
    date: str
    ticker: str
    name: str
    market: str
    close: float
    change_rate: float
    volume: int
    trading_value: int

