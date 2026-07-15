# 삼성전자(005930) 월별 거래량 차트

삼성전자의 **올해 월별 거래량**(및 거래대금)을 KRX 공식 데이터로 집계해 막대 차트로
보여주는 단일 파일 대시보드.

| 경로 | 설명 |
|---|---|
| `samsung_volume.html` | 단일 파일 대시보드 (외부 의존성 없음). 거래량/거래대금 토글, 호버 툴팁, 표 뷰, 라이트/다크 대응 |
| `data/samsung_2026_monthly_volume.json` | 대시보드가 읽는 데이터. **현재 미연동(값 null)** — 아래 스크립트로 채운다 |
| `scripts/fetch_samsung_volume.py` | KRX 데이터를 수집해 위 JSON을 생성하는 스크립트 |

## ⚠ 현재 상태: 실데이터 미연동

이 리포지토리를 다룬 Claude Code on the web 세션은 이그레스 정책상 KRX 계열
아웃바운드가 모두 차단돼 있어(아래 참고) **실데이터를 채우지 못했다.** 그래서
`data/samsung_2026_monthly_volume.json`의 `volume`/`value`는 전부 `null`이고,
대시보드는 상단에 "실데이터 미연동" 배너와 빈 차트 골격을 표시한다.

차단이 확인된 호스트(모두 프록시에서 `403 CONNECT`):
`data.krx.co.kr`, `k-skill-proxy.nomadamas.org`(KRX Open API 프록시),
`openapi.tossinvest.com`(토스 Open API). Massive(Polygon)는 한국 종목 미지원.

## 실데이터로 채우는 방법 (네트워크가 열린 로컬/사내 환경에서)

두 소스 모두 **API 키가 필요 없다.** 하나만 성공하면 된다.

```bash
# A. pykrx (권장) — 일별 OHLCV를 한 번에 받아 월별 합산
pip install pykrx pandas
python scripts/fetch_samsung_volume.py                    # 올해 1월~이번 달
#   python scripts/fetch_samsung_volume.py --year 2026     # 연도 지정
#   python scripts/fetch_samsung_volume.py --start 2026-01-01 --end 2026-07-31

# B. KRX Open API 프록시 — pandas/pykrx 없이 거래일별로 조회해 합산
pip install requests
python scripts/fetch_samsung_volume.py --source krx-proxy
```

실행되면 JSON의 `meta.is_sample`이 `false`가 되고 `volume`/`value`가 채워진다.
`samsung_volume.html`을 **로컬 웹서버(http) 또는 GitHub Pages로 열고** 새로고침하면
실데이터로 렌더링된다. HTML은 수정할 필요 없다.

> `file://` 로 직접 열면 브라우저가 로컬 `fetch`를 차단하므로 차트가 비어 보인다.
> `python -m http.server` 로 띄운 뒤 `http://localhost:8000/samsung_volume.html` 로 열거나,
> GitHub Pages(https://hippapy.github.io/heatmapmonthly/samsung_volume.html)로 확인할 것.

## '월별 거래량' 정의

각 월의 값 = **해당 월 모든 거래일의 일별 거래량(주)을 단순 합산**한 값.
거래대금(원)도 같은 방식으로 월 합계를 저장하며, 대시보드에서 토글로 전환한다.

## 데이터 스키마

```json
{
  "meta": {
    "ticker": "005930", "name": "삼성전자", "market": "KOSPI", "year": 2026,
    "period": {"start": "2026-01", "end": "2026-07"},
    "unit_volume": "shares", "unit_value": "KRW",
    "source": "...", "as_of": "YYYY-MM-DD", "is_sample": false
  },
  "months": ["2026-01", "..."],
  "volume": {"2026-01": 382000000, "...": null},
  "value":  {"2026-01": 32400000000000, "...": null}
}
```

출처 표기: **KRX 공식 데이터 기준 · 투자 조언 아님.**
