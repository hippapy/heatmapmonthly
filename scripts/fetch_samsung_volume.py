"""
삼성전자(005930) 월별 거래량/거래대금을 KRX 공식 데이터로 수집해
data/samsung_2026_monthly_volume.json 을 생성한다.

'월별 거래량' 정의: 해당 월 각 거래일의 일별 거래량(주)을 단순 합산한 값.
(거래대금도 동일하게 월 합계로 함께 저장한다.)

## 두 가지 수집 소스 (둘 다 API 키 불필요)

  --source pykrx      (기본) pykrx 로 일별 OHLCV 를 한 번에 받아 월별 합산.
                      내부적으로 KRX 정보데이터시스템(data.krx.co.kr)을 조회하므로
                      아웃바운드 네트워크가 열린 환경에서 실행해야 한다.
                        pip install pykrx pandas

  --source krx-proxy  KRX 공식 데이터를 키 없이 제공하는 프록시
                      (k-skill-proxy.nomadamas.org)의 일별 시세를 거래일마다 조회해
                      월별 합산. pandas/pykrx 없이 requests 만 있으면 된다.
                        pip install requests

** 실행 요건 (중요) **
  Claude Code on the web 등 이그레스 정책이 걸린 샌드박스에서는 data.krx.co.kr 과
  k-skill-proxy.nomadamas.org 모두 CONNECT 가 403 으로 차단된다. 반드시 네트워크가
  열린 로컬/사내 환경에서 실행할 것. (리포지토리 README의 로컬 워크플로 참고)

## 사용법

    python scripts/fetch_samsung_volume.py                       # 올해 1월~이번 달
    python scripts/fetch_samsung_volume.py --year 2026
    python scripts/fetch_samsung_volume.py --source krx-proxy
    python scripts/fetch_samsung_volume.py --start 2026-01-01 --end 2026-07-31

생성 후 samsung_volume.html 을 새로고침하면 실데이터로 렌더링된다(HTML 수정 불필요).
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta

TICKER = "005930"
NAME = "삼성전자"
MARKET = "KOSPI"
OUT_DEFAULT = "data/samsung_2026_monthly_volume.json"
KRX_PROXY_BASE = "https://k-skill-proxy.nomadamas.org"


def month_labels(start: date, end: date):
    labels, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        labels.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return labels


# ---------------------------------------------------------------- pykrx 소스
def collect_pykrx(start: date, end: date):
    try:
        import pandas as pd
        from pykrx import stock
    except ImportError:
        sys.exit("pykrx/pandas 가 필요합니다: pip install pykrx pandas")

    df = stock.get_market_ohlcv(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), TICKER
    )
    if df is None or df.empty:
        sys.exit("pykrx 가 데이터를 반환하지 않았습니다(휴장/네트워크 차단 확인).")

    df.index = pd.to_datetime(df.index)
    monthly = df.resample("MS").agg({"거래량": "sum", "거래대금": "sum"})
    volume, value = {}, {}
    for ts, row in monthly.iterrows():
        label = f"{ts.year:04d}-{ts.month:02d}"
        volume[label] = int(row["거래량"])
        value[label] = int(row["거래대금"])
    return volume, value, "KRX 정보데이터시스템 (pykrx get_market_ohlcv, 일별 거래량 월합계)"


# ------------------------------------------------------------ krx-proxy 소스
def collect_krx_proxy(start: date, end: date):
    try:
        import requests
    except ImportError:
        sys.exit("requests 가 필요합니다: pip install requests")

    volume, value = {}, {}
    day = start
    session = requests.Session()
    while day <= end:
        if day.weekday() < 5:  # 월~금만 시도, 휴장일은 not_found 로 건너뜀
            try:
                r = session.get(
                    f"{KRX_PROXY_BASE}/v1/korean-stock/trade-info",
                    params={"market": MARKET, "code": TICKER,
                            "bas_dd": day.strftime("%Y%m%d")},
                    timeout=15,
                )
            except requests.RequestException as e:
                sys.exit(f"프록시 연결 실패({day}): {e}\n"
                         "이그레스 정책 차단 환경일 수 있습니다. 로컬에서 실행하세요.")
            if r.status_code == 200:
                item = r.json().get("item") or {}
                vol = item.get("trading_volume")
                val = item.get("trading_value")
                if vol is not None:
                    label = f"{day.year:04d}-{day.month:02d}"
                    volume[label] = volume.get(label, 0) + int(vol)
                    value[label] = value.get(label, 0) + int(val or 0)
            elif r.status_code not in (404,):  # 404=해당일 데이터 없음(휴장)
                sys.exit(f"프록시 오류 {r.status_code} ({day}): {r.text[:200]}")
        day += timedelta(days=1)

    if not volume:
        sys.exit("수집된 거래일이 없습니다(기간/휴장/차단 확인).")
    return volume, value, "KRX Open API (k-skill-proxy trade-info, 일별 거래량 월합계)"


def main():
    ap = argparse.ArgumentParser(description="삼성전자 월별 거래량 수집기")
    ap.add_argument("--source", choices=["pykrx", "krx-proxy"], default="pykrx")
    ap.add_argument("--year", type=int, default=date.today().year)
    ap.add_argument("--start", help="YYYY-MM-DD (지정 시 --year 무시)")
    ap.add_argument("--end", help="YYYY-MM-DD")
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else date.today()
    else:
        start = date(args.year, 1, 1)
        end = date(args.year, 12, 31)
        if args.year == date.today().year:
            end = date.today()

    collect = collect_pykrx if args.source == "pykrx" else collect_krx_proxy
    print(f"[{args.source}] {NAME}({TICKER}) {start} ~ {end} 수집 중...")
    volume, value, source = collect(start, end)

    months = month_labels(start, end)
    data = {
        "meta": {
            "title": f"{NAME}({TICKER}) 월별 거래량",
            "ticker": TICKER,
            "name": NAME,
            "market": MARKET,
            "year": start.year,
            "period": {"start": months[0], "end": months[-1]},
            "unit_volume": "shares",
            "unit_value": "KRW",
            "definition": "월별 = 해당 월 각 거래일의 일별 거래량/거래대금 단순 합계",
            "source": source,
            "as_of": date.today().strftime("%Y-%m-%d"),
            "is_sample": False,
        },
        "months": months,
        "volume": {m: volume.get(m) for m in months},
        "value": {m: value.get(m) for m in months},
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    filled = sum(1 for m in months if data["volume"][m] is not None)
    print(f"완료: {args.out}  ({filled}/{len(months)}개월 채움, 출처: {source})")


if __name__ == "__main__":
    main()
