# Remotion v4 공식 API 참조

> 이 프로젝트의 영상 생성 코드 작성 시 반드시 이 문서를 기준으로 한다.
> 출처: https://www.remotion.dev/docs  
> 적용 버전: 4.0.461

---

## 1. Composition

`<Composition>` 은 영상 단위를 등록한다. `registerRoot()` 로 등록된 루트 컴포넌트 안에 배치한다.

### 필수 Props

| Prop | 타입 | 설명 |
|------|------|------|
| `id` | string | 영문자·숫자·`-`만 허용. 렌더 시 composition ID로 사용 |
| `component` | React.FC | 렌더할 컴포넌트 (lazyComponent와 양자택일) |
| `fps` | number | 초당 프레임 수 (예: 30) |
| `durationInFrames` | number | 총 프레임 수 |
| `width` | number | 가로 픽셀 (예: 1920) |
| `height` | number | 세로 픽셀 (예: 1080) |

### 선택 Props

| Prop | 설명 |
|------|------|
| `defaultProps` | 순수 JSON 직렬화 가능한 기본 props 객체 |
| `calculateMetadata` | 동적으로 fps/duration/width/height/props 결정하는 함수 |
| `lazyComponent` | 동적 import 함수 (component와 양자택일) |

### calculateMetadata

```typescript
const calcMeta: CalculateMetadataFunction<Props> = async ({props, defaultProps, abortSignal}) => {
  return {
    fps: props.fps,
    durationInFrames: props.scene.duration_frames,
    width: 1920,
    height: 1080,
    props: transformedProps, // 선택: props 변환
  };
};

<Composition
  id="SceneOnly"
  component={SceneOnly}
  fps={30}
  width={1920}
  height={1080}
  durationInFrames={900}           // defaultProps 기반 초기값
  calculateMetadata={calcMeta}     // 렌더 시 실제값으로 덮어씀
  defaultProps={{scene, fps: 30, bpm: 120}}
/>
```

**반환 가능 필드**: `fps`, `durationInFrames`, `width`, `height`, `props`, `defaultCodec`, `defaultOutName`, `defaultVideoImageFormat`, `defaultPixelFormat`, `defaultSampleRate`

---

## 2. AbsoluteFill

화면 전체를 채우는 절대 위치 div. 레이어 쌓기에 사용한다.

```typescript
// 적용되는 CSS
{
  position: 'absolute',
  top: 0, left: 0, right: 0, bottom: 0,
  width: '100%', height: '100%',
  display: 'flex',
  flexDirection: 'column',
}
```

**나중에 렌더된 레이어가 위에 표시된다** (HTML 기본 동작).

```tsx
import {AbsoluteFill} from 'remotion';

<AbsoluteFill>
  <AbsoluteFill><OffthreadVideo src="..." /></AbsoluteFill>  {/* 배경 */}
  <AbsoluteFill><h1>텍스트 오버레이</h1></AbsoluteFill>      {/* 전면 */}
</AbsoluteFill>
```

---

## 3. Sequence

자식 컴포넌트의 시간을 이동시키고 지속 시간을 제한한다.

### Props

| Prop | 기본값 | 설명 |
|------|--------|------|
| `from` | 0 | 자식이 시작할 프레임 (v3.2.36부터 선택) |
| `durationInFrames` | Infinity | 표시 지속 프레임 수. 이 범위를 벗어나면 자식 언마운트 |
| `layout` | `"absolute-fill"` | `"none"` 으로 하면 AbsoluteFill 래핑 없음 |
| `name` | — | Studio 타임라인 표시 레이블 |
| `style` | — | 컨테이너 CSS (layout="none" 에서는 무효) |
| `premountFor` | — | 표시 전 미리 마운트할 프레임 수 (깜빡임 방지) |

### useCurrentFrame 동작

```tsx
// 타임라인 프레임 30, Sequence from={30} 인 경우
// Sequence 밖: useCurrentFrame() = 30
// Sequence 안: useCurrentFrame() = 0  ← from 기준으로 리셋됨
```

