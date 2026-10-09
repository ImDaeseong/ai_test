# AI·API·의존성 정밀 검수

검수일: 2026-10-09

이 문서는 AI라는 이름만으로 모든 프로젝트에 모델 호출을 추가하지 않고, 실제 경계를 구분해 유지보수하는 기준이다.

## 프로젝트별 경계와 검증

| 프로젝트 | 실제 AI/API 경계 | 이번 검증 |
|---|---|---|
| `Analysis_music` | 규칙 기반 음악 분석과 이미지 프롬프트 산출; 생성형 API 호출 없음 | pytest 67개 통과 |
| `imagevideo` | 사람이 준비한 이미지·가사·오디오를 소비; 생성형 API 호출 없음 | Node 테스트 50개, 런타임 npm audit 0, 실제 재렌더 freeze 11.24%; 권리 증빙 부재로 공개 불승인 |
| `Pexels` | Gemini 장면 계획 + Pexels 검색 API | 구조화 JSON, 입력 신뢰 경계, 선택적 재시도 회귀 포함 pytest 27개 통과 |
| `lyrics_tag` | 수동 가사 타이밍 도구; 생성형 API 호출 없음 | pytest 18개 통과 |
| `lyricvideo` | Remotion 렌더러; 생성형 API 호출 없음 | Node 테스트 23개와 TypeScript 검사 통과 |
| `master_tag` | 결정론적 오디오 마스터링; 생성형 API 호출 없음 | pytest 18개 통과 |
| `mp3_daw` | 로컬 오디오 처리와 선택적 Demucs 실행; 원격 생성형 API 호출 없음 | `go test ./...` 통과 |
| `mp4_tag` | 미디어 탐지·다운로드; 생성형 API 호출 없음 | pytest 50개 통과 |
| `weather_alarm` | 기상·메신저 API이며 생성형 AI가 아님 | pytest 56개 통과 |
| `ai_anime_production` | AI가 만든 이미지·프롬프트를 소비하는 Remotion 렌더러 | Node 테스트 30개와 TypeScript 검사 통과 |
| `ai-webtoon` | 프롬프트 생성 + 선택적 OpenAI Images 직접 호출 | Python 테스트 71개 통과; 모델·품질을 명시 설정 |
| `ai-webtoon_capcut` | 이미지·가사·오디오를 검증해 영상/편집 전달 묶음 생성 | 공식 배치 26개 통과 |

## API 기준

- Gemini: `Pexels`는 안정 모델 `gemini-2.5-flash`를 기본값으로 유지한다. 출력은 JSON 스키마로 제한하고, 가사·스크립트는 지시가 아닌 비신뢰 데이터로 감싼다. HTTP 429·5xx와 전송 실패만 재시도한다. 신규 모델은 `GEMINI_MODEL`로 대표 입력을 먼저 검증한 뒤 기준선을 바꾼다.
- OpenAI Images: `ai-webtoon`은 `gpt-image-2`, `1536x1024`, `medium`을 명시한다. `OPENAI_IMAGE_MODEL`과 `OPENAI_IMAGE_QUALITY`로 전환할 수 있지만 유료 요청은 자동 재시도하지 않는다.
- 실제 API 검증은 합성 입력만 사용하고 키·공급자 원문 오류·프롬프트를 로그에 남기지 않는다.

공식 확인 위치: [Gemini 모델](https://ai.google.dev/gemini-api/docs/models), [Gemini 구조화 출력](https://ai.google.dev/gemini-api/docs/generate-content/structured-output), [OpenAI 이미지 생성](https://developers.openai.com/api/docs/guides/image-generation).

## 의존성 결정

- `imagevideo`, `lyricvideo`, `ai_anime_production`은 선언된 호환 범위 안에서 lockfile을 갱신했다. 후자의 두 프로젝트는 `npm audit` 취약점 0이다.
- `imagevideo` 기본 FFmpeg 배포 경로는 Motion Canvas 계보를 개발 의존성으로 격리해 `npm audit --omit=dev` 0건이다. 호환 가능한 xmldom 0.9.12 override 후 개발 도구 전체 감사에는 high 5/moderate 2가 남는다. `audit-baseline.json`은 신규 패키지·권고·심각도 증가와 런타임 취약점 재유입을 차단한다. Motion Canvas가 Vite 6.4.3 이상을 지원하기 전 Vite 8 강제 override는 HOLD다.
- TypeScript 7, Vite 8, Gin 1.12 등 메이저 또는 런타임 기준 변경은 별도 마이그레이션에서 테스트한다. 최신이라는 이유만으로 일괄 적용하지 않는다.
- Python 요구사항의 비정확 핀과 전체 생태계 취약점 검수는 `DEPENDENCY_INVENTORY.md`의 출시 HOLD를 유지한다.

## 출시 전 반복 순서

1. 이 문서의 12개 명령을 `qa_manager` 체크리스트로 실행한다.
2. manifest가 바뀌면 `DEPENDENCY_INVENTORY.md` 해시와 생태계 감사를 갱신한다.
3. AI 모델을 바꾸면 합성 입력 1건으로 응답 형식·비용·안전 오류를 확인한다.
4. 실제 MP4는 `validate:media`로 검사하고 자산 증빙은 `release-review.json`에 기록한다.
5. 창작 품질, 저작권, 최종 공개 여부는 각각 사람 판정으로 남긴다.
