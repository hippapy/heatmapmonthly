"""
KRX 데이터로 19개 세부업종 월별 수익률을 계산해 data/sector_monthly_returns.json을 생성한다.

전략 (PRD 4.4 3-트랙):
  Track A - KRX/KOSPI/KOSDAQ/테마 공식 지수의 월말 종가로 직접 계산
  Track B - 공식 지수가 없는 업종은 대표종목 바스켓의 시가총액가중 월간 수익률로 근사

** 실행 요건 **
이 스크립트는 data.krx.co.kr에 대한 아웃바운드 네트워크 접근이 필요하다 (pykrx가
KRX 정보데이터시스템을 내부적으로 호출함). 샌드박스/사내망 등 KRX 접근이 막힌 환경에서는
바로 실행되지 않으니, 실제 인터넷 접근이 가능한 환경(로컬 PC, 사내 배치 서버 등)에서
`pip install pykrx pandas` 후 실행할 것.

사용법:
  python scripts/fetch_sector_data.py --start 2024-01-01 --end 2026-06-30 \
      --out data/sector_monthly_returns.json
"""
import argparse
import json
import sys
from datetime import datetime

from sector_index_mapping import SECTORS, TRACK_A_KEYWORDS, TRACK_B_BASKETS


def month_end_dates(start: str, end: str):
    """start~end 사이 각 월의 마지막 영업일 이전 달력월 말일 리스트 (YYYYMMDD)."""
    import pandas as pd
    return [d.strftime("%Y%m%d") for d in pd.date_range(start, end, freq="ME")]


def month_label(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}"


def find_track_a_index(stock, keywords):
    """KRX/KOSPI/KOSDAQ/테마 지수 목록에서 키워드에 매칭되는 티커들을 반환."""
    matched = []
    for market in ("KRX", "KOSPI", "KOSDAQ", "테마"):
        try:
            tickers = stock.get_index_ticker_list(market=market)
        except Exception as e:
            print(f"  [warn] get_index_ticker_list({market}) 실패: {e}", file=sys.stderr)
            continue
        for t in tickers:
            name = stock.get_index_ticker_name(t)
            if any(kw in name for kw in keywords):
                matched.append((market, t, name))
    return matched


def track_a_monthly_returns(stock, dates, keywords):
    matches = find_track_a_index(stock, keywords)
    if not matches:
        return None
    market, ticker, name = matches[0]
    print(f"  Track A 매칭: {name} ({market} {ticker})")
    closes = {}
    for d in dates:
        try:
            df = stock.get_index_ohlcv_by_date(d, d, ticker)
            if not df.empty:
                closes[d] = float(df.iloc[-1]["종가"])
        except Exception as e:
            print(f"  [warn] {d} 지수 조회 실패: {e}", file=sys.stderr)
    return closes_to_returns(closes, dates)


def track_b_monthly_returns(stock, dates, tickers):
    """바스켓 종목의 시가총액가중 지수를 월말 기준으로 합성 후 수익률 계산."""
    synthetic_index = {}
    for d in dates:
        total_cap = 0.0
        for t in tickers:
            try:
                df = stock.get_market_cap_by_date(d, d, t)
                if not df.empty:
                    total_cap += float(df.iloc[-1]["시가총액"])
            except Exception as e:
                print(f"  [warn] {t} {d} 시총 조회 실패: {e}", file=sys.stderr)
        if total_cap > 0:
            synthetic_index[d] = total_cap
    return closes_to_returns(synthetic_index, dates)


def closes_to_returns(level_by_date, ordered_dates):
    returns = {}
    prev = None
    for d in ordered_dates:
        label = month_label(d)
        cur = level_by_date.get(d)
        if cur is None or prev is None:
            returns[label] = None
        else:
            returns[label] = round((cur / prev - 1) * 100, 2)
        if cur is not None:
            prev = cur
    return returns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--out", default="data/sector_monthly_returns.json")
    args = ap.parse_args()

    try:
        from pykrx import stock
    except ImportError:
        print("pykrx가 설치되어 있지 않습니다: pip install pykrx pandas", file=sys.stderr)
        sys.exit(1)

    dates = month_end_dates(args.start, args.end)
    months = [month_label(d) for d in dates]

    returns_by_sector = {}
    for s in SECTORS:
        sid = s["id"]
        print(f"[{sid}] {s['name_kr']} 수집 중...")
        if sid in TRACK_A_KEYWORDS:
            r = track_a_monthly_returns(stock, dates, TRACK_A_KEYWORDS[sid])
            if r is None:
                print(f"  Track A 실패, Track B로 폴백 필요 (바스켓 미정의시 전체 None)")
                r = {m: None for m in months}
        else:
            r = track_b_monthly_returns(stock, dates, TRACK_B_BASKETS[sid])
        returns_by_sector[sid] = r

    data = {
        "meta": {
            "title": "국내 주식시장 세부업종 월별 수익률",
            "period": {"start": months[0], "end": months[-1]},
            "unit": "percent",
            "return_definition": "월말 종가 기준 전월 대비 수익률",
            "source": "KRX 공식 지수(Track A) + 대표종목 시총가중 자체지수(Track B), pykrx 경유",
            "as_of": datetime.now().strftime("%Y-%m-%d"),
            "is_sample": False,
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
