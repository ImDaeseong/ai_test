# AI Anime Production

`input/` 폴더의 씬 이미지와 영상 프롬프트를 읽어 Remotion 렌더용 manifest를 만드는 작업 공간입니다.

## 빠른 시작

`input/`에 씬 파일을 넣습니다. 씬 수에는 제한이 없습니다.

```text
input/
  character_reference_prompt.png  # 선택: 캐릭터 메인 참고 이미지 (1개)
  scene_01_intro.png              # 씬 이미지
  scene_01_intro.md               # 영상 생성 프롬프트
  scene_02_verse.png              # 추가 씬 (선택)
  scene_02_verse.md
```

캐릭터가 없는 풍경/배경 중심 영상이면 `character_reference_prompt.png`를 넣지 않아도 됩니다.

씬 이미지와 프롬프트는 반드시 같은 basename을 사용해야 합니다.

```text
scene_01_intro.png
scene_01_intro.md
```

## 실행

```powershell
npm run import:input
npm run check
npm run render:scenes
```

한 번에 실행하려면:

```powershell
npm run build
```

또는 `run.bat` (더블클릭, Windows 메뉴).

## 입력 규칙

| 파일 | 필수 여부 | 설명 |
| --- | --- | --- |
| `character_reference_prompt.{png,jpg,jpeg,webp}` | 선택 (최대 1개) | 캐릭터 참고 이미지. 없으면 풍경/환경 중심 씬으로 처리 |
| `scene_NN_name.{png,jpg,jpeg,webp}` | 필수 (1개 이상) | 씬 이미지 |
| `scene_NN_name.md` | 필수 (씬당 1개) | 영상 생성 프롬프트 |

씬 이미지와 프롬프트는 반드시 1:1 대응해야 합니다. 이미지에 매칭되는 `.md`가 없거나 그 반대이면 import가 중단됩니다.

오디오, 자막, 임시 파일이 있으면 import가 중단됩니다.

## 출력

```text
public/assets/images/
  character_reference.png   # 캐릭터 입력이 있을 때만 생성
  scene_01_intro.png
  scene_02_verse.png

prompts/video_prompts/
  scene_01_intro.md
  scene_02_verse.md

manifests/
  render_manifest.json
  source/song_master.json
  source/scene_list.json

output/clips/
  scene_01_intro.mp4
  scene_02_verse.mp4
```

## 자동 추출

| 항목 | 추출 방법 | 기본값 |
| --- | --- | --- |
| 프로젝트 제목 | 프롬프트 첫 번째 `# 제목` 줄 | `AI Anime Scene` |
| BPM | `174 BPM` 같은 패턴 | `null` |
| 씬 길이 | `duration_seconds: 30` 같은 패턴 | 30초 |
| 카메라 방향 | `Camera motion: ...` | 빈 문자열 |
| 강도 | `intensity low` 같은 패턴 | 빈 문자열 |
