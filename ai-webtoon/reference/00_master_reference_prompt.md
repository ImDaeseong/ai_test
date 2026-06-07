# ai-webtoon 마스터 레퍼런스 프롬프트

> 이 파일의 프롬프트로 생성한 이미지를 `reference/` 폴더에 저장한다.
> 저장된 이미지가 이후 모든 패널 생성 시 레퍼런스로 첨부된다.
>
> **생성 순서:** 01 → 02 → 03 → 04 → 05 순서로 생성.  
> 01(전체 밴드)이 가장 중요. 01 이미지가 마음에 들면 나머지도 동일 스타일로 진행.

---

## 01 — 전체 밴드 마스터 (가장 중요)

> 이 이미지 하나가 모든 패널의 기준이 된다. 가장 공을 들여 생성할 것.

### GPT Image (gpt-image-2) — 1792x1024

```
Simple rounded Western cartoon style, thick bold black outlines, flat bright cel colors, large circular hollow eye sockets with neon magenta inner glow, chubby rounded body proportions, clean friendly original character design.

Full band portrait of an original fantasy skeleton music band on a colorful stylized cyberpunk city concert stage. Four members clearly visible:
- CENTER: skeleton vocalist, simple round skull, large circular hollow eye sockets glowing neon magenta, holding a decorative concert microphone, chubby rounded body, facing forward, expressive pose
- LEFT: skeleton guitarist, simple geometric round skull, large glowing hollow eye sockets, rounded stubby limbs, holding guitar in playful exaggerated pose
- RIGHT: skeleton bassist, round chubby skull, simple flat cartoon body, large hollow eye sockets softly glowing, holding bass guitar
- BACKGROUND: skeleton drummer, simple rounded skull, seated at drum kit, stubby round arms mid-motion

Stage: colorful stylized cyberpunk city concert stage, simple flat cartoon style, neon magenta spotlights.
Moon: the same massive glowing neon magenta moon, perfectly round and simple like a giant flat circle, filling the upper sky behind the stage.
Costume: simple flat cartoon stage outfits in dark colors with bright neon magenta accent details, rounded costume elements, no complex shading.
Palette: flat bright colors — deep black base, neon magenta highlights, vivid solid color fills.

Wide establishing shot, low angle looking up at the stage, all four band members clearly visible and distinguishable. 

Original characters only — not based on any existing IP. Do not make characters scary — keep them cute and charming. No text, no watermark, no logo.
```

### Nijijourney (--niji 7)

```
simple rounded Western cartoon style, original skeleton music band, four members, vocalist center holding microphone, guitarist left, bassist right, drummer background, large circular hollow eye sockets neon magenta glow, chubby rounded body proportions, thick bold black outlines, flat bright cel colors, colorful cyberpunk concert stage, giant round neon magenta moon, wide establishing shot, low angle, cute and charming original character design --niji 7 --ar 16:9 --s 250 --no watermark, text, logo, realistic, scary, horror, human characters, existing IP
```

### FLUX.1 (무료, 자연어)

```
A simple rounded Western cartoon illustration of an original fantasy skeleton music band performing on a colorful cyberpunk concert stage. Four band members are clearly visible: the vocalist stands at center holding a decorative microphone with a simple round skull and large circular hollow eye sockets glowing neon magenta, the guitarist stands to the left with a playful pose, the bassist stands to the right, and the drummer sits in the background at a drum kit. All characters have chubby rounded body proportions, short stubby limbs, and flat dark cartoon costumes with bright neon magenta accent details. A perfectly round massive neon magenta moon glows like a giant flat circle in the sky above the stage. Thick bold black outlines, flat bright colors, no gradients on characters, clean friendly original character design. No text, no watermark.
```

---

## 02 — 보컬 단독 클로즈업

> 감정 표현이 가장 많은 캐릭터. 눈구멍 빛의 강도로 감정을 표현.

### GPT Image (gpt-image-2) — 1792x1024

```
Simple rounded Western cartoon style, thick bold black outlines, flat bright cel colors, original character design.

Close-up portrait of the original skeleton vocalist from the fantasy skeleton music band. Simple round skull, large circular hollow eye sockets with vivid neon magenta inner glow, slightly open jaw in mid-performance expression, holding a decorative concert microphone close to the skull. Chubby rounded body proportions visible from chest up. Simple flat cartoon dark stage costume with bright neon magenta accent details. Background: blurred colorful cyberpunk stage with neon magenta lighting. Expression: expressive and charming, hollow eye sockets conveying emotion through glow intensity.

Thick bold black outlines, same line weight throughout. Flat bright colors with no gradients on the character. Deep black base, vivid neon magenta accent glow. Original character only — not based on any existing IP. Do not make character scary — keep cute and charming. No text, no watermark, no logo.
```

### Nijijourney (--niji 7)

