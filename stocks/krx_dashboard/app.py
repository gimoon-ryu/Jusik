import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import load_config
from .scheduler import DailyScheduler, next_update_label
from .storage import read_csv_rows
from .updater import run_update


CONFIG_PATH = "stocks/krx_dashboard/config.json"


class DashboardHandler(BaseHTTPRequestHandler):
    scheduler: DailyScheduler | None = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_dashboard())
        elif parsed.path == "/api/scores":
            config = load_config(CONFIG_PATH)
            self._send_json(read_csv_rows(config.scores_csv))
        elif parsed.path == "/api/events":
            config = load_config(CONFIG_PATH)
            self._send_json(read_csv_rows(config.events_csv)[-20:])
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/update":
            scores = run_update(CONFIG_PATH)
            self.send_response(303)
            self.send_header("Location", f"/?updated={len(scores)}")
            self.end_headers()
            return
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, value: object) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def render_dashboard() -> str:
    config = load_config(CONFIG_PATH)
    scores = read_csv_rows(config.scores_csv)
    events = read_csv_rows(config.events_csv)
    top_scores = scores[:50]
    updated_at = top_scores[0].get("updated_at", "-") if top_scores else "-"
    next_update = next_update_label(config.update_times)
    rows = "\n".join(render_score_row(row, idx + 1) for idx, row in enumerate(top_scores))
    event_rows = "\n".join(render_event(row) for row in events[-5:][::-1])
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KRX 주식 스코어링</title>
  <style>{CSS}</style>
</head>
<body>
  <header class="topbar">
    <div>
      <h1>KRX 주식 스코어링</h1>
      <p>상대강도, 거래대금 유지, ETF 노출, 성장 근거를 합산한 관심종목 랭킹</p>
    </div>
    <form method="post" action="/update">
      <button type="submit">지금 업데이트</button>
    </form>
  </header>
  <main>
    <section class="metrics">
      <article><span>최근 업데이트</span><strong>{html.escape(updated_at)}</strong></article>
      <article><span>다음 자동 갱신</span><strong>{html.escape(next_update)}</strong></article>
      <article><span>표시 종목</span><strong>{len(top_scores)}</strong></article>
    </section>
    <section class="panel">
      <div class="panel-title">
        <h2>랭킹</h2>
        <p>점수는 매수 권유가 아니라 후보 압축용입니다.</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>종목</th><th>점수</th><th>등락률</th><th>거래대금</th><th>상대강도</th><th>거래</th><th>ETF</th><th>성장</th><th>메모</th>
            </tr>
          </thead>
          <tbody>{rows or '<tr><td colspan="10">아직 데이터가 없습니다. 지금 업데이트를 눌러 주세요.</td></tr>'}</tbody>
        </table>
      </div>
    </section>
    <section class="panel">
      <div class="panel-title"><h2>업데이트 로그</h2></div>
      <div class="events">{event_rows or '<p>업데이트 이력이 없습니다.</p>'}</div>
    </section>
  </main>
</body>
</html>"""


def render_score_row(row: dict[str, str], rank: int) -> str:
    trading_value = int(float(row.get("trading_value") or 0))
    trading_label = f"{trading_value / 100_000_000:,.0f}억"
    ticker = html.escape(row.get("ticker", ""))
    name = html.escape(row.get("name", ""))
    thesis = html.escape(row.get("thesis", ""))
    return f"""<tr>
  <td>{rank}</td>
  <td><strong>{name}</strong><small>{ticker}</small></td>
  <td><b>{html.escape(row.get("final_score", ""))}</b></td>
  <td>{html.escape(row.get("change_rate", ""))}%</td>
  <td>{trading_label}</td>
  <td>{html.escape(row.get("relative_strength_score", ""))}</td>
  <td>{html.escape(row.get("trading_value_score", ""))}</td>
  <td>{html.escape(row.get("etf_exposure_score", ""))}</td>
  <td>{html.escape(row.get("growth_score", ""))}</td>
  <td>{thesis}</td>
</tr>"""


def render_event(row: dict[str, str]) -> str:
    status = html.escape(row.get("status", ""))
    message = html.escape(row.get("message", ""))
    updated_at = html.escape(row.get("updated_at", ""))
    count = html.escape(row.get("count", ""))
    return f"<p><strong>{updated_at}</strong> <span>{status}</span> {message} ({count}개)</p>"


CSS = """
:root { color-scheme: light; --ink:#17202a; --muted:#667085; --line:#d9e1ea; --bg:#f6f8fb; --panel:#ffffff; --accent:#0f766e; --warn:#b45309; }
* { box-sizing:border-box; }
body { margin:0; font-family:Segoe UI, Apple SD Gothic Neo, Malgun Gothic, sans-serif; color:var(--ink); background:var(--bg); }
.topbar { display:flex; justify-content:space-between; gap:16px; align-items:center; padding:22px clamp(16px,4vw,44px); background:#ffffff; border-bottom:1px solid var(--line); position:sticky; top:0; z-index:2; }
h1 { margin:0; font-size:24px; letter-spacing:0; }
h2 { margin:0; font-size:18px; }
p { margin:6px 0 0; color:var(--muted); }
button { border:0; border-radius:8px; background:var(--accent); color:#fff; font-weight:700; padding:12px 15px; cursor:pointer; white-space:nowrap; }
main { width:min(1180px, 100%); margin:0 auto; padding:18px clamp(12px,3vw,24px) 40px; }
.metrics { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:16px; }
.metrics article, .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; }
.metrics article { padding:16px; }
.metrics span { display:block; color:var(--muted); font-size:13px; }
.metrics strong { display:block; margin-top:8px; font-size:18px; }
.panel { margin-top:16px; overflow:hidden; }
.panel-title { display:flex; justify-content:space-between; gap:16px; align-items:end; padding:16px; border-bottom:1px solid var(--line); }
.table-wrap { overflow-x:auto; }
table { border-collapse:collapse; width:100%; min-width:940px; }
th, td { padding:12px 10px; border-bottom:1px solid #eef2f6; text-align:left; font-size:14px; vertical-align:top; }
th { color:var(--muted); font-size:12px; background:#fbfcfe; position:sticky; top:0; }
td strong { display:block; }
td small { display:block; color:var(--muted); margin-top:2px; }
td b { color:var(--accent); font-size:16px; }
.events { padding:12px 16px 16px; }
.events p { color:var(--ink); padding:8px 0; border-bottom:1px solid #eef2f6; }
.events span { color:var(--warn); font-weight:700; }
@media (max-width: 720px) {
  .topbar { align-items:flex-start; }
  .topbar p { font-size:13px; }
  h1 { font-size:20px; }
  .metrics { grid-template-columns:1fr; }
  .panel-title { display:block; }
  button { padding:10px 12px; }
}
"""


def main() -> None:
    global CONFIG_PATH
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--update-on-start", action="store_true")
    args = parser.parse_args()
    CONFIG_PATH = args.config
    config = load_config(CONFIG_PATH)
    if args.update_on_start:
        run_update(CONFIG_PATH)
    scheduler = DailyScheduler(CONFIG_PATH)
    scheduler.start()
    DashboardHandler.scheduler = scheduler
    server = ThreadingHTTPServer((config.host, config.port), DashboardHandler)
    print(f"KRX dashboard: http://127.0.0.1:{config.port}")
    print(f"Mobile/LAN URL: http://<this-pc-ip>:{config.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
