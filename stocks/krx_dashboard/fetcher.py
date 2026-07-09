import csv
import io
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from .models import Config, StockSnapshot
from .storage import read_csv_rows


KRX_OTP_URL = "https://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
KRX_DOWNLOAD_URL = "https://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"
NAVER_DAILY_URL = "https://api.finance.naver.com/siseJson.naver"

FIELD_ALIASES = {
    "ticker": ["\uc885\ubaa9\ucf54\ub4dc", "\ub2e8\ucd95\ucf54\ub4dc", "code"],
    "name": ["\uc885\ubaa9\uba85", "\ud55c\uae00 \uc885\ubaa9\uc57d\uba85", "name"],
    "market": ["\uc2dc\uc7a5\uad6c\ubd84", "\uc2dc\uc7a5", "market"],
    "close": ["\uc885\uac00", "\ud604\uc7ac\uac00", "close"],
    "change_rate": ["\ub4f1\ub77d\ub960", "\ub300\ube44\uc728", "change_rate"],
    "volume": ["\uac70\ub798\ub7c9", "volume"],
    "trading_value": ["\uac70\ub798\ub300\uae08", "\uac70\ub798\ub300\uae08(\uc6d0)", "trading_value"],
}


def _to_number(value: str) -> float:
    cleaned = (value or "").replace(",", "").replace("%", "").strip()
    if cleaned in {"", "-"}:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _post_form(
    url: str,
    payload: dict[str, str],
    timeout: int = 12,
    opener: urllib.request.OpenerDirector | None = None,
) -> bytes:
    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 KRX scoring dashboard",
            "Referer": "https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd",
        },
        method="POST",
    )
    http = opener.open if opener else urllib.request.urlopen
    with http(request, timeout=timeout) as response:
        return response.read()


def _decode_csv(csv_bytes: bytes) -> str:
    for encoding in ("euc-kr", "cp949", "utf-8-sig", "utf-8"):
        try:
            return csv_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return csv_bytes.decode("utf-8", errors="replace")


def _candidate_trade_dates(trade_date: str | None = None, lookback_days: int = 14) -> list[str]:
    start = datetime.strptime(trade_date, "%Y%m%d") if trade_date else datetime.now()
    dates = []
    cursor = start
    while len(dates) < lookback_days:
        if cursor.weekday() < 5:
            dates.append(cursor.strftime("%Y%m%d"))
        cursor -= timedelta(days=1)
    return dates


def _row_value(row: dict[str, str], aliases: list[str], fallback_index: int | None = None) -> str:
    for alias in aliases:
        if alias in row:
            return row.get(alias, "")
    if fallback_index is not None:
        values = list(row.values())
        if 0 <= fallback_index < len(values):
            return values[fallback_index]
    return ""


def _parse_stock_rows(rows: list[dict[str, str]], date: str) -> list[StockSnapshot]:
    snapshots: list[StockSnapshot] = []
    for row in rows:
        # KRX stock CSV order is usually:
        # code, name, market, department, close, change, change_rate, open,
        # high, low, volume, trading_value, market_cap, shares.
        ticker = _row_value(row, FIELD_ALIASES["ticker"], 0).strip().zfill(6)
        if not ticker or not ticker.isdigit():
            continue
        snapshots.append(
            StockSnapshot(
                date=f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                ticker=ticker,
                name=_row_value(row, FIELD_ALIASES["name"], 1).strip(),
                market=_row_value(row, FIELD_ALIASES["market"], 2).strip(),
                close=_to_number(_row_value(row, FIELD_ALIASES["close"], 4)),
                change_rate=_to_number(_row_value(row, FIELD_ALIASES["change_rate"], 6)),
                volume=int(_to_number(_row_value(row, FIELD_ALIASES["volume"], 10))),
                trading_value=int(_to_number(_row_value(row, FIELD_ALIASES["trading_value"], 11))),
            )
        )
    return snapshots


def _fetch_krx_stock_snapshot_for_date(date: str) -> list[StockSnapshot]:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    otp_payload = {
        "locale": "ko_KR",
        "mktId": "ALL",
        "trdDd": date,
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false",
        "name": "fileDown",
        "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
    }
    otp = _post_form(KRX_OTP_URL, otp_payload, opener=opener).decode("utf-8").strip()
    if otp == "LOGOUT" or len(otp) < 20:
        raise RuntimeError(f"KRX OTP failed: {otp!r}")
    csv_bytes = _post_form(KRX_DOWNLOAD_URL, {"code": otp}, opener=opener)
    text = _decode_csv(csv_bytes)
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return []
    return _parse_stock_rows(rows, date)