```
simple rounded Western cartoon style, original skeleton vocalist close-up, simple round skull, large circular hollow eye sockets neon magenta glow, holding decorative microphone, chubby rounded proportions, expressive charming pose, flat dark costume neon magenta accent, colorful cyberpunk stage background, thick bold black outlines, flat bright cel colors, original character design --niji 7 --ar 16:9 --s 250 --no watermark, text, logo, realistic, scary, horror, existing IP
```

---

## 03 — 기타리스트 단독

### GPT Image (gpt-image-2) — 1792x1024

```
Simple rounded Western cartoon style, thick bold black outlines, flat bright cel colors, original character design.

Medium shot of the original skeleton guitarist from the fantasy skeleton music band. Simple geometric round skull, large glowing hollow eye sockets with neon magenta glow, rounded stubby limbs, holding a guitar in a playful exaggerated performance pose. Simple flat cartoon dark stage costume with neon magenta accent details. Background: colorful cyberpunk stage lighting. Chubby rounded body proportions, expressive and charming character.

Thick bold black outlines. Flat bright colors, no gradients. Original character only — not based on any existing IP. Do not make character scary. No text, no watermark, no logo.
```

---

## 04 — 베이시스트 단독

### GPT Image (gpt-image-2) — 1792x1024

```
Simple rounded Western cartoon style, thick bold black outlines, flat bright cel colors, original character design.

Medium shot of the original skeleton bassist from the fantasy skeleton music band. Round chubby skull, large circular hollow eye sockets softly glowing neon magenta, holding a bass guitar in a steady groove pose. Simple flat cartoon dark stage costume with neon magenta accent details. Chubby rounded body proportions, friendly and charming expression. Background: colorful cyberpunk stage.

Thick bold black outlines. Flat bright colors, no gradients. Original character only. No text, no watermark, no logo.
```

---

## 05 — 무대 전체 와이드 (달 포함)

> 달과 무대 세계관을 고정하는 배경 레퍼런스.

### GPT Image (gpt-image-2) — 1792x1024

```
Simple rounded Western cartoon style, thick bold black outlines, flat bright cel colors.

Wide establishing shot of the colorful stylized cyberpunk city concert stage. The entire skeleton band is visible as small figures performing on stage. The same massive glowing neon magenta moon — perfectly round and simple like a giant flat glowing circle — fills the upper half of the sky directly above the stage. Colorful cartoon cyberpunk city towers on both sides. Stage floor with neon magenta lighting. Crowd silhouettes in the foreground. Deep field composition: crowd foreground, stage midground, city skyline background.

Simple flat cartoon style backgrounds — colorful, not photorealistic. Thick bold black outlines. Flat bright colors. Original character design. No text, no watermark, no logo.
```

### Nijijourney (--niji 7)

```
simple rounded Western cartoon style, colorful cyberpunk concert stage wide shot, full skeleton band small figures on stage, giant round neon magenta moon flat circle in sky, colorful cartoon city towers, crowd silhouettes foreground, neon magenta stage lighting, deep field composition, thick bold black outlines, flat bright colors --niji 7 --ar 16:9 --s 250 --no watermark, text, logo, realistic, scary, horror
```

---

## 06 — 드러머 단독

> 배경에 위치해 전체 밴드 샷에서 작게 보이는 경우가 많음. 단독 레퍼런스로 디테일 고정.

### GPT Image (gpt-image-2) — 1792x1024

```
Simple rounded Western cartoon style, thick bold black outlines, flat bright cel colors, original character design.

Medium shot of the original skeleton drummer from the fantasy skeleton music band. Simple rounded skull, large circular hollow eye sockets with neon magenta glow, seated behind a colorful cartoon drum kit. Short stubby round arms raised mid-strike holding drumsticks. Exaggerated comic motion lines showing energetic drumming. Simple flat cartoon dark stage costume with neon magenta accent details. Chubby rounded body proportions. Background: colorful cyberpunk stage with neon magenta back lighting, smoke particles behind the drum kit.

Thick bold black outlines, same line weight throughout. Flat bright colors, no gradients on character. Original character only — not based on any existing IP. Do not make character scary — keep cute and charming. No text, no watermark, no logo.
```

### Nijijourney (--niji 7)

```
simple rounded Western cartoon style, original skeleton drummer, simple round skull, large circular hollow eye sockets neon magenta glow, seated at colorful cartoon drum kit, stubby round arms holding drumsticks mid-strike, exaggerated comic motion lines, chubby rounded proportions, flat dark costume neon magenta accent, cyberpunk stage neon back lighting, thick bold black outlines, flat bright cel colors, original character design --niji 7 --ar 16:9 --s 250 --no watermark, text, logo, realistic, scary, horror, existing IP
```

### FLUX.1 (무료, 자연어)

