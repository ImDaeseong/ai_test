import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {MusicVideo} from './compositions/MusicVideo';
import {SceneOnly} from './compositions/SceneOnly';
import {DEFAULT_BPM, RenderManifest, RenderScene, defaultManifest} from './data/manifest';

const calcMusicVideo: CalculateMetadataFunction<RenderManifest> = ({props}) => ({
  fps: props.fps,
  width: props.width,
  height: props.height,
  durationInFrames: props.duration_frames,
});

const calcSceneOnly: CalculateMetadataFunction<{
  scene: RenderScene;
  fps: number;
  bpm: number;
  beatTimesSeconds?: number[];
}> = ({props}) => ({
  fps: props.fps,
  width: 1920,
  height: 1080,
  durationInFrames: props.scene.duration_frames,
});

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="MusicVideo"
        component={MusicVideo}
        fps={defaultManifest.fps}
        width={defaultManifest.width}
        height={defaultManifest.height}
        durationInFrames={defaultManifest.duration_frames}
        calculateMetadata={calcMusicVideo}
        defaultProps={defaultManifest satisfies RenderManifest}
      />
      <Composition
        id="SceneOnly"
        component={SceneOnly}
        fps={30}
        width={1920}
        height={1080}
        durationInFrames={defaultManifest.scenes[0].duration_frames}
        calculateMetadata={calcSceneOnly}
        defaultProps={{
          scene: defaultManifest.scenes[0],
          fps: defaultManifest.fps,
          bpm: DEFAULT_BPM,
          beatTimesSeconds: [],
        }}
      />
    </>
  );
};
