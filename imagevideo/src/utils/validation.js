import {isValidTimestamp} from './timecode.js';

export const ALLOWED_ASPECT_RATIOS = new Set(['16:9', '9:16', '1:1']);

export function validatePlannerInput(input) {
  const errors = [];

  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return ['Input must be a JSON object.'];
  }

  if (typeof input.lyrics !== 'string' || input.lyrics.trim().length === 0) {
    errors.push('lyrics is required and must not be empty.');
  }

  if (input.aspect_ratio !== undefined && !ALLOWED_ASPECT_RATIOS.has(input.aspect_ratio)) {
    errors.push('aspect_ratio must be one of: 16:9, 9:16, 1:1.');
  }

  if (
    input.duration_per_line !== undefined &&
    (!Number.isFinite(Number(input.duration_per_line)) || Number(input.duration_per_line) <= 0)
  ) {
    errors.push('duration_per_line must be greater than zero.');
  }

  return errors;
}

export function validateProductionPlan(plan) {
  const errors = [];

  if (!plan || typeof plan !== 'object') {
    return ['Production plan must be an object.'];
  }

  if (!Array.isArray(plan.segments)) {
    return ['segments must be an array.'];
  }

  plan.segments.forEach((segment, index) => {
    const expectedId = index + 1;

    if (segment.id !== expectedId) {
      errors.push(`Segment IDs must be sequential. Expected ${expectedId}, got ${segment.id}.`);
    }

    if (!isValidTimestamp(segment.start)) {
      errors.push(`Segment ${segment.id ?? expectedId} has an invalid start timestamp.`);
    }

    if (!isValidTimestamp(segment.end)) {
      errors.push(`Segment ${segment.id ?? expectedId} has an invalid end timestamp.`);
    }
  });

  return errors;
}
