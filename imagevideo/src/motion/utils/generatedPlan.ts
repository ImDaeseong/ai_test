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
    "title": "환승 음악 또 나오네",
    "aspect_ratio": "16:9",
    "resolution": "1920x1080",
    "fps": 30,
    "font_style": "modern geometric sans serif",
    "color_palette": [
      "ink black",
      "soft violet",
      "cool blue",
      "warm white"
    ]
  },
  "segments": [
    {
      "id": 1,
      "start": "00:00:13.085",
      "end": "00:00:15.319",
      "duration": 2.234,
      "lyric": "환승 음악 또 나오네",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 2,
      "start": "00:00:15.319",
      "end": "00:00:17.952",
      "duration": 2.633,
      "lyric": "사람들 사이 널 봤고",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 3,
      "start": "00:00:17.952",
      "end": "00:00:20.425",
      "duration": 2.473,
      "lyric": "동시에 폰 보는 척",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 4,
      "start": "00:00:20.425",
      "end": "00:00:22.660",
      "duration": 2.235,
      "lyric": "우리 둘 다 웃겼어 좀",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 5,
      "start": "00:00:22.660",
      "end": "00:00:25.532",
      "duration": 2.872,
      "lyric": "“어… 잘 지냈어?”",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 6,
      "start": "00:00:25.532",
      "end": "00:00:27.846",
      "duration": 2.314,
      "lyric": "딱 거기까지였고",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 7,
      "start": "00:00:27.846",
      "end": "00:00:29.920",
      "duration": 2.074,
      "lyric": "열차 들어오는 소리에",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 8,
      "start": "00:00:29.920",
      "end": "00:00:32.442",
      "duration": 2.522,
      "lyric": "대답은 잘 안 들렸어",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 9,
      "start": "00:00:32.792",
      "end": "00:00:35.027",
      "duration": 2.235,
      "lyric": "아무렇지 않은 척",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 10,
      "start": "00:00:35.027",
      "end": "00:00:37.819",
      "duration": 2.792,
      "lyric": "카드 찍고 걸었는데",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 11,
      "start": "00:00:37.819",
      "end": "00:00:40.052",
      "duration": 2.233,
      "lyric": "환승 통로 끝에서",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 12,
      "start": "00:00:40.052",
      "end": "00:00:42.576",
      "duration": 2.524,
      "lyric": "괜히 뒤돌아봤네",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 13,
      "start": "00:00:42.926",
      "end": "00:00:48.430",
      "duration": 5.504,
      "lyric": "숨 막히게 익숙한 표정",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 14,
      "start": "00:00:48.430",
      "end": "00:00:51.831",
      "duration": 3.401,
      "lyric": "지운 줄 알았는데 또",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 15,
      "start": "00:00:52.180",
      "end": "00:00:57.606",
      "duration": 5.426,
      "lyric": "잘 지내냐는 말 한 번에 또",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 16,
      "start": "00:00:57.606",
      "end": "00:01:02.314",
      "duration": 4.708,
      "lyric": "괜찮던 하루가 밀려와 또",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 17,
      "start": "00:01:02.314",
      "end": "00:01:07.420",
      "duration": 5.106,
      "lyric": "닫힌 문에 네 얼굴 비쳐",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 18,
      "start": "00:01:07.420",
      "end": "00:01:11.250",
      "duration": 3.83,
      "lyric": "내릴 역 지나쳤어 또",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 19,
      "start": "00:01:11.250",
      "end": "00:01:17.632",
      "duration": 6.382,
      "lyric": "또 환승 음악 나오는데",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 20,
      "start": "00:01:17.632",
      "end": "00:01:22.659",
      "duration": 5.027,
      "lyric": "왜 거기 멈춰 서 있냐 나",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 21,
      "start": "00:01:22.659",
      "end": "00:01:27.766",
      "duration": 5.107,
      "lyric": "다 끝났다 했는데 왜 또",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 22,
      "start": "00:01:27.766",
      "end": "00:01:33.081",
      "duration": 5.315,
      "lyric": "잘 지내냐는 말 한 번에 또",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 23,
      "start": "00:01:33.430",
      "end": "00:01:35.504",
      "duration": 2.074,
      "lyric": "편의점 원플원 커피",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 24,
      "start": "00:01:35.504",
      "end": "00:01:38.298",
      "duration": 2.794,
      "lyric": "두 개 집었다 놨어",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 25,
      "start": "00:01:38.298",
      "end": "00:01:40.293",
      "duration": 1.995,
      "lyric": "습관은 아직 그대로네",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 26,
      "start": "00:01:40.293",
      "end": "00:01:41.968",
      "duration": 1.675,
      "lyric": "참 별거 아닌데 또",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 27,
      "start": "00:01:41.968",
      "end": "00:01:42.605",
      "duration": 0.637,
      "lyric": "너도 봤을까 아마",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 28,
      "start": "00:01:42.605",
      "end": "00:01:46.355",
      "duration": 3.75,
      "lyric": "내 가방 달린 키링",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 29,
      "start": "00:01:46.355",
      "end": "00:01:48.750",
      "duration": 2.395,
      "lyric": "버렸다 하기엔 아직",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 30,
      "start": "00:01:48.750",
      "end": "00:01:53.427",
      "duration": 4.677,
      "lyric": "손이 좀 느렸나 봐",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 31,
      "start": "00:01:53.777",
      "end": "00:01:56.170",
      "duration": 2.393,
      "lyric": "막차 시간 뜨는 전광판",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 32,
      "start": "00:01:56.170",
      "end": "00:01:58.802",
      "duration": 2.632,
      "lyric": "그 밑에서 숨만 골랐어",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 33,
      "start": "00:01:58.802",
      "end": "00:02:01.197",
      "duration": 2.395,
      "lyric": "모른 척 지나가기엔",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 34,
      "start": "00:02:01.197",
      "end": "00:02:03.560",
      "duration": 2.363,
      "lyric": "심장이 먼저 알았어",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 35,
      "start": "00:02:03.909",
      "end": "00:02:06.462",
      "duration": 2.553,
      "lyric": "사람들은 다 급한데",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 36,
      "start": "00:02:06.462",
      "end": "00:02:09.015",
      "duration": 2.553,
      "lyric": "나만 거기 멈춘 듯이",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 37,
      "start": "00:02:09.015",
      "end": "00:02:11.489",
      "duration": 2.474,
      "lyric": "환승은 매일 하는데",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 38,
      "start": "00:02:11.489",
      "end": "00:02:13.133",
      "duration": 1.644,
      "lyric": "너는 아직 어렵네",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 39,
      "start": "00:02:13.484",
      "end": "00:02:18.590",
      "duration": 5.106,
      "lyric": "잘 지내냐는 말 한 번에 또",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 40,
      "start": "00:02:18.590",
      "end": "00:02:23.616",
      "duration": 5.026,
      "lyric": "멀쩡했던 밤이 길어져 또",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 41,
      "start": "00:02:23.616",
      "end": "00:02:28.723",
      "duration": 5.107,
      "lyric": "세탁 안 한 후드 뒤집어쓰고",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 42,
      "start": "00:02:28.723",
      "end": "00:02:33.750",
      "duration": 5.027,
      "lyric": "한참 TV만 돌렸어 또",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 43,
      "start": "00:02:33.750",
      "end": "00:02:38.776",
      "duration": 5.026,
      "lyric": "또 환승 음악 나오겠지",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 44,
      "start": "00:02:38.776",
      "end": "00:02:42.605",
      "duration": 3.829,
      "lyric": "내일도 사람들 사이로",
      "motion": {
        "camera": "gentle lateral drift with subtle parallax",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "quick blur dissolve"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 45,
      "start": "00:02:42.605",
      "end": "00:02:49.068",
      "duration": 6.463,
      "lyric": "다신 안 본다 했는데 왜 또",
      "motion": {
        "camera": "small pull-back revealing more negative space",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "fade and rise; hold with subtle breathing scale",
        "transition": "crossfade with light streak"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    },
    {
      "id": 46,
      "start": "00:02:49.068",
      "end": "00:02:51.592",
      "duration": 2.524,
      "lyric": "잘 지내냐는 말 한 번에 또",
      "motion": {
        "camera": "slow push-in with stable center framing",
        "background_motion": "slow atmospheric movement with soft particles and gradient shifts",
        "text_animation": "slide in with slight scale settle; hold with subtle breathing scale",
        "transition": "soft fade out"
      },
      "style": {
        "color_palette": "ink black, soft violet, cool blue, warm white",
        "lighting": "soft cinematic lighting with clear lyric readability",
        "background": "original kinetic typography with soft abstract backgrounds; original abstract environment with reflective atmosphere and uncluttered text-safe center.",
        "emotional_tone": "reflective"
      }
    }
  ]
} as MotionPlan;

export const motionProjectSettings = {
  aspectRatio: motionPlan.project.aspect_ratio,
  resolution: motionPlan.project.resolution,
  fps: motionPlan.project.fps
};
