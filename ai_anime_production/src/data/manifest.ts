/** Safe BPM fallback when a prompt does not specify one. Not music-specific. */
export const DEFAULT_BPM = 120;

export type VideoGenImage = {
  path: string;
  exists: boolean;
  role: 'character' | 'scene';
};

export type RenderScene = {
  scene_number: number;
  section: string;
  slug: string;
  start: number;
  end: number;
  duration: number;
  start_frame: number;
  duration_frames: number;
  image: string;
  image_exists: boolean;
  video: string;
  video_exists: boolean;
  image_prompt: string;
  video_prompt: string;
  selected_video_prompt_platform?: string;
  selected_video_prompt?: string;
  video_gen_images: VideoGenImage[];
  camera_direction: string;
  movement: string;
  intensity: string;
  emotion: string;
};

export type RenderManifest = {
  title: string;
  fps: number;
  width: number;
  height: number;
  duration_seconds: number;
  duration_frames: number;
  bpm: number | null;
  audio: string | null;
  subtitles: string | null;
  subtitle_note?: string;
  character_image: string | null;
  character_image_exists: boolean;
  scenes: RenderScene[];
};

export const defaultManifest: RenderManifest = {
  title: 'AI Anime Music Video',
  fps: 30,
  width: 1920,
  height: 1080,
  duration_seconds: 30,
  duration_frames: 900,
  bpm: null,
  audio: null,
  subtitles: null,
  character_image: null,
  character_image_exists: false,
  scenes: [
    {
      scene_number: 1,
      section: 'Preview',
      slug: 'scene_01_preview',
      start: 0,
      end: 30,
      duration: 30,
      start_frame: 0,
      duration_frames: 900,
      image: 'assets/images/scene_01_preview.png',
      image_exists: false,
      video: 'assets/videos/scene_01_preview.mp4',
      video_exists: false,
      image_prompt: '',
      video_prompt: '',
      selected_video_prompt_platform: '',
      selected_video_prompt: '',
      video_gen_images: [
        {path: 'assets/images/scene_01_preview.png', exists: false, role: 'scene'},
      ],
      camera_direction: '',
      movement: '',
      intensity: '',
      emotion: '',
    },
  ],
};