### 중첩 예시

```tsx
<Sequence from={30} durationInFrames={45}>
  <MyComp />  {/* 타임라인 30~74에 표시, 내부에서는 0~44로 인식 */}
</Sequence>
```

---

## 4. useCurrentFrame

현재 프레임 번호를 반환하는 훅. 0-indexed.

```tsx
import {useCurrentFrame} from 'remotion';

const frame = useCurrentFrame();
// Sequence 안: Sequence 기준 상대 프레임
// Sequence 밖: 전체 컴포지션 기준 절대 프레임
```

**절대 프레임이 필요한 경우**: 상위 컴포넌트에서 `useCurrentFrame()` 호출 후 prop으로 전달.

---

## 5. useVideoConfig

컴포지션/시퀀스 메타데이터를 반환하는 훅.

```tsx
import {useVideoConfig} from 'remotion';

const {width, height, fps, durationInFrames, id} = useVideoConfig();
// Sequence 안: durationInFrames는 Sequence의 duration
// Sequence 밖: 컴포지션 전체 duration
```

---

## 6. spring

물리 기반 스프링 애니메이션. 목표값에 도달할 때 자연스러운 탄성이 있다.

```typescript
import {spring} from 'remotion';

const value = spring({
  frame,          // 현재 프레임 (useCurrentFrame())
  fps,            // useVideoConfig().fps
  from?: 0,       // 시작값 (기본 0)
  to?: 1,         // 목표값 (기본 1)
  durationInFrames?: number,  // 정확한 길이로 늘리기
  delay?: number,             // 시작 지연 프레임
  reverse?: false,            // 역방향 재생
  config: {
    mass?: 1,           // 질량 (낮을수록 빠름)
    damping?: 10,       // 감쇠 (높을수록 탄성 감소)
    stiffness?: 100,    // 강도 (높을수록 빠름)
    overshootClamping?: false,  // true: 오버슈트 방지
  },
});
```

### 현재 프로젝트 사용값 (promptMotion.ts)

```typescript
spring({
  frame,
  fps,
  config: { damping: 140, stiffness: 45, mass: 1.1 },
  durationInFrames: endFrame,
})
// damping 140 → 거의 탄성 없는 부드러운 슬라이드
```

---

## 7. interpolate

입력 범위를 출력 범위로 선형 매핑한다.

```typescript
import {interpolate} from 'remotion';

interpolate(
  inputValue,   // 현재 값
  inputRange,   // 입력 범위 배열 [0, 30]
  outputRange,  // 출력 범위 배열 [0, 1]
  options?: {
    extrapolateLeft:  'extend' | 'clamp' | 'wrap' | 'identity',  // 기본: 'extend'
    extrapolateRight: 'extend' | 'clamp' | 'wrap' | 'identity',  // 기본: 'extend'
    easing: (t: number) => number,  // 기본: 선형
  }
)
```

### 주요 패턴

```typescript
// 페이드 인 (0~30프레임)
const opacity = interpolate(frame, [0, 30], [0, 1], {
  extrapolateLeft: 'clamp',
  extrapolateRight: 'clamp',
});

// 다중 키프레임
const x = interpolate(frame, [0, 30, 60, 90], [0, 100, 50, 200]);

// spring 결과를 픽셀로 변환
const px = interpolate(springValue, [0, 1], [0, 500]);
```

---

## 8. Html5Video (영상 컴포넌트)

> **주의**: 구버전 `<Video>` 는 deprecated. 반드시 `<Html5Video>` 사용.

