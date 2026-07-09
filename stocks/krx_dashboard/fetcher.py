import csv
import io
import urllib.parse
import urllib.request
from datetime import datetime

from .models import Config, StockSnapshot
from .storage import read_csv_rows


KRX_OTP_URL = "https://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
KRX_DOWNLOAD_URL = "https://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"


def _to_number(value: str) -> float:
    cleaned = (value or "").replace(",", "").replace("%", "").strip()
    if cleaned in {"", "-"}:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _post_form(url: str, payload: dict[str, str], timeout: int = 12) -> bytes:
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
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_krx_stock_snapshot(config: Config, trade_date: str | None = None) -> list[StockSnapshot]:
    date = trade_date or datetime.now().strftime("%Y%m%d")
    otp_payload = {
        "locale": "ko_KR",
        "mktId": "ALL",
        "trdDd": date,
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false",
        "name": "fileDown",
        "url": "dbms/MDC/STAT/standard/MDCSTAT01501",
    }
    otp = _post_form(KRX_OTP_URL, otp_payload).decode("utf-8").strip()
    csv_bytes = _post_form(KRX_DOWNLOAD_URL, {"code": otp})
    text = csv_bytes.decode("euc-kr", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))

    snapshots: list[StockSnapshot] = []
    for row in rows:
        ticker = row.get("종목코드", "").strip()
        if not ticker:
            continue
        close = _to_number(row.get("종가", ""))
        trading_value = int(_to_number(row.get("거래대금", "")) * 1_000_000)
        snapshots.append(
            StockSnapshot(
                date=f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                ticker=ticker,
                name=row.get("종목명", "").strip(),
                market=row.get("시장구분", "").strip(),
                close=close,
                change_rate=_to_number(row.get("등락률", "")),
                volume=int(_to_number(row.get("거래량", ""))),
                trading_value=trading_value,
            )
        )
    return snapshots


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

