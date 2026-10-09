import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {evaluateReleaseReview, verifyReferencedFiles} from './validateReleaseReview.js';

const HASH = 'a'.repeat(64);

function approvedReview() {
  return {
    schemaVersion: 2,
    project: 'imagevideo',
    technicalValidation: 'pass',
    media: {path: 'output/video.mp4', sha256: HASH},
    qualityReport: {path: 'output/quality.json', sha256: HASH, status: 'pass', overrideReason: ''},
    assets: [{
      label: 'synthetic-audio.wav',
      path: 'input/synthetic-audio.wav', sha256: HASH,
      evidencePath: 'evidence/audio.txt', evidenceSha256: HASH,
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
  review.qualityReport.status = 'pending';
  review.humanReview.creativeQuality = 'pending';
  review.humanReview.finalPublish = 'pending';
  const result = evaluateReleaseReview(review);
  assert.equal(result.errors.length, 0);
  assert.equal(result.holds.length, 5);
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

test('release approval is bound to media, evidence, and quality-report hashes', async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'imagevideo-release-'));
  t.after(() => fs.rm(root, {recursive: true, force: true}));
  const review = approvedReview();
  for (const relative of ['output/video.mp4', 'input/synthetic-audio.wav', 'evidence/audio.txt']) {
    const absolute = path.join(root, relative);
    await fs.mkdir(path.dirname(absolute), {recursive: true});
    await fs.writeFile(absolute, relative);
  }
  review.media.sha256 = digest('output/video.mp4');
  const qualityContent = JSON.stringify({status: 'pass', mediaSha256: review.media.sha256});
  await fs.writeFile(path.join(root, 'output/quality.json'), qualityContent);
  review.qualityReport.sha256 = digest(qualityContent);
  review.assets[0].sha256 = digest('input/synthetic-audio.wav');
  review.assets[0].evidenceSha256 = digest('evidence/audio.txt');
  assert.deepEqual(verifyReferencedFiles(review, root), []);
  await fs.writeFile(path.join(root, 'output/video.mp4'), 'changed');
  assert.match(verifyReferencedFiles(review, root).join('\n'), /Final media SHA-256 mismatch/);

  function digest(value) {
    return crypto.createHash('sha256').update(value).digest('hex');
  }
});

test('publishing a quality hold requires an explicit human override reason', () => {
  const review = approvedReview();
  review.qualityReport.status = 'hold';
  const result = evaluateReleaseReview(review);
  assert.match(result.errors.join('\n'), /overrideReason/);
});