```tsx
import {Html5Video, staticFile} from 'remotion';

<Html5Video
  src={staticFile('video.mp4')}   // 필수: public/ 내 파일
  muted                            // 음소거 (렌더 시 파일 다운로드 최적화)
  loop                             // 반복 재생 (v3.2.29+)
  playbackRate={1}                 // 재생 속도 (기본 1, 역재생 불가)
  volume={0.5}                     // 볼륨 0~1
  volume={(f) => interpolate(f, [0, 30], [0, 1], {extrapolateRight: 'clamp'})}
  trimBefore={60}                  // 앞 60프레임 제거 (v4.0.319+, 구: startFrom)
  trimAfter={120}                  // 뒤 120프레임 제거 (v4.0.319+, 구: endAt)
  style={{width: '100%', height: '100%', objectFit: 'cover'}}
/>
```

**deprecated props**: `startFrom` → `trimBefore`, `endAt` → `trimAfter`

**성능 주의**: Html5Video는 브라우저 video 엘리먼트 기반. 정밀한 프레임 추출이 필요하면 OffthreadVideo 사용.

---

## 9. OffthreadVideo (고성능 영상 컴포넌트)

렌더링 시 FFmpeg로 정확한 프레임 추출. Html5Video보다 렌더 품질이 높다.

```tsx
import {OffthreadVideo, staticFile} from 'remotion';

<OffthreadVideo
  src={staticFile('video.mp4')}
  muted
  volume={0.5}
  playbackRate={1}
  trimBefore={0}
  trimAfter={90}
  transparent={false}    // true: PNG(투명도 지원, 느림) / false: BMP(기본, 빠름)
  toneMapped={true}      // false: 렌더 속도 향상, 색상 정확도 감소
/>
```

**Html5Video vs OffthreadVideo 선택 기준**:

| 상황 | 권장 |
|------|------|
| 정확한 프레임 추출 필요 | OffthreadVideo |
| 루프 재생 필요 | **Html5Video** (OffthreadVideo는 loop 미지원) |
| 일반 재생 | OffthreadVideo (렌더 품질 우수) |
| 클라이언트 사이드 렌더 | @remotion/media의 Video |

---

## 10. Html5Audio (오디오 컴포넌트)

> **주의**: 구버전 `<Audio>` 는 deprecated. 반드시 `<Html5Audio>` 사용.

```tsx
import {Html5Audio, staticFile} from 'remotion';

<Html5Audio
  src={staticFile('audio.mp3')}   // 필수
  volume={0.5}                     // 정적 볼륨 0~1
  volume={(f) => interpolate(f, [0, 30], [0, 1], {extrapolateLeft: 'clamp'})}
  muted={frame < 30}               // 조건부 음소거
  loop                             // 반복 (v3.2.29+)
  playbackRate={1}                 // 재생 속도
  trimBefore={60}                  // v4.0.319+
  trimAfter={120}                  // v4.0.319+
/>
```

**deprecated props**: `startFrom` → `trimBefore`, `endAt` → `trimAfter`

---

## 11. Img (이미지 컴포넌트)

> 네이티브 `<img>` 대신 사용. 이미지 로드 완료 전 렌더를 자동으로 블로킹한다.

```tsx
import {Img, staticFile} from 'remotion';

<Img
  src={staticFile('image.png')}
  style={{
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transform: `scale(${scale}) translate(${x}px, ${y}px)`,
  }}
  onError={() => { /* 실패 시 src 교체 또는 언마운트 필요 */ }}
  maxRetries={2}         // 실패 시 재시도 횟수 (기본 2)
/>
```

**GIF 사용 시**: `@remotion/gif` 패키지의 `<Gif>` 컴포넌트 사용.

---

## 12. staticFile

`public/` 폴더 내 파일을 URL로 변환한다.

```typescript
import {staticFile} from 'remotion';

// public/assets/audio/song.mp3 → 접근 가능한 URL
const audioUrl = staticFile('assets/audio/song.mp3');

// 특수문자 자동 인코딩 (v4.0+)
const url = staticFile('assets/audio/나만 홀로.mp3');  // # ? & 등 자동 처리
```

**호환 컴포넌트**: `<Img>`, `<Html5Audio>`, `<Html5Video>`, `<OffthreadVideo>`, `<Gif>`, Fetch API, FontFace()

---

## 13. delayRender / continueRender / cancelRender

