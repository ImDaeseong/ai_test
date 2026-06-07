# Project Start: Band Performance Reference Profiles

## Purpose

실제 밴드 공연에서 관찰 가능한 무대 배치, 조명, 카메라, 퍼포먼스, 관객 연출을 일반 속성으로 변환해 `ai-webtoon` 출력의 반복성을 낮춘다.

## Scope And Safety

- 공개된 공식 공연·앨범·투어 자료만 출처로 사용한다.
- 실제 밴드명은 조사 출처에만 기록한다.
- 이미지 프롬프트에는 실존 아티스트명, 얼굴, 로고, 정확한 의상, 고유 소품, 시그니처 무대 복제를 넣지 않는다.
- 기존 오리지널 스켈레톤 밴드 정체성은 유지한다.
- 곡 제목별 분기나 하드코딩은 금지한다.

## Architecture

- `configs/band_performance_profiles.json`: 출처와 변환된 공연 프로필
- `select_performance_profile()`: 장르, BPM, 분위기, 감정 기반 프로필 선택
- `select_profile_variant()`: 곡 제목과 패널 번호의 SHA-256 기반 결정론적 세부 변형
- `build_panel_prompt()`: 기존 웹툰 스타일에 공연 연출 속성 결합

## Acceptance Criteria

1. Mood/Emotion이 비어 있어도 프로필 선택이 실패하지 않는다.
2. Hardcore, electronic, post-punk, funk/new-wave, acoustic 입력이 서로 다른 프로필로 분류된다.
3. 같은 곡과 패널은 항상 같은 변형을 얻고, 여러 패널에서는 카메라·조명이 둘 이상으로 변화한다.
4. 생성 프롬프트에는 조사 대상 실존 밴드명이 포함되지 않는다.
5. 기존 스타일 선택 테스트와 폴더 검증이 모두 통과한다.

## Verification

```powershell
python -m pytest tests_unit.py -q
python main.py create --input input\UPGRADE.txt --output-dir output --force
python main.py validate --folder output\UPGRADE
```

## Human Review Hold

- 실제 밴드와 지나치게 유사한 의상·무대·인물 인상이 보이면 공개 전에 수정한다.
- Q3 검수에서 최소 3곡의 패널을 나란히 비교해 무대·카메라 반복이 체감상 줄었는지 사람이 확인한다.

