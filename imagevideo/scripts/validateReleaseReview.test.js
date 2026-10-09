import assert from 'node:assert/strict';
import test from 'node:test';

import {evaluateReleaseReview} from './validateReleaseReview.js';

function approvedReview() {
  return {
    schemaVersion: 1,
    project: 'imagevideo',
    technicalValidation: 'pass',
    assets: [{
      label: 'synthetic-audio.wav',
      sourceEvidence: 'created locally for test',
      rightsBasis: 'owned',
      commercialUse: 'approved',
      attributionRequired: false,
      attributionText: ''
    }],
    humanReview: {
      creativeQuality: 'approved', copyright: 'approved', finalPublish: 'approved',
      reviewer: 'test reviewer', reviewedAt: '2026-10-09', notes: ''
    }
  };
}

test('release review accepts complete technical, rights, and human approval', () => {
  assert.deepEqual(evaluateReleaseReview(approvedReview()), {errors: [], holds: []});
});

test('release review keeps pending judgments as HOLD rather than PASS', () => {
  const review = approvedReview();
  review.technicalValidation = 'pending';
  review.assets[0].rightsBasis = 'pending';
  review.humanReview.creativeQuality = 'pending';
  review.humanReview.finalPublish = 'pending';
  const result = evaluateReleaseReview(review);
  assert.equal(result.errors.length, 0);
  assert.equal(result.holds.length, 4);
});

test('release review rejects publish approval before quality and copyright', () => {
  const review = approvedReview();
  review.humanReview.copyright = 'pending';
  const result = evaluateReleaseReview(review);
  assert.match(result.errors.join('\n'), /finalPublish cannot be approved/);
});

test('release review rejects missing attribution evidence', () => {
  const review = approvedReview();
  review.assets[0].attributionRequired = true;
  const result = evaluateReleaseReview(review);
  assert.match(result.errors.join('\n'), /requires attributionText/);
});
