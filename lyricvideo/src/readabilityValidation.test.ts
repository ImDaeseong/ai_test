import test from 'node:test';
import assert from 'node:assert/strict';
import {
  compositeColor,
  contrastRatio,
  validateLyricReadability,
} from './readabilityValidation';

test('lyric panel keeps current and context text above WCAG contrast thresholds', () => {
  const brightestMedia = {red: 255, green: 255, blue: 255, alpha: 1};
  const panel = compositeColor({red: 4, green: 10, blue: 16, alpha: 0.82}, brightestMedia);
  const current = compositeColor({red: 255, green: 255, blue: 255, alpha: 1}, panel);
  const context = compositeColor({red: 255, green: 255, blue: 255, alpha: 0.64}, panel);

  assert.ok(contrastRatio(current, panel) >= 7);
  assert.ok(contrastRatio(context, panel) >= 4.5);
});

test('validateLyricReadability rejects excessive reading speed', () => {
  assert.deepEqual(
    validateLyricReadability([{id: 'fast', start: 0, end: 1, text: 'This lyric line is much too fast to read comfortably'}]),
    ['line 1 exceeds 20 graphemes per second'],
  );
});

test('validateLyricReadability rejects an excessive line length', () => {
  assert.deepEqual(
    validateLyricReadability([{id: 'long', start: 0, end: 10, text: '가'.repeat(81)}]),
    ['line 1 exceeds 80 graphemes'],
  );
});

test('validateLyricReadability accepts a concise lyric line', () => {
  assert.deepEqual(
    validateLyricReadability([{id: 'clear', start: 0, end: 2, text: 'Readable lyric line'}]),
    [],
  );
});
