import type {EditTimeline} from './types';

export const fixtureTimeline: EditTimeline = {
  schema_version: '2.0',
  audio_duration_ms: 30000,
  canvas: {width: 960, height: 540, fps: 30},
  audio_path: 'fixture/tone.wav',
  title: 'Webtoon timeline render fixture',
  clips: [
    {clip_id: 'clip-01', panel_id: 'panel-01', section_id: 'intro', media_path: 'fixture/panel-01.svg', start_ms: 0, end_ms: 10000, duration_ms: 10000, motion_preset: 'slow_zoom_in', fit: 'cover'},
    {clip_id: 'clip-02', panel_id: 'panel-02', section_id: 'verse', media_path: 'fixture/panel-02.svg', start_ms: 10000, end_ms: 20000, duration_ms: 10000, motion_preset: 'pan_left', fit: 'cover'},
    {clip_id: 'clip-03', panel_id: 'panel-03', section_id: 'chorus', media_path: 'fixture/panel-03.svg', start_ms: 20000, end_ms: 30000, duration_ms: 10000, motion_preset: 'slow_zoom_out', fit: 'cover'},
  ],
};
