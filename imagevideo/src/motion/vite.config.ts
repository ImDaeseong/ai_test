import {defineConfig} from 'vite';
import motionCanvasModule from '@motion-canvas/vite-plugin';
import ffmpegModule from '@motion-canvas/ffmpeg';

// @motion-canvas/vite-plugin and @motion-canvas/ffmpeg ship as CJS with a
// .default wrapper in some Node/Vite interop paths. The fallback handles both.
const motionCanvas = (motionCanvasModule as any).default ?? motionCanvasModule;
const ffmpeg = (ffmpegModule as any).default ?? ffmpegModule;

export default defineConfig({
  // Explicit localhost-only binding: @motion-canvas/vite-plugin's
  // peerDependencies cap vite at "4.x || 5.x", so the dev-server CVEs fixed
  // in vite 6.4.3 (server.fs.deny bypass, etc.) can't be patched via a
  // version bump yet. This matches Vite's own default, but states the
  // intent explicitly rather than relying on it staying the default.
  server: {
    host: '127.0.0.1'
  },
  plugins: [
    motionCanvas({
      project: './src/motion/project.ts',
      output: './output/motion-canvas'
    }),
    ffmpeg()
  ]
});
