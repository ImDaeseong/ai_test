# master_tag — Suno AI 음원 마스터링 프로세서

Pedalboard + Librosa + pyloudnorm 기반 오디오 마스터링 도구.  
적응형 EQ → 글루 컴프레서 → M/S 스테레오 처리 → LUFS 정규화 → 브릭월 리미터.

## 실행

```bash
pip install -r requirements.txt
python server.py
# 브라우저: http://127.0.0.1:5000
```

## 개선 이력 (2026-06-02)

### 버그 수정
| 파일 | 내용 |
|---|---|
| `server.py:148` | `_run_job` 함수에서 "queued" 이벤트를 중복 발행하던 문제 수정 — `/master` 엔드포인트에서 이미 발행하므로 `_run_job` 내 중복 제거 |

### 테스트
- `tests/test_core.py` 신규 작성 — 18개 테스트 전원 통과
- 대상: gain 수학 공식, LUFS 정규화, 파일 검증, 이벤트 헬퍼, 모듈 상수
