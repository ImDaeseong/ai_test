import assert from 'node:assert/strict';
import test from 'node:test';

import {parseArgs} from '../render/renderTypographyVideo.js';

test('typography renderer accepts the motion wrapper output flag', () => {
  assert.deepEqual(parseArgs(['--output', 'output/verification.mp4']), {
    output: 'output/verification.mp4'
  });
});

test('typography renderer keeps the documented short output flag', () => {
  assert.deepEqual(parseArgs(['--out', 'output/final.mp4']), {
    output: 'output/final.mp4'
  });
});
