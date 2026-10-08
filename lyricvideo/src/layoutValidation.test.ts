import test from 'node:test';
import assert from 'node:assert/strict';
import {validateLayoutRects} from './layoutValidation';

const canvas = {left: 0, top: 0, right: 1920, bottom: 1080};

test('validateLayoutRects accepts separated boxes inside the canvas', () => {
  assert.deepEqual(
    validateLayoutRects(canvas, [
      {role: 'previous', left: 300, top: 600, right: 1620, bottom: 640},
      {role: 'current', left: 300, top: 656, right: 1620, bottom: 720},
      {role: 'next', left: 300, top: 736, right: 1620, bottom: 776},
    ]),
    [],
  );
});

test('validateLayoutRects reports clipping', () => {
  assert.deepEqual(
    validateLayoutRects(canvas, [
      {role: 'current', left: 300, top: 1000, right: 1620, bottom: 1100},
    ]),
    ['current is clipped outside the render canvas'],
  );
});

test('validateLayoutRects reports overlap', () => {
  assert.deepEqual(
    validateLayoutRects(canvas, [
      {role: 'previous', left: 300, top: 600, right: 1620, bottom: 680},
      {role: 'current', left: 300, top: 660, right: 1620, bottom: 720},
    ]),
    ['previous overlaps current'],
  );
});
