"""
19개 세부업종 <-> KRX 데이터 소스 매핑 설정.

PRD 4.4의 3-트랙 전략 중 Track A(공식 지수)/Track B(자체 시총가중 지수) 배정표.
공식 GICS Sub-Industry 1:1 매핑이 아닌 실무 커버리지 기준 근사치이므로,
운영 전 KRX "업종분류현황" 다운로드로 최신 종목 구성을 검증/갱신할 것.

SECTORS 순서/ id는 sector_heatmap.html의 SECTORS와 반드시 동일하게 유지한다
(달라지면 필터/정렬 로직이 깨짐).
"""

SECTORS = [
    {"id": "semis", "name_kr": "반도체", "hue": 0},
    {"id": "semi_equip", "name_kr": "반도체장비/소재", "hue": 19},
    {"id": "battery", "name_kr": "2차전지/배터리", "hue": 38},
    {"id": "power_equip", "name_kr": "전력기기", "hue": 57},
    {"id": "cosmetics", "name_kr": "화장품", "hue": 76},
    {"id": "defense", "name_kr": "방위산업", "hue": 95},
    {"id": "shipbuilding", "name_kr": "조선", "hue": 114},
    {"id": "auto_parts", "name_kr": "자동차부품", "hue": 133},
    {"id": "steel", "name_kr": "철강", "hue": 152},
    {"id": "chemicals", "name_kr": "화학소재", "hue": 171},
    {"id": "banks", "name_kr": "은행", "hue": 189},
    {"id": "securities", "name_kr": "증권", "hue": 208},
    {"id": "pharma", "name_kr": "제약", "hue": 227},
    {"id": "biotech", "name_kr": "바이오텍", "hue": 246},
    {"id": "internet", "name_kr": "인터넷/포털", "hue": 265},
    {"id": "gaming", "name_kr": "게임", "hue": 284},
    {"id": "telecom", "name_kr": "통신서비스", "hue": 303},
    {"id": "power_utility", "name_kr": "전력유틸리티", "hue": 322},
    {"id": "construction_machinery", "name_kr": "건설/기계", "hue": 341},
]

# Track A: KRX/KOSPI/KOSDAQ/테마 공식 지수 이름에서 찾을 키워드.
# pykrx.stock.get_index_ticker_list(date, market)로 얻은 (ticker, name) 목록을
# 아래 키워드로 substring 매칭한다. 여러 개 매칭되면 첫 번째(가장 대표적인 것)를 사용.
# 값이 list인 경우 여러 지수를 시총가중 평균해 근사치로 합성한다(운영 전 검증 필요).
TRACK_A_KEYWORDS = {
    "semis": ["반도체"],
    "battery": ["2차전지"],
    "banks": ["은행"],
    "securities": ["증권"],
    "steel": ["철강"],
    "chemicals": ["에너지화학"],  # 근사치: 화학소재보다 넓은 범위(에너지 포함)
    "auto_parts": ["자동차"],  # 근사치: 완성차+부품 통합
    "construction_machinery": ["건설", "기계장비"],  # 두 지수 평균으로 근사
}

# Track B: Track A에 대응 지수가 없거나 근사 오차가 커서 개별종목 시총가중
# 자체지수로 계산하는 세부업종의 대표종목 바스켓 (KRX 6자리 코드).
# ** 주의: 아래 티커는 초기 프로토타이핑용 curated 리스트이며 실거래 검증 전임.
#    운영 투입 전 KRX "업종분류현황" 공식 다운로드로 재검증할 것. **
TRACK_B_BASKETS = {
    "semi_equip": ["042700", "240810", "036930", "095340", "131290"],
    "power_equip": ["267260", "010120", "034020", "052690", "001440"],
    "cosmetics": ["090430", "051900", "161890", "192820", "237880"],
    "defense": ["012450", "047810", "079550", "064350"],
    "shipbuilding": ["009540", "010140", "042660", "097230"],
    "pharma": ["000100", "185750", "128940", "069620", "006280"],
    "biotech": ["207940", "068270", "196170", "141080", "298380"],
    "internet": ["035420", "035720"],
    "gaming": ["036570", "251270", "293490", "112040", "263750"],
    "telecom": ["017670", "030200", "032640"],
    "power_utility": ["015760", "018670", "016710"],
}

