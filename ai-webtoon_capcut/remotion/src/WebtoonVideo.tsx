import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {EditTimeline, TimelineClip} from './types';

const ClipView: React.FC<{clip: TimelineClip}> = ({clip}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const frames = Math.max(1, Math.round((clip.duration_ms / 1000) * fps));
  const progress = interpolate(frame, [0, Math.max(1, frames - 1)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const scale = clip.motion_preset === 'slow_zoom_out' ? 1.12 - progress * 0.12 : clip.motion_preset === 'slow_zoom_in' ? 1 + progress * 0.12 : 1.08;
  const x = clip.motion_preset === 'pan_left' ? 42 - progress * 84 : clip.motion_preset === 'pan_right' ? -42 + progress * 84 : 0;
  const opacity = interpolate(frame, [0, Math.min(12, frames / 4), Math.max(12, frames - 12), frames], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{backgroundColor:'#090d18', overflow:'hidden', opacity}}>
    <Img src={staticFile(clip.media_path)} style={{width:'100%',height:'100%',objectFit:clip.fit==='contain'?'contain':'cover',transform:`translate3d(${x}px,0,0) scale(${scale})`}} />
    <div style={{position:'absolute',left:28,bottom:24,padding:'10px 16px',borderRadius:999,background:'rgba(5,9,18,.72)',color:'white',font:'600 22px Arial'}}>{clip.section_id}</div>
  </AbsoluteFill>;
};

export const WebtoonVideo: React.FC<{timeline: EditTimeline}> = ({timeline}) => <AbsoluteFill>
  {timeline.audio_path ? <Audio src={staticFile(timeline.audio_path)} /> : null}
  {timeline.clips.map((clip) => {
    const from = Math.round((clip.start_ms / 1000) * timeline.canvas.fps);
    const durationInFrames = Math.round((clip.duration_ms / 1000) * timeline.canvas.fps);
    return <Sequence key={clip.clip_id} from={from} durationInFrames={durationInFrames} premountFor={timeline.canvas.fps}><ClipView clip={clip}/></Sequence>;
  })}
  <div style={{position:'absolute',right:24,top:20,color:'rgba(255,255,255,.75)',font:'500 18px Arial'}}>{timeline.title}</div>
</AbsoluteFill>;
