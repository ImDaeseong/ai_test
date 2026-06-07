# 배포 전 체크리스트

현재 배포 상태: `HOLD`

## 보안

- [x] `.env` 미사용
- [x] 비밀값 패턴 자동 검사
- [x] 산출물 절대 사용자 경로 검사
- [ ] Git history secret scan

## 코드

- [x] 자동 테스트 통과
- [x] 세 곡 build 회귀 통과
- [x] 214곡 discover 통과
- [ ] Remotion 렌더 통과
- [ ] WhisperX/Demucs 통합 통과

## 운영

- [x] 실행 명령 문서화
- [x] 구조화 로그
- [x] QA 보고서
- [x] 원본 불변
- [ ] 설치 자동화와 버전 고정

## 롤백

1. 실행 중단
2. 생성된 workspace run 폴더 제거
3. 이전 Git commit으로 코드 복원
4. 동일 입력 해시로 재실행

## 배포 판정 기준

5곡 end-to-end, Remotion preview, CapCut import, P0/P1 0건이 확인되기 전에는
`RELEASE`로 변경하지 않는다.
