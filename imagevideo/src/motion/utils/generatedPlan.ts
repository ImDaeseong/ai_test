export interface MotionPlanProject {
  title: string;
  aspect_ratio: '16:9' | '9:16' | '1:1';
  resolution: string;
  fps: number;
  font_style: string;
  color_palette: string[];
}

export interface MotionPlanSegment {
  id: number;
  start: string;
  end: string;
  duration: number;
  lyric: string;
  motion: {
    camera: string;
    background_motion: string;
    text_animation: string;
    transition: string;
  };
  style: {
    color_palette: string;
    lighting: string;
    background: string;
    emotional_tone: string;
  };
}

export interface MotionPlan {
  project: MotionPlanProject;
  segments: MotionPlanSegment[];
}

export const motionPlan: MotionPlan = {
  "project": {
    "title": "City lights are waking",
    "aspect_ratio": "16:9",
    "resolution": "1920x1080",
    "fps": 30,
    "font_style": "modern geometric sans serif",
    "color_palette": [
      "deep navy",
      "warm gold",
      "soft cyan",
      "clean white"
    ]
  },
  "segments": [
    {
      "id": 1,
      "start": "00:00:00.000",
      "end": "00:00:04.000",
      "duration": 4,
      "lyric": "City lights are waking",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; word-level highlight sweep across the lyric",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "deep navy, warm gold, soft cyan, clean white",
        "lighting": "gentle rim light with warm highlights",
        "background": "clean kinetic typography with abstract city light textures; original abstract environment with hopeful atmosphere and uncluttered text-safe center.",
        "emotional_tone": "hopeful"
      }
    },
    {
      "id": 2,
      "start": "00:00:04.000",
      "end": "00:00:08.000",
      "duration": 4,
      "lyric": "I find the rhythm in the rain",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; word-level highlight sweep across the lyric",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "deep navy, warm gold, soft cyan, clean white",
        "lighting": "gentle rim light with warm highlights",
        "background": "clean kinetic typography with abstract city light textures; original abstract environment with hopeful atmosphere and uncluttered text-safe center.",
        "emotional_tone": "introspective"
      }
    },
    {
      "id": 3,
      "start": "00:00:08.000",
      "end": "00:00:12.000",
      "duration": 4,
      "lyric": "Every step is a spark",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; word-level highlight sweep across the lyric",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "deep navy, warm gold, soft cyan, clean white",
        "lighting": "gentle rim light with warm highlights",
        "background": "clean kinetic typography with abstract city light textures; original abstract environment with hopeful atmosphere and uncluttered text-safe center.",
        "emotional_tone": "uplifting"
      }
    },
    {
      "id": 4,
      "start": "00:00:12.000",
      "end": "00:00:16.000",
      "duration": 4,
      "lyric": "We rise and start again",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; word-level highlight sweep across the lyric",
        "transition": "soft fade out"
      },
      "style": {
        "color_palette": "deep navy, warm gold, soft cyan, clean white",
        "lighting": "gentle rim light with warm highlights",
        "background": "clean kinetic typography with abstract city light textures; original abstract environment with hopeful atmosphere and uncluttered text-safe center.",
        "emotional_tone": "uplifting"
      }
    }
  ]
} as MotionPlan;

export const motionProjectSettings = {
  aspectRatio: motionPlan.project.aspect_ratio,
  resolution: motionPlan.project.resolution,
  fps: motionPlan.project.fps
};