비동기 데이터 로딩 시 렌더를 일시 정지한다.

```tsx
import {delayRender, continueRender, cancelRender} from 'remotion';

const MyComp: React.FC = () => {
  const [handle] = useState(() => delayRender('Loading SRT...', {
    timeoutInMilliseconds: 10000,  // 기본 30초
  }));

  useEffect(() => {
    fetchSubtitles()
      .then(() => continueRender(handle))
      .catch(err => cancelRender(err));
  }, []);

  return <div />;
};
```

**주의**: 30초 내 `continueRender` 미호출 시 렌더 타임아웃 오류 발생.

---

## 14. remotion render CLI

```bash
npx remotion render <entry-point> <composition-id> <output> [options]

# 기본 렌더
npx remotion render src/index.ts SceneOnly output/clips/scene_01.mp4

# props 파일로 전달
npx remotion render src/index.ts SceneOnly output/clips/scene_01.mp4 \
  --props=manifests/scene_props/scene_01_intro.json

# 주요 옵션
--codec=h264           # 코덱: h264, h265, vp8, vp9, av1, prores (기본: h264)
--crf=18               # 화질 (낮을수록 고화질, 파일 큼)
--pixel-format=yuv420p # 픽셀 포맷 (브라우저 호환)
--concurrency=4        # 병렬 렌더 스레드
--fps=30               # FPS 오버라이드
--width=1920           # 가로 오버라이드
--height=1080          # 세로 오버라이드
--muted                # 오디오 없이 렌더
--overwrite            # 기존 파일 덮어쓰기 (기본 true)
--log=verbose          # 로그 레벨: error, warn, info, verbose
--timeout=30000        # 프레임 해석 타임아웃 (ms)
--scale=1              # 스케일 배율 (0 < scale ≤ 16)
```

---

## 15. 현재 프로젝트 컴포넌트 구조

```
Root.tsx
├── Composition(id="MusicVideo")          # 전체 합본 (오디오+자막 포함)
│   └── MusicVideo.tsx
│       ├── Html5Audio(src=audio)
│       ├── Sequence × N scenes
│       │   └── SceneClip(scene, fps, bpm)
│       └── CaptionLayer(src=subtitles)
│
└── Composition(id="SceneOnly")           # 씬별 개별 클립 (오디오 없음)
    └── SceneOnly.tsx
        └── SceneClip(scene, fps, bpm)
            ├── [video_exists]  Html5Video(loop, muted) + LookOverlay
            ├── [image_exists]  Img(Ken Burns) + LookOverlay
            └── [없음]          Placeholder
```

### SceneClip 렌더 우선순위

```
1. scene.video_exists → Html5Video (loop=true, muted)
2. scene.image_exists → Img + Ken Burns 애니메이션
3. 둘 다 없음         → 다크 플레이스홀더
```

---

## 16. 주요 주의사항

| 항목 | 잘못된 코드 | 올바른 코드 |
|------|-----------|-----------|
| 오디오 | `<Audio>` | `<Html5Audio>` |
| 비디오 | `<Video>` | `<Html5Video>` 또는 `<OffthreadVideo>` |
| 이미지 | `<img>` | `<Img>` |
| 루프 비디오 | `<OffthreadVideo loop>` | `<Html5Video loop>` |
| 트리밍 | `startFrom` / `endAt` | `trimBefore` / `trimAfter` |
| 파일 경로 | `"/assets/audio/song.mp3"` | `staticFile('assets/audio/song.mp3')` |

---

## 17. 영상 생성 입력 명세 (video_gen_images)

```jsonc
// render_manifest.json 씬별 video_gen_images
[
  {"role": "character", "exists": true,  "path": "assets/images/character_reference.png"},
  {"role": "scene",     "exists": true,  "path": "assets/images/scene_01_intro.png"}
]
// exists: false 항목은 외부 AI 도구에 전달하지 않음
// character: 스타일 레퍼런스로 첨부
// scene: 기반 프레임(image-to-video)으로 첨부
```
