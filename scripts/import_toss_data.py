"""
scripts/toss_data_template.csv에 사용자가 토스증권 앱/API에서 직접 확인한 값을 채워 넣으면,
이 스크립트가 그 CSV를 읽어 data/sector_monthly_returns.json을 생성한다.

CSV 컬럼:
  sector_id, sector_name, ticker, instrument_name, data_type, baseline_2023-12_price,
  2024-01, 2024-02, ..., 2026-06

data_type:
  - "return": 월간 수익률(%)을 직접 채워 넣는 방식. 2024-01~2026-06 30칸에 숫자(%)를 입력.
              baseline_2023-12_price는 비워둬도 됨.
  - "price" : 월말 종가/기준가(NAV)를 채워 넣는 방식. baseline_2023-12_price(2023년 12월 말 값)를
              반드시 채우고, 2024-01~2026-06에도 각 월말 값을 채운다. 스크립트가 전월 대비
              등락률(%)을 자동 계산한다.

특정 세부업종 데이터를 아직 못 구했으면 그 행은 전부 비워두면 된다 (해당 섹터는 null로 채워짐 -
대시보드에 '—'로 표시되고 히트맵 계산에서는 제외됨).

사용법:
  python scripts/import_toss_data.py --in scripts/toss_data_template.csv \
      --out data/sector_monthly_returns.json
"""
import argparse
import csv
import json
import sys
from datetime import datetime

from sector_index_mapping import SECTORS


def parse_num(s):
    s = (s or "").strip().replace(",", "").replace("%", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"  [warn] 숫자로 해석 안 됨: '{s}' -> null 처리", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="scripts/toss_data_template.csv")
    ap.add_argument("--out", default="data/sector_monthly_returns.json")
    args = ap.parse_args()

    months = []
    for y in (2024, 2025, 2026):
        for m in range(1, 13):
            if y == 2026 and m > 6:
                continue
            months.append(f"{y}-{m:02d}")

    by_id = {s["id"]: s for s in SECTORS}
    returns_by_sector = {sid: {m: None for m in months} for sid in by_id}
    filled_sectors = []

    with open(args.infile, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["sector_id"].strip()
            if sid not in by_id:
                print(f"  [warn] 알 수 없는 sector_id: {sid} (건너뜀)", file=sys.stderr)
                continue

            data_type = (row.get("data_type") or "return").strip().lower()

            if data_type == "price":
                baseline = parse_num(row.get("baseline_2023-12_price"))
                prev = baseline
                any_value = baseline is not None
                for m in months:
                    cur = parse_num(row.get(m))
                    if cur is not None:
                        any_value = True
                    if cur is not None and prev is not None:
                        returns_by_sector[sid][m] = round((cur / prev - 1) * 100, 2)
                    else:
                        returns_by_sector[sid][m] = None
                    if cur is not None:
                        prev = cur
            else:  # "return"
                any_value = False
                for m in months:
                    v = parse_num(row.get(m))
                    returns_by_sector[sid][m] = v
                    if v is not None:
                        any_value = True

            if any_value:
                filled_sectors.append(sid)

    empty_sectors = [sid for sid in by_id if sid not in filled_sectors]
    print(f"채워진 섹터: {len(filled_sectors)}/{len(by_id)}")
    if empty_sectors:
        print(f"  데이터 없음(전부 null 처리됨): {', '.join(empty_sectors)}")

    data = {
        "meta": {
            "title": "국내 주식시장 세부업종 월별 수익률",
            "period": {"start": months[0], "end": months[-1]},
            "unit": "percent",
            "return_definition": "월말 종가/기준가 기준 전월 대비 수익률 (섹터 ETF 프록시, 토스증권 데이터 기반)",
            "source": "토스증권 앱/API에서 사용자가 직접 확인한 섹터 ETF 가격 (scripts/import_toss_data.py로 변환)",
            "as_of": datetime.now().strftime("%Y-%m-%d"),
            "is_sample": len(empty_sectors) > 0,  # 일부라도 비어있으면 완전한 실데이터는 아님
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
