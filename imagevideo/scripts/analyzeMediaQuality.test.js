import assert from 'node:assert/strict';
import test from 'node:test';

import {classifyQuality, parseQualityLog} from './analyzeMediaQuality.js';

const policy = {warningRatios: {black: 0.01, silence: 0.05, freeze: 0.6}, failureRatios: {black: 0.5, silence: 0.9}};

test('quality parser sums detector intervals and normalizes ratios', () => {
  const log = 'black_duration:2.0\nsilence_duration: 3.0\nfreeze_duration: 4.0\nblack_duration:1.0';
  assert.deepEqual(parseQualityLog(log, 10), {
    seconds: {black: 3, silence: 3, freeze: 4},
    ratios: {black: 0.3, silence: 0.3, freeze: 0.4}
  });
});

test('quality classifier distinguishes pass, hold, and hard failure', () => {
  assert.equal(classifyQuality({ratios: {black: 0, silence: 0, freeze: 0}}, policy).status, 'pass');
  assert.equal(classifyQuality({ratios: {black: 0.02, silence: 0, freeze: 0}}, policy).status, 'hold');
  assert.equal(classifyQuality({ratios: {black: 0.6, silence: 0, freeze: 0}}, policy).status, 'fail');
});
