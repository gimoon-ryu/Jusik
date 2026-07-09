# Jusik

KRX 데이터 기반 한국 주식 스코어링 대시보드입니다.

## Dashboard

GitHub Pages 배포 후 아래 주소에서 접속할 수 있습니다.

```text
https://gimoon-ryu.github.io/Jusik/
```

## Scoring Logic

최종 점수는 후보 종목 압축용입니다. 매수 권유나 자동매매 신호가 아닙니다.

```text
최종점수 =
  30% 상대강도
+ 20% 거래대금 유지
+ 20% ETF 노출
+ 20% 성장 근거
- 10% 리스크
```

## Daily Updates

GitHub Actions가 한국 시간 기준 평일 하루 3회 실행됩니다.

- 09:20
- 12:30
- 16:00

각 실행은 KRX 데이터 다운로드를 시도하고, 실패하면 `data/krx_universe.csv`의 수동 관심종목을 기준으로 대시보드가 계속 열리도록 fallback합니다.

## Manual Inputs

관심종목과 정성 점수는 아래 파일에서 관리합니다.

```text
data/krx_universe.csv
```

주요 컬럼:

- `growth_score`: 실적, 수출, 마진, 수주 등 성장 근거 점수
- `etf_exposure_score`: ETF 편입/수급 노출 점수
- `risk_note`: 리스크 메모. 값이 있으면 감점
- `thesis`: 종목을 추적하는 이유

## Local Run

```powershell
python -m stocks.krx_dashboard --update-on-start
```

Open:

```text
http://127.0.0.1:8765
```
