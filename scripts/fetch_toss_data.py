"""
토스증권 Open API(Market Data)로 19개 세부업종 ETF의 월말 종가를 받아
data/sector_monthly_returns.json을 생성한다.

** 실행 요건 **
- 이 API는 발급받은 클라이언트(API Key/Secret Key)에 IP 화이트리스트가 걸려 있다.
  발급 시 등록한 허용 IP에서만 실행할 것 (샌드박스/클라우드 환경에서 실행하면 막힘).
- 인증 정보는 절대 코드에 하드코딩하지 말고 환경변수로 전달한다:
    export TOSS_CLIENT_ID=발급받은_API_Key
    export TOSS_CLIENT_SECRET=발급받은_Secret_Key
  (토스 개발자센터의 "API Key"가 OAuth의 client_id, "Secret Key"가 client_secret에 대응)

API 스펙 요약 (공식 OpenAPI 문서 기준):
  - 인증: POST /oauth2/token (client_credentials grant, x-www-form-urlencoded)
          -> access_token, 이후 모든 요청에 Authorization: Bearer {token}
  - 시세: GET /api/v1/candles?symbol=X&interval=1d&count=200&adjusted=true
          월봉은 지원하지 않음(1m/1d만 가능) -> 일봉을 받아 각 월의 마지막 거래일
          종가를 직접 추출해서 월간 수익률을 계산한다.
          count는 요청당 최대 200개, before(ISO datetime, exclusive)로 과거 방향
          페이지네이션. 응답의 nextBefore를 다음 요청의 before로 그대로 전달.
  - 이 엔드포인트는 계좌 연동이 필요 없다 (X-Tossinvest-Account 헤더 불필요).

사용법:
  python scripts/fetch_toss_data.py --since 2023-12-01 --out data/sector_monthly_returns.json
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, date

import requests

from sector_index_mapping import SECTORS, SECTOR_TOSS_SYMBOL

BASE = "https://openapi.tossinvest.com"


def get_access_token():
    client_id = os.environ.get("TOSS_CLIENT_ID")
    client_secret = os.environ.get("TOSS_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("TOSS_CLIENT_ID / TOSS_CLIENT_SECRET 환경변수가 필요합니다.", file=sys.stderr)
        sys.exit(1)

    resp = requests.post(
        f"{BASE}/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def request_with_retry(method, url, headers, params=None, max_retries=3):
    for attempt in range(max_retries):
        resp = requests.request(method, url, headers=headers, params=params)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", "2"))
            print(f"  [rate-limit] {wait}초 대기 후 재시도", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"재시도 초과: {url}")


def fetch_daily_history(token, symbol, since: date):
    """symbol의 일봉을 since 이전까지 과거 방향으로 페이지네이션하며 전부 수집."""
    headers = {"Authorization": f"Bearer {token}"}
    all_candles = []
    before = None
    while True:
        params = {"symbol": symbol, "interval": "1d", "count": 200, "adjusted": "true"}
        if before:
            params["before"] = before
        data = request_with_retry("GET", f"{BASE}/api/v1/candles", headers, params)
        page = data["result"]["candles"]
        if not page:
            break
        all_candles.extend(page)
        oldest_ts = datetime.fromisoformat(page[-1]["timestamp"])
        if oldest_ts.date() <= since:
            break
        next_before = data["result"]["nextBefore"]
        if not next_before:
            break
        before = next_before
        time.sleep(0.2)  # MARKET_DATA_CHART rate limit 그룹 배려
    return all_candles


def month_end_closes(candles, months):
    """월 라벨(YYYY-MM) -> 해당 월 마지막 거래일 종가. candles는 최신순으로 가정."""
    by_month = {}
    for c in candles:
        ts = datetime.fromisoformat(c["timestamp"])
        label = f"{ts.year:04d}-{ts.month:02d}"
        # candles가 최신순으로 들어오므로 각 월에서 처음 만나는 것이 그 달의 마지막 거래일
        if label not in by_month:
            by_month[label] = float(c["closePrice"])
    return {m: by_month.get(m) for m in months}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2023-12-01", help="이 날짜까지의 일봉을 수집 (기준월 직전 월말 포함)")
    ap.add_argument("--out", default="data/sector_monthly_returns.json")
    args = ap.parse_args()
    since = datetime.strptime(args.since, "%Y-%m-%d").date()

    months = []
    for y in (2024, 2025, 2026):
        for m in range(1, 13):
            if y == 2026 and m > 6:
                continue
            months.append(f"{y}-{m:02d}")
    baseline_month = "2023-12"

    token = get_access_token()

    returns_by_sector = {}
    missing_symbol = []
    for s in SECTORS:
        sid = s["id"]
        symbol = SECTOR_TOSS_SYMBOL.get(sid)
        if not symbol:
            missing_symbol.append(sid)
            returns_by_sector[sid] = {m: None for m in months}
            continue

        print(f"[{sid}] {s['name_kr']} ({symbol}) 수집 중...")
        candles = fetch_daily_history(token, symbol, since)
        closes = month_end_closes(candles, [baseline_month] + months)

        series = {}
        prev = closes.get(baseline_month)
        for m in months:
            cur = closes.get(m)
            if cur is not None and prev is not None:
                series[m] = round((cur / prev - 1) * 100, 2)
            else:
                series[m] = None
            if cur is not None:
                prev = cur
        returns_by_sector[sid] = series

    if missing_symbol:
        print(f"심볼 미설정으로 건너뜀: {', '.join(missing_symbol)}", file=sys.stderr)
        print("  -> scripts/sector_index_mapping.py의 SECTOR_TOSS_SYMBOL을 채워 넣으세요.", file=sys.stderr)

    data = {
        "meta": {
            "title": "국내 주식시장 세부업종 월별 수익률",
            "period": {"start": months[0], "end": months[-1]},
            "unit": "percent",
            "return_definition": "월말 종가 기준 전월 대비 수익률 (섹터 ETF 프록시, 토스증권 Open API 일봉 기반)",
            "source": "토스증권 Open API (Market Data /api/v1/candles)",
            "as_of": datetime.now().strftime("%Y-%m-%d"),
            "is_sample": len(missing_symbol) > 0,
        },
        "sectors": [
            {
                "id": s["id"],
                "name_kr": s["name_kr"],
                "name_en": s.get("name_en", ""),
                "color": f"hsl({s['hue']} 65% 55%)",
            }
            for s in SECTORS
        ],
        "months": months,
        "returns": returns_by_sector,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"완료: {args.out}")


if __name__ == "__main__":
    main()
