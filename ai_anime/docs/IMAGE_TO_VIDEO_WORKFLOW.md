# GPT Image to Flow/Kling Video Workflow

This guide explains how to use the generated prompt package for a full MV workflow:

1. Generate the song-specific character reference image with GPT Image.
2. Generate one approved scene image per scene with GPT Image.
3. Generate multiple short video clips from each scene image in Flow or Kling AI.
4. Stitch the clips in timeline order.

The key rule is simple: every song has its own character, palette, and motif. Do not mix references from another song.

---

## 1. Folder Structure

After running the pipeline, each song has this structure:

```text
output/<song title>/
  character_reference_prompt.md
  image_prompts/
    00_character_turnaround_model_sheet.md
    scene_01_intro.md
    scene_02_verse.md
    ...
  video_prompts/
    scene_01_intro.md
    scene_02_verse.md
    ...
  video_clip_prompts/
    timeline_plan.md
    scene_01_intro_clip_01.md
    scene_01_intro_clip_02.md
    ...
```

Use the folders this way:

```text
character_reference_prompt.md
  -> GPT Image prompt for the master character/model sheet.

image_prompts/*.md
  -> GPT Image prompts for still scene images.

video_prompts/*.md
  -> Section-level video direction. Good for overview and checking continuity.

video_clip_prompts/*.md
  -> Actual clip-by-clip prompts for Flow/Kling generation.

video_clip_prompts/timeline_plan.md
  -> The order and time range of all video clips.
```

---

## 2. Recommended Production Order

Follow this order for each song:

```text
Step 00: Generate character/model sheet
Step 01: Generate scene image 01
Step 02: Generate video clips for scene 01
Step 03: Generate scene image 02
Step 04: Generate video clips for scene 02
...
Final: Stitch clips according to timeline_plan.md
```

Do not generate video clips before the matching scene image is approved. The video prompt assumes image-to-video generation.

---

## 3. Generate The Character Reference Image With GPT Image

Open:

```text
output/<song title>/character_reference_prompt.md
```

Copy the full prompt into GPT Image.

Recommended settings:

```text
Model: gpt-image-2
Quality: high
Aspect ratio: square or portrait
Suggested size: 1024x1024 or 1024x1536
```

The result should be a clean character turnaround/model sheet. Check these items before continuing:

- The character is visibly song-specific.
- Full body is visible in the reference views.
- Hair, outfit, face, silhouette, and signature prop are clear.
- No text, watermark, logo, or readable letters are visible.
- The palette matches the prompt.
- The prop close-up is visible.

Save the approved image with a clear name:

```text
assets/<song title>/00_character_model_sheet.png
```

If you do not use an `assets` folder, any organized local folder is fine. Keep the image name stable.

---

## 4. Generate Scene Images With GPT Image

For each scene, open:

```text
output/<song title>/image_prompts/scene_XX_<section>.md
```

Use the `## GPT Image (gpt-image-2 / OpenAI)` section.

In GPT Image:

1. Attach the approved character/model sheet image.
2. Paste the GPT Image prompt for the scene.
3. Generate the image.
4. Review character consistency and scene readability.
5. Regenerate or edit until approved.

Recommended settings:

```text
Model: gpt-image-2
Quality: high
Aspect ratio: 16:9 for MV scenes
Suggested size: 1536x1024
```

Approval checklist for every scene image:

- Same character as the model sheet.
- Same hair, face, outfit, prop, and accent color.
- Scene location matches the prompt.
- Camera framing matches the prompt.
- No extra main characters unless explicitly requested.
- No text, subtitles, watermark, logo, or readable signs.
- The image can work as the first frame of a video clip.

Save approved scene images like this:

```text
assets/<song title>/scene_01_intro.png
assets/<song title>/scene_02_verse.png
assets/<song title>/scene_03_pre_chorus.png
```

---

## 5. Understand Section Prompts vs Clip Prompts

There are two kinds of video prompt files.

### Section-Level Prompts

```text
output/<song title>/video_prompts/scene_XX_<section>.md
```

These describe the whole music section. Use them to understand the scene direction.

They are not always the best unit for generation because many video tools produce short clips.

