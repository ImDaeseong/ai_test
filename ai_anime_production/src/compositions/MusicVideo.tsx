import React from 'react';
import {AbsoluteFill, Html5Audio, Sequence, staticFile} from 'remotion';
import {CaptionLayer} from '../components/CaptionLayer';
import {SceneClip} from '../components/SceneClip';
import {DEFAULT_BPM, RenderManifest} from '../data/manifest';

type Props = {
  manifest: RenderManifest;
};

export const MusicVideo: React.FC<Props> = ({manifest}) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#050509'}}>
      {manifest.audio ? <Html5Audio src={staticFile(manifest.audio)} /> : null}

      {manifest.scenes.map((scene) => (
        <Sequence
          key={scene.slug}
          from={scene.start_frame}
          durationInFrames={scene.duration_frames}
        >
          <SceneClip scene={scene} fps={manifest.fps} bpm={manifest.bpm ?? DEFAULT_BPM} />
        </Sequence>
      ))}

      {manifest.subtitles ? (
        <CaptionLayer src={manifest.subtitles} fps={manifest.fps} />
      ) : null}
    </AbsoluteFill>
  );
};
