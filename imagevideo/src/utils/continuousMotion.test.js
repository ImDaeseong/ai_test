import assert from 'node:assert/strict';
import test from 'node:test';

import {continuousZoompanFilter} from './continuousMotion.js';

test('still-image motion oscillates continuously instead of saturating at a maximum zoom', () => {
  const filter = continuousZoompanFilter(
    {width: 1920, height: 1080, fps: 30},
    {zoomAmplitude: 0.04, zoomPeriodSeconds: 30}
  );
  assert.match(filter, /cos\(2\*PI\*on\/900\)/);
  assert.match(filter, /sin\(2\*PI\*on\/1170\)/);
  assert.doesNotMatch(filter, /min\(zoom\+/);
  assert.match(filter, /s=1920x1080:fps=30/);
});
