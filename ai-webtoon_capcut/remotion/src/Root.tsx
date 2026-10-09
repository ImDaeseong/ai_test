import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {fixtureTimeline} from './fixture';
import type {EditTimeline} from './types';
import {validateTimeline} from './validateTimeline';
import {WebtoonVideo} from './WebtoonVideo';

const calculateMetadata: CalculateMetadataFunction<{timeline: EditTimeline}> = ({props}) => {
  validateTimeline(props.timeline);
  const {canvas, audio_duration_ms} = props.timeline;
  return {fps: canvas.fps, width: canvas.width, height: canvas.height, durationInFrames: Math.round((audio_duration_ms / 1000) * canvas.fps)};
};

export const Root: React.FC = () => <Composition id="WebtoonVideo" component={WebtoonVideo} width={fixtureTimeline.canvas.width} height={fixtureTimeline.canvas.height} fps={fixtureTimeline.canvas.fps} durationInFrames={fixtureTimeline.canvas.fps * 30} defaultProps={{timeline: fixtureTimeline}} calculateMetadata={calculateMetadata}/>;
