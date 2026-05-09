import {makeProject} from '@motion-canvas/core';
import lyricsScene from './scenes/lyricsScene?scene';
import {motionProjectSettings} from './utils/generatedPlan';

export default makeProject({
  name: 'lyric-typography',
  scenes: [lyricsScene],
  variables: {
    resolution: motionProjectSettings.resolution,
    aspectRatio: motionProjectSettings.aspectRatio,
    fps: motionProjectSettings.fps
  }
});
