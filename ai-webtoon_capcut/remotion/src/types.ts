export type MotionPreset = 'static' | 'slow_zoom_in' | 'slow_zoom_out' | 'pan_left' | 'pan_right';

export type TimelineClip = {
  clip_id: string;
  panel_id: string;
  section_id: string;
  media_path: string;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  motion_preset: MotionPreset | string;
  fit: 'cover' | 'contain' | string;
};

export type EditTimeline = {
  schema_version: '2.0';
  audio_duration_ms: number;
  canvas: {width: number; height: number; fps: number};
  clips: TimelineClip[];
  audio_path?: string | null;
  title?: string;
};
