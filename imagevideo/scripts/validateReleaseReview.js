import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const DECISIONS = new Set(['pending', 'approved', 'rejected']);
const RIGHTS = new Set(['pending', 'owned', 'licensed', 'public-domain', 'ai-generated']);

/** Validate evidence completeness while preserving subjective decisions as human gates. */
export function evaluateReleaseReview(review) {
  const errors = [];
  const holds = [];
  if (review?.schemaVersion !== 2 || review?.project !== 'imagevideo') {
    errors.push('schemaVersion 2 and project imagevideo are required.');
  }
  if (!['pending', 'pass', 'fail'].includes(review?.technicalValidation)) {
    errors.push('technicalValidation must be pending, pass, or fail.');
  } else if (review.technicalValidation !== 'pass') {
    (review.technicalValidation === 'fail' ? errors : holds).push('Technical media validation is not PASS.');
  }

  if (!String(review?.media?.path ?? '').trim() || !/^[a-f0-9]{64}$/.test(review?.media?.sha256 ?? '')) {
    errors.push('media.path and a lowercase SHA-256 are required.');
  }
  if (!String(review?.qualityReport?.path ?? '').trim() || !/^[a-f0-9]{64}$/.test(review?.qualityReport?.sha256 ?? '')) {
    errors.push('qualityReport.path and a lowercase SHA-256 are required.');
  }
  if (!['pending', 'pass', 'hold', 'fail'].includes(review?.qualityReport?.status)) {
    errors.push('qualityReport.status must be pending, pass, hold, or fail.');
  } else if (review.qualityReport.status === 'fail') {
    errors.push('Automated quality report failed.');
  } else if (review.qualityReport.status !== 'pass') {
    holds.push(`Automated quality report is ${review.qualityReport.status}.`);
  }

  if (!Array.isArray(review?.assets) || review.assets.length === 0) {
    errors.push('At least one asset evidence record is required.');
  } else {
    review.assets.forEach((asset, index) => {
      const prefix = `Asset ${index + 1}`;
      if (!String(asset?.label ?? '').trim() || !String(asset?.path ?? '').trim() || !/^[a-f0-9]{64}$/.test(asset?.sha256 ?? '')) {
        errors.push(`${prefix} requires label, path, and a lowercase SHA-256.`);
      }
      if (!String(asset?.evidencePath ?? '').trim() || !/^[a-f0-9]{64}$/.test(asset?.evidenceSha256 ?? '')) {
        errors.push(`${prefix} requires evidencePath and evidenceSha256.`);
      }
      if (!RIGHTS.has(asset?.rightsBasis)) {
        errors.push(`${prefix} has an invalid rightsBasis.`);
      } else if (asset.rightsBasis === 'pending') {
        holds.push(`${prefix} rightsBasis is pending.`);
      }
      if (!DECISIONS.has(asset?.commercialUse)) {
        errors.push(`${prefix} commercialUse must be pending, approved, or rejected.`);
      } else if (asset.commercialUse === 'rejected') {
        errors.push(`${prefix} is not approved for commercial use.`);
      } else if (asset.commercialUse === 'pending') {
        holds.push(`${prefix} commercialUse is pending.`);
      }
      if (asset?.attributionRequired === true && !String(asset?.attributionText ?? '').trim()) {
        errors.push(`${prefix} requires attributionText.`);
      }
    });
  }

  const human = review?.humanReview ?? {};
  for (const field of ['creativeQuality', 'copyright', 'finalPublish']) {
    if (!DECISIONS.has(human[field])) {
      errors.push(`humanReview.${field} must be pending, approved, or rejected.`);
    } else if (human[field] === 'rejected') {
      errors.push(`humanReview.${field} is rejected.`);
    } else if (human[field] === 'pending') {
      holds.push(`humanReview.${field} is pending.`);
    }
  }
  const anyApproval = ['creativeQuality', 'copyright', 'finalPublish'].some((field) => human[field] === 'approved');
  if (anyApproval && (!String(human.reviewer ?? '').trim() || !/^\d{4}-\d{2}-\d{2}$/.test(human.reviewedAt ?? ''))) {
    errors.push('Approved human decisions require reviewer and reviewedAt (YYYY-MM-DD).');
  }
  if (human.finalPublish === 'approved' && (human.creativeQuality !== 'approved' || human.copyright !== 'approved')) {
    errors.push('finalPublish cannot be approved before creativeQuality and copyright.');
  }
  if (human.finalPublish === 'approved' && review?.qualityReport?.status === 'hold' && !String(review.qualityReport.overrideReason ?? '').trim()) {
    errors.push('Publishing a quality HOLD requires qualityReport.overrideReason.');
  }
  return {errors, holds};
}

/** Verify that every approved artifact is byte-for-byte identical to its recorded hash. */
export function verifyReferencedFiles(review, root = process.cwd()) {
  const errors = [];
  const references = [
    ['Final media', review?.media?.path, review?.media?.sha256],
    ['Quality report', review?.qualityReport?.path, review?.qualityReport?.sha256],
    ...(review?.assets ?? []).flatMap((asset, index) => [
      [`Asset ${index + 1}`, asset?.path, asset?.sha256],
      [`Asset ${index + 1} evidence`, asset?.evidencePath, asset?.evidenceSha256]
    ])
  ];
  for (const [label, relativePath, expected] of references) {
    if (!relativePath || !/^[a-f0-9]{64}$/.test(expected ?? '')) continue;
    const absolute = path.resolve(root, relativePath);
    if (!absolute.startsWith(`${path.resolve(root)}${path.sep}`)) {
      errors.push(`${label} path escapes the project root.`);
      continue;
    }
    if (!fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) {
      errors.push(`${label} file is missing: ${relativePath}.`);
      continue;
    }
    const actual = crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
    if (actual !== expected) errors.push(`${label} SHA-256 mismatch: ${relativePath}.`);
  }
  const qualityPath = review?.qualityReport?.path
    ? path.resolve(root, review.qualityReport.path)
    : null;
  if (qualityPath?.startsWith(`${path.resolve(root)}${path.sep}`) && fs.existsSync(qualityPath)) {
    try {
      const report = JSON.parse(fs.readFileSync(qualityPath, 'utf8'));
      if (report.status !== review.qualityReport.status) {
        errors.push('Quality report status does not match release review.');
      }
      if (report.mediaSha256 !== review?.media?.sha256) {
        errors.push('Quality report is not bound to the approved media SHA-256.');
      }
    } catch {
      errors.push('Quality report is not valid JSON.');
    }
  }
  return errors;
}

function main() {
  const args = process.argv.slice(2);
  const allowHold = args.includes('--allow-hold');
  const filename = args.find((arg) => arg !== '--allow-hold');
  if (!filename) {
    console.error('Usage: node scripts/validateReleaseReview.js [--allow-hold] <review.json>');
    process.exitCode = 1;
    return;
  }
  let review;
  try {
    review = JSON.parse(fs.readFileSync(path.resolve(filename), 'utf8'));
  } catch (error) {
    console.error(`Cannot read release review: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
    return;
  }
  const result = evaluateReleaseReview(review);
  if (!allowHold) result.errors.push(...verifyReferencedFiles(review));
  if (result.errors.length) {
    console.error(`Release review FAIL:\n- ${result.errors.join('\n- ')}`);
    process.exitCode = 1;
  } else if (result.holds.length) {
    console.log(`Release review HOLD:\n- ${result.holds.join('\n- ')}`);
    process.exitCode = allowHold ? 0 : 2;
  } else {
    console.log('Release review PASS: technical, rights, creative, copyright, and publish gates are approved.');
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main();
}
