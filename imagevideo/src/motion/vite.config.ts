import {defineConfig} from 'vite';
import motionCanvasModule from '@motion-canvas/vite-plugin';
import ffmpegModule from '@motion-canvas/ffmpeg';

// @motion-canvas/vite-plugin and @motion-canvas/ffmpeg ship as CJS with a
// .default wrapper in some Node/Vite interop paths. The fallback handles both.
const motionCanvas = (motionCanvasModule as any).default ?? motionCanvasModule;
const ffmpeg = (ffmpegModule as any).default ?? ffmpegModule;

export default defineConfig({
  plugins: [
    motionCanvas({
      project: './src/motion/project.ts',
      output: './output/motion-canvas'
    }),
    ffmpeg()
  ]
});
