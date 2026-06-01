// 영상 전체에 걸쳐 사용되는 설정값을 한 곳에서 관리합니다.
// 여기만 수정하면 LyricVideo, Root 등 모든 컴포넌트에 반영됩니다.

export const VIDEO_CONFIG = {
  fps: 30,
  width: 1920,
  height: 1080,
} as const;

export const VIDEO_CONFIG_VERTICAL = {
  fps: 30,
  width: 1080,
  height: 1920,
} as const;

export const TIMING_CONFIG = {
  // 인트로: 배경 위에 곡명/아티스트를 오버레이하는 시간 (초)
  introSeconds: 3.2,
  // 아웃트로 페이드: 마지막 가사 이후 페이드 투 블랙 애니메이션 시간 (초)
  outroSeconds: 2.5,
  // 아웃트로 여백: 마지막 가사 종료 후 페이드 시작까지 여유 시간 (초)
  // 전체 비디오 추가 길이 = outroSeconds + outroBufferSeconds
  outroBufferSeconds: 1.5,
} as const;

export const LYRIC_STYLE = {
  // 현재 가사 줄
  currentFontSize: 'clamp(24px, 2.8vw, 44px)',
  currentFontWeight: 700,
  currentColor: '#ffffff',
  currentTextShadow: '0 0 14px rgba(198, 232, 224, 0.22), 0 7px 24px rgba(0, 0, 0, 0.6)',

  // 이전/다음 가사 줄
  contextFontSize: 'clamp(15px, 1.7vw, 26px)',
  contextFontWeight: 400,
  prevColor: 'rgba(255, 255, 255, 0.36)',
  nextColor: 'rgba(255, 255, 255, 0.28)',
  contextTextShadow: '0 2px 8px rgba(0,0,0,0.5)',

  // 3줄 컨테이너 위치 (화면 세로 기준 %)
  containerTopPercent: 64,
  lineGap: 16,
} as const;

export const WAVEFORM_STYLE = {
  // 파형 너비/높이 (px)
  width: 260,
  height: 86,
  // 화면 세로 기준 위치 (%)
  topPercent: 82.7,
  opacity: 0.68,
  // 주파수 샘플 수
  numLineSamples: 128,
  numSpikes: 56,
  numParticles: 10,
} as const;

export const FONT_FAMILY =
  'Inter, Pretendard, "Noto Sans KR", "Noto Sans JP", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif';