### Clip-Level Prompts

```text
output/<song title>/video_clip_prompts/scene_XX_<section>_clip_YY.md
```

These are the prompts you should use for actual generation.

Each clip file includes:

- scene number
- section name
- clip number
- timecode
- clip role
- reference flow
- platform-specific prompts for Flow, Kling AI, Sora, Runway, etc.

Always prefer `video_clip_prompts` for production.

---

## 6. Use timeline_plan.md

Open:

```text
output/<song title>/video_clip_prompts/timeline_plan.md
```

Example:

```text
| 02 Verse | 1/4 | 31.24s-37.68s | opening clip |
| 02 Verse | 2/4 | 37.68s-44.12s | detail clip |
| 02 Verse | 3/4 | 44.12s-50.57s | development clip |
| 02 Verse | 4/4 | 50.57s-57.01s | transition clip |
```

Generate clips in this order. The final edit should follow this order unless you intentionally change the MV structure.

---

## 7. Generate Video In Flow

Use Flow when you want a Veo-style image-to-video workflow with strong cinematic motion.

For each clip:

1. Open the clip prompt file:

```text
output/<song title>/video_clip_prompts/scene_XX_<section>_clip_YY.md
```

2. Find this section:

```text
## Google Flow (Veo Workflow)
```

3. Copy only the prompt text under that heading.

Do not copy the next platform heading. Stop before the next `##`.

4. Attach the correct image reference:

```text
For clip 01 of a scene:
  attach the approved scene image, for example scene_02_verse.png.

For clip 02+ of the same scene:
  attach the previous clip's final frame if Flow supports it.
  If not, attach the approved scene image again.
```

5. Paste the Flow prompt.

6. Set duration close to the timeline duration if the tool allows it:

```text
5s, 6s, or 8s are usually safe.
```

7. Generate the clip.

8. Check the result:

- Character stays consistent.
- No costume or hairstyle drift.
- Motion matches the clip role.
- Final frame is clean enough to continue into the next clip.
- No text or watermark.

9. Save the clip with a timeline-safe name:

```text
renders/<song title>/scene_02_verse_clip_01_flow.mp4
```

Flow reference strategy:

```text
Best:
  scene image as first frame/reference
  previous clip end frame as continuity reference for later clips

Acceptable:
  scene image only for every clip

Avoid:
  using a scene image from a different section
  using a character sheet alone without the scene image
```

---

## 8. Generate Video In Kling AI

Use Kling when you want shorter, controlled clips with concise motion.

For each clip:

1. Open the clip prompt file:

```text
output/<song title>/video_clip_prompts/scene_XX_<section>_clip_YY.md
```

2. Find:

```text
## Kling AI
```

3. Copy only the paragraph under `## Kling AI`.

Do not copy the note line beginning with `>`, unless you want it only as human guidance.

4. In Kling AI, choose image-to-video mode.

5. Upload the correct image:

```text
For clip 01:
  upload the approved scene image.

For clip 02+:
  upload the previous clip's final frame if you are extending continuity.
  Otherwise upload the approved scene image again.
```

6. Paste the Kling prompt.

7. Choose duration:

```text
5s or 10s depending on Kling availability.
Use 5s for tighter control.
Use 10s only if the prompt action is simple and stable.
```

8. Generate.

9. Review:

- The prompt ends in a settled motion state.
- Character identity does not drift.
- The prop remains visible when required.
- The camera move is simple.
- The scene does not introduce unrelated characters or objects.

10. Save:

```text
renders/<song title>/scene_02_verse_clip_01_kling.mp4
```

Kling practical rule:

```text
Short prompt + strong image reference usually beats long prompt + weak reference.
```

The generated Kling section is already compressed for this reason.

---

## 9. Which Prompt Should I Paste?

Use this table:

| Task | File | Section |
|---|---|---|
| Character model sheet | `character_reference_prompt.md` | whole file |
| Scene still image | `image_prompts/scene_XX.md` | `## GPT Image` |
| Flow video clip | `video_clip_prompts/scene_XX_clip_YY.md` | `## Google Flow (Veo Workflow)` |
| Kling video clip | `video_clip_prompts/scene_XX_clip_YY.md` | `## Kling AI` |
| Overall direction check | `video_prompts/scene_XX.md` | any platform section |
| Edit order | `video_clip_prompts/timeline_plan.md` | whole file |