def fetch_krx_stock_snapshot(config: Config, trade_date: str | None = None) -> list[StockSnapshot]:
    del config
    errors = []
    for date in _candidate_trade_dates(trade_date):
        try:
            snapshots = _fetch_krx_stock_snapshot_for_date(date)
        except Exception as exc:
            errors.append(f"{date}: {exc}")
            continue
        if snapshots:
            return snapshots
        errors.append(f"{date}: no rows")
    raise RuntimeError("KRX returned no stock rows for recent dates; " + "; ".join(errors[-5:]))


def _fetch_naver_daily_rows(ticker: str, end_date: datetime, lookback_days: int = 900) -> list[list[object]]:
    start_date = end_date - timedelta(days=lookback_days)
    params = {
        "symbol": ticker,
        "requestType": "1",
        "startTime": start_date.strftime("%Y%m%d"),
        "endTime": end_date.strftime("%Y%m%d"),
        "timeframe": "day",
    }
    url = f"{NAVER_DAILY_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 KRX scoring dashboard",
            "Referer": "https://finance.naver.com",
        },
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        text = response.read().decode("utf-8", errors="replace")
    data_rows = []
    for match in re.finditer(r'\["(\d{8})",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)', text):
        data_rows.append(
            [
                match.group(1),
                float(match.group(2)),
                float(match.group(3)),
                float(match.group(4)),
                float(match.group(5)),
                int(float(match.group(6))),
            ]
        )
    return data_rows


def fetch_quote_fallback_snapshot(config: Config, trade_date: str | None = None) -> list[StockSnapshot]:
    end_date = datetime.strptime(trade_date, "%Y%m%d") if trade_date else datetime.now()
    snapshots = []
    for row in read_csv_rows(config.manual_universe_csv):
        ticker = row.get("ticker", "").zfill(6)
        if not ticker:
            continue
        try:
            daily_rows = _fetch_naver_daily_rows(ticker, end_date)
        except Exception:
            daily_rows = []
        if daily_rows:
            latest = daily_rows[-1]
            previous_close = daily_rows[-2][4] if len(daily_rows) >= 2 else latest[4]
            close = float(latest[4])
            volume = int(latest[5])
            change_rate = ((close - previous_close) / previous_close * 100) if previous_close else 0.0
            snapshots.append(
                StockSnapshot(
                    date=f"{latest[0][:4]}-{latest[0][4:6]}-{latest[0][6:8]}",
                    ticker=ticker,
                    name=row.get("name", ""),
                    market=row.get("market", ""),
                    close=close,
                    change_rate=change_rate,
                    volume=volume,
                    trading_value=int(close * volume),
                )
            )
        else:
            snapshots.append(
                StockSnapshot(
                    date=end_date.strftime("%Y-%m-%d"),
                    ticker=ticker,
                    name=row.get("name", ""),
                    market=row.get("market", ""),
                    close=_to_number(row.get("close", row.get("price", "0"))),
                    change_rate=_to_number(row.get("change_rate", "0")),
                    volume=int(_to_number(row.get("volume", "0"))),
                    trading_value=int(_to_number(row.get("trading_value", "0"))),
                )
            )
    return [snapshot for snapshot in snapshots if snapshot.ticker]


def load_manual_universe(config: Config) -> list[StockSnapshot]:
    today = datetime.now().strftime("%Y-%m-%d")
    snapshots = []
    for row in read_csv_rows(config.manual_universe_csv):
        snapshots.append(
            StockSnapshot(
                date=today,
                ticker=row.get("ticker", "").zfill(6),
                name=row.get("name", ""),
                market=row.get("market", ""),
                close=_to_number(row.get("close", row.get("price", "0"))),
                change_rate=_to_number(row.get("change_rate", "0")),
                volume=int(_to_number(row.get("volume", "0"))),
                trading_value=int(_to_number(row.get("trading_value", "0"))),
            )
        )
    return [snapshot for snapshot in snapshots if snapshot.ticker]
