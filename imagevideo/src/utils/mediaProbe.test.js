import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {validateFinalMediaOutput} from './mediaProbe.js';

async function fixture(t) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'imagevideo-media-'));
  t.after(() => fs.rm(dir, {recursive: true, force: true}));
  const mediaPath = path.join(dir, 'video.mp4');
  const planPath = path.join(dir, 'plan.json');
  await fs.writeFile(mediaPath, 'fixture');
  await fs.writeFile(planPath, JSON.stringify({project: {resolution: '1920x1080', duration_total: '00:00:10.000'}}));
  return {mediaPath, planPath};
}

function validProbe(overrides = {}) {
  return {
    streams: [
      {codec_type: 'video', codec_name: 'h264', width: 1920, height: 1080},
      {codec_type: 'audio', codec_name: 'aac'}
    ],
    format: {duration: '10.2'},
    ...overrides
  };
}

test('final media accepts matching video, audio, resolution, and duration', async (t) => {
  const paths = await fixture(t);
  const report = await validateFinalMediaOutput({...paths, probeMedia: async () => validProbe()});
  assert.equal(report.videoCodec, 'h264');
  assert.equal(report.audioCodec, 'aac');
  assert.equal(report.width, 1920);
});

test('final media rejects missing audio and wrong video properties', async (t) => {
  const paths = await fixture(t);
  const probe = validProbe({
    streams: [{codec_type: 'video', codec_name: 'vp9', width: 1280, height: 720}],
    format: {duration: '14'}
  });
  await assert.rejects(
    validateFinalMediaOutput({...paths, probeMedia: async () => probe}),
    /video codec must be h264[\s\S]*resolution must be 1920x1080[\s\S]*no audio stream[\s\S]*differs from timeline/
  );
});
