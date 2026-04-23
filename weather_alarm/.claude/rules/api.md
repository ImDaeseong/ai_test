# 기상청 초단기실황 API 명세

## 엔드포인트
```
GET http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst
```

## 요청 파라미터
| 파라미터 | 설명 | 예시 |
|---|---|---|
| serviceKey | 인증키 (URL 디코딩 값) | `abc123...` |
| numOfRows | 한 페이지 결과 수 | `10` |
| pageNo | 페이지 번호 | `1` |
| dataType | 응답 형식 | `JSON` |
| base_date | 발표 일자 | `20260423` |
| base_time | 발표 시각 | `1410` |
| nx | 예보지점 X좌표 | `58` |
| ny | 예보지점 Y좌표 | `125` |

## 가산동 격자 좌표
- nx = 58, ny = 125 (서울특별시 금천구 가산동)

## 10분 지연 호출 로직
기상청 초단기실황 데이터는 매 정시 기준으로 약 10분 후에 제공된다.
- 현재 시각에서 10분을 뺀 뒤, 분 단위를 10의 배수로 내림한 값을 base_time으로 사용한다.
- 예: 현재 14:23 → 14:23 - 10분 = 14:13 → 내림 → 14:10 (base_time = "1410")

```python
from datetime import datetime, timedelta

def get_base_datetime():
    now = datetime.now() - timedelta(minutes=10)
    minutes = (now.minute // 10) * 10
    base = now.replace(minute=minutes, second=0, microsecond=0)
    return base.strftime("%Y%m%d"), base.strftime("%H%M")
```

## 응답 카테고리 (초단기실황)
| 코드 | 항목명 | 단위 |
|---|---|---|
| T1H | 기온 | °C |
| RN1 | 1시간 강수량 | mm |
| UUU | 동서바람성분 | m/s |
| VVV | 남북바람성분 | m/s |
| REH | 습도 | % |
| PTY | 강수형태 | 코드 |
| VEC | 풍향 | deg |
| WSD | 풍속 | m/s |

## 강수형태(PTY) 코드표
| 코드 | 설명 |
|---|---|
| 0 | 없음 |
| 1 | 비 |
| 2 | 비/눈 |
| 3 | 눈 |
| 5 | 빗방울 |
| 6 | 빗방울눈날림 |
| 7 | 눈날림 |
