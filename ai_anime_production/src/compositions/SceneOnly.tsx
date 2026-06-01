import React from 'react';
import {AbsoluteFill} from 'remotion';
import {SceneClip} from '../components/SceneClip';
import {RenderScene} from '../data/manifest';

type Props = {
  scene: RenderScene;
  fps: number;
  bpm: number;
};

export const SceneOnly: React.FC<Props> = ({scene, fps, bpm}) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#050509'}}>
      <SceneClip scene={scene} fps={fps} bpm={bpm} />
    </AbsoluteFill>
  );
};