```
A simple rounded Western cartoon illustration of an original skeleton drummer seated at a colorful cartoon drum kit. The character has a simple rounded skull with large circular hollow eye sockets glowing neon magenta, short stubby round arms raised with drumsticks in mid-strike motion, and chubby rounded body proportions. Comic motion lines suggest energetic drumming. Simple flat dark cartoon costume with neon magenta accent details. Background shows colorful cyberpunk stage with neon magenta back lighting and soft smoke particles. Thick bold black outlines, flat bright colors, no gradients. Original character — not based on any existing IP. No text, no watermark.
```

---

## 07 — 군중 (관객)

> 무대 앞 관객 실루엣. 공연 규모감과 에너지 표현용.

### GPT Image (gpt-image-2) — 1792x1024

```
Simple rounded Western cartoon style, thick bold black outlines, flat bright colors.

Wide crowd shot of a cartoon concert audience in front of the colorful cyberpunk concert stage. Crowd foreground: simple rounded silhouette figures of audience members, hands raised, some holding phone lights as tiny glowing dots. Stage midground: the small figures of the original skeleton band performing, neon magenta spotlights visible. Background: the same massive glowing neon magenta moon — perfectly round flat circle — in the sky above the stage, colorful cartoon cyberpunk city towers on both sides.

Crowd silhouettes are simple rounded cartoon shapes — not detailed, just clear audience energy. Neon magenta light beams sweep overhead. Deep field composition: crowd fills bottom third, stage in upper center, moon prominent above.

Simple flat cartoon style. Thick bold black outlines. Flat bright colors with neon magenta accent lighting. No text, no watermark, no logo.
```

### Nijijourney (--niji 7)

```
simple rounded Western cartoon style, cartoon concert crowd wide shot, simple rounded audience silhouettes foreground, hands raised, phone lights as tiny dots, skeleton band small figures on stage midground, giant round neon magenta moon above, colorful cartoon cyberpunk city towers, neon magenta light beams overhead, deep field composition, crowd energy, thick bold black outlines, flat bright colors --niji 7 --ar 16:9 --s 250 --no watermark, text, logo, realistic, scary, horror
```

### FLUX.1 (무료, 자연어)

```
A simple rounded Western cartoon illustration of a concert crowd scene. Simple rounded silhouette figures of audience members fill the foreground with arms raised and tiny glowing phone lights. In the midground, the small figures of the original skeleton band perform on a colorful cyberpunk stage under neon magenta spotlights. Above the stage, the same massive perfectly round neon magenta moon glows like a giant flat circle in the sky, flanked by colorful cartoon cyberpunk city towers. Neon magenta light beams sweep overhead. Deep field composition creates a sense of scale. Simple flat cartoon style, thick bold black outlines, flat bright colors. No text, no watermark.
```

---

## 레퍼런스 저장 규칙

```
ai-webtoon/reference/
├── 00_master_reference_prompt.md   ← 이 파일
├── 밴드전체화면 마스터.png           ← 전체 밴드 마스터 (가장 중요)
├── 보컬.png                        ← 보컬 클로즈업
├── 기타.png                        ← 기타리스트
├── 베이스.png                      ← 베이시스트
├── 전체 무대 장면.png               ← 무대 전체 + 달
├── 드럼.png                        ← 드러머
└── 군중 장면.png                   ← 군중/관객
```

## 이미지 생성 후 활용

1. 생성된 이미지를 위 경로에 저장 (현재 저장 완료 ✅)
2. **모든 패널 생성 시** → `밴드전체화면 마스터.png` 필수 첨부
3. 패널 타입별 추가 첨부:

| 패널 타입 | 필수 첨부 | 추가 첨부 |
|----------|---------|---------|
| `wide` (와이드) | 밴드전체화면 마스터.png | 전체 무대 장면.png |
| `closeup` (클로즈업) | 밴드전체화면 마스터.png | 보컬.png |
| `medium` (미디엄) | 밴드전체화면 마스터.png | 보컬.png 또는 기타.png 또는 베이스.png |
| `silhouette` (실루엣) | 밴드전체화면 마스터.png | 전체 무대 장면.png |
| `detail` (디테일) | 밴드전체화면 마스터.png | 기타.png 또는 베이스.png 또는 드럼.png |
| `crowd` (군중) | 밴드전체화면 마스터.png | 군중 장면.png |
| `atmosphere` (분위기) | 밴드전체화면 마스터.png | 전체 무대 장면.png |

## 주의사항

- 01번 이미지가 마음에 안 들면 → 다시 생성. 이 이미지가 전체 MV의 캐릭터 기준이 됨
- 01번 이미지와 스타일이 다른 패널 이미지가 나오면 → 01번 이미지를 레퍼런스로 다시 첨부하여 재생성
- ai_img_video_prompt/reference/ 이미지는 임시 참고용. 웹툰 스타일 이미지 생성 후 교체할 것