---

## 10. Reference Attachment Rules

Use references in this priority:

```text
1. Matching approved scene image
2. Previous clip final frame
3. Character/model sheet as secondary reference if the tool supports it
```

For scene clip 01:

```text
Primary reference: scene image
Secondary reference: character model sheet if supported
```

For scene clip 02 and later:

```text
Primary reference: previous clip final frame
Secondary reference: original scene image or character model sheet if supported
```

Never use:

```text
Another song's character sheet
Another song's scene image
A later scene image for an earlier clip unless intentionally redesigning continuity
```

---

## 11. Clip Review Checklist

Approve a generated clip only if:

- Character face, hair, outfit, and prop stay consistent.
- Accent color and palette remain faithful to the song.
- The clip follows its role: opening, detail, development, or transition.
- Motion is readable and not overactive.
- The last frame can connect to the next clip.
- There are no unwanted subtitles, logos, watermarks, or random text.
- There are no extra limbs, distorted hands, or face warping.
- The emotional tone matches the section.

Reject or regenerate if:

- The character looks like a different person.
- The outfit changes.
- The prop disappears in a prop-focused clip.
- The camera movement fights the prompt.
- The clip introduces unrelated people.
- The final frame is too chaotic for continuity.

---

## 12. Suggested Naming Convention

Use this naming convention for generated assets:

```text
assets/<song title>/00_character_model_sheet.png
assets/<song title>/scene_01_intro.png
assets/<song title>/scene_02_verse.png

renders/<song title>/scene_01_intro_clip_01_flow.mp4
renders/<song title>/scene_01_intro_clip_02_flow.mp4
renders/<song title>/scene_02_verse_clip_01_kling.mp4
```

If you generate several attempts:

```text
scene_02_verse_clip_01_flow_v01.mp4
scene_02_verse_clip_01_flow_v02.mp4
scene_02_verse_clip_01_flow_APPROVED.mp4
```

---

## 13. Final Editing

After generating all clips:

1. Import the song audio into your editor.
2. Import clips in `timeline_plan.md` order.
3. Align clips to the listed timecodes.
4. Trim or stretch only slightly.
5. Keep cuts close to musical section boundaries.
6. Use the transition clips at the end of each section to hide continuity shifts.
7. Add no readable lyric text unless intentionally planned.

Recommended edit rule:

```text
If the music section is long, preserve the timeline order.
If the generated motion is weak, replace only that clip, not the whole scene.
```

---

## 14. Common Mistakes

Avoid these:

- Generating video from the character model sheet only.
- Using `video_prompts` instead of `video_clip_prompts` for long sections.
- Copying multiple platform sections into one tool.
- Forgetting to attach the scene image.
- Reusing a scene image from another song.
- Letting Flow/Kling invent a new outfit or hairstyle.
- Accepting a clip with a messy final frame.
- Editing clips out of timeline order without checking emotional continuity.

---

## 15. Quick Start Example

For `100 Seconds`, Scene 02 Verse:

1. Generate or open:

```text
assets/100 Seconds/scene_02_verse.png
```

2. Open:

```text
output/100 Seconds/video_clip_prompts/timeline_plan.md
```

3. See Scene 02 Verse has 4 clips:

```text
scene_02_verse_clip_01.md
scene_02_verse_clip_02.md
scene_02_verse_clip_03.md
scene_02_verse_clip_04.md
```

4. For Flow:

```text
Open scene_02_verse_clip_01.md
Copy ## Google Flow (Veo Workflow)
Attach scene_02_verse.png
Generate 6s video
Save as scene_02_verse_clip_01_flow.mp4
```

5. For Kling:

```text
Open scene_02_verse_clip_01.md
Copy ## Kling AI paragraph
Upload scene_02_verse.png in image-to-video mode
Generate 5s or 10s
Save as scene_02_verse_clip_01_kling.mp4
```

6. Continue with clip 02, using the previous clip's final frame when available.

That is the intended workflow.