# 산출 방식 검증: 19개 섹터가 Track A 아니면 Track B 둘 중 하나에 반드시 있어야 함
_covered = set(TRACK_A_KEYWORDS) | set(TRACK_B_BASKETS)
_all_ids = {s["id"] for s in SECTORS}
assert _covered == _all_ids, f"매핑 누락: {_all_ids - _covered}"

# Track D (보조, 2026-07-03 웹서치로 확인): KRX 지수 대신 섹터 ETF 가격을 프록시로 쓰는
# 방법. data.krx.co.kr 직접 접근이 막혔을 때의 대안으로 검토됨(사용자 요청).
# 이 세션에서는 WebSearch로 티커 존재까지는 확인했지만, 실제 가격 데이터가 있는 페이지
# (Naver/Yahoo Finance, 삼성자산운용, Investing.com, WiseReport, Stooq)는 전부 WebFetch가
# 403/차단되어 가격 시계열은 가져오지 못했다. 아래 티커는 검색 스니펫에 코드가 명시적으로
# 노출된 것만 담았고("종목코드: ..." 형태로 직접 확인), ISIN(KR7xxxxxxxxx)에서 역산한 것은
# 별도 표기했다. Agent Store capital-markets(finance_securities_quote)가 복구되거나
# pykrx로 KRX 접근이 가능한 환경에서 이 티커로 바로 조회해 가격 시계열을 채울 것.
TRACK_D_ETF_PROXY = {
    "semis": {
        "tickers": ["091160", "091230", "396500"],
        "names": ["KODEX 반도체", "TIGER 반도체", "TIGER Fn반도체TOP10"],
        "confidence": "confirmed",  # 검색 결과에 종목코드 명시
    },
    "battery": {
        "tickers": ["305720"],
        "names": ["KODEX 2차전지산업"],
        "confidence": "confirmed",
    },
    "defense": {
        "tickers": ["490480"],
        "names": ["SOL K방산"],
        "confidence": "confirmed",
    },
    "banks": {
        "tickers": ["091220", "466940"],
        "names": ["TIGER 은행", "TIGER 은행고배당TOP10"],
        "confidence": "isin_derived",  # ISIN(KR7091220004 등)에서 역산, 티커 직접 확인 필요
    },
    # 나머지 15개 세부업종은 이번 웹서치에서 신뢰할 만한 티커를 확보하지 못함.
    # (화장품/조선/자동차부품/철강/화학소재/증권/제약/바이오텍/인터넷/게임/통신서비스/
    #  전력유틸리티/건설/기계/반도체장비-소재/전력기기 — 상품이 존재할 가능성은 높으나
    #  이 세션에서 코드 확인 실패)
}

# Track A/D 티커가 없는 나머지 세부업종용 — 토스증권 앱에서 검색해볼 키워드 제안.
# 정확한 상품/티커를 보장하지 않음 (이 세션에서 검증 못함). 유사 상품이 여러 개면
# 순자산(AUM)이 가장 큰 것을 대표로 고르는 것을 권장.
TOSS_SEARCH_HINTS = {
    "semi_equip": "반도체장비 OR 반도체소재",
    "power_equip": "전력기기 OR 전력설비",
    "cosmetics": "화장품",
    "shipbuilding": "조선",
    "auto_parts": "자동차 (부품사 포함 여부 확인)",
    "steel": "철강",
    "chemicals": "화학 OR 에너지화학",
    "securities": "증권",
    "pharma": "제약",
    "biotech": "바이오 OR 헬스케어",
    "internet": "인터넷 OR 미디어콘텐츠",
    "gaming": "게임",
    "telecom": "통신서비스 OR 미디어통신",
    "power_utility": "전력 OR 유틸리티",
    "construction_machinery": "건설 OR 기계장비",
}
