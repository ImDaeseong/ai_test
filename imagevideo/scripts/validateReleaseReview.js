import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const DECISIONS = new Set(['pending', 'approved', 'rejected']);
const RIGHTS = new Set(['pending', 'owned', 'licensed', 'public-domain', 'ai-generated']);

/** Validate evidence completeness while preserving subjective decisions as human gates. */
export function evaluateReleaseReview(review) {
  const errors = [];
  const holds = [];
  if (review?.schemaVersion !== 1 || review?.project !== 'imagevideo') {
    errors.push('schemaVersion 1 and project imagevideo are required.');
  }
  if (!['pending', 'pass', 'fail'].includes(review?.technicalValidation)) {
    errors.push('technicalValidation must be pending, pass, or fail.');
  } else if (review.technicalValidation !== 'pass') {
    (review.technicalValidation === 'fail' ? errors : holds).push('Technical media validation is not PASS.');
  }

  if (!Array.isArray(review?.assets) || review.assets.length === 0) {
    errors.push('At least one asset evidence record is required.');
  } else {
    review.assets.forEach((asset, index) => {
      const prefix = `Asset ${index + 1}`;
      if (!String(asset?.label ?? '').trim() || !String(asset?.sourceEvidence ?? '').trim()) {
        errors.push(`${prefix} requires label and sourceEvidence.`);
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
  return {errors, holds};
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
