import {makeProject} from '@motion-canvas/core';
import lyricsScene from './scenes/lyricsScene?scene';

// Canvas size and FPS are set in project.meta (shared.size / preview.fps),
// which renderLyricsScene.ts writes from the production plan.
// makeProject.variables is for user scene variables only — not rendering config.
export default makeProject({
  name: 'lyric-typography',
  scenes: [lyricsScene]
});
