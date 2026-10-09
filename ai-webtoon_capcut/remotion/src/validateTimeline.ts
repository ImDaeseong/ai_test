import type {EditTimeline} from './types';

export const validateTimeline = (timeline: EditTimeline): void => {
  if (timeline.schema_version !== '2.0') throw new Error('timeline schema_version must be 2.0');
  if (!Number.isInteger(timeline.canvas.fps) || timeline.canvas.fps <= 0) throw new Error('timeline fps must be a positive integer');
  if (timeline.audio_duration_ms <= 0) throw new Error('audio_duration_ms must be positive');
  if (timeline.clips.length === 0) throw new Error('timeline must contain at least one clip');
  let cursor = 0;
  for (const clip of timeline.clips) {
    if (clip.start_ms !== cursor) throw new Error(`timeline gap or overlap before ${clip.clip_id}`);
    if (clip.end_ms <= clip.start_ms || clip.duration_ms !== clip.end_ms - clip.start_ms) throw new Error(`invalid duration for ${clip.clip_id}`);
    if (!clip.media_path) throw new Error(`missing media_path for ${clip.clip_id}`);
    cursor = clip.end_ms;
  }
  if (cursor !== timeline.audio_duration_ms) throw new Error('timeline duration must equal audio duration');
};
