const TIMESTAMP_PATTERN = /^\d{2}:\d{2}:\d{2}\.\d{3}$/;

export function formatTimestamp(totalSeconds) {
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) {
    throw new Error(`Invalid timestamp seconds: ${totalSeconds}`);
  }

  const totalMilliseconds = Math.round(totalSeconds * 1000);
  const milliseconds = totalMilliseconds % 1000;
  const totalWholeSeconds = Math.floor(totalMilliseconds / 1000);
  const seconds = totalWholeSeconds % 60;
  const totalMinutes = Math.floor(totalWholeSeconds / 60);
  const minutes = totalMinutes % 60;
  const hours = Math.floor(totalMinutes / 60);

  return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)}.${pad(milliseconds, 3)}`;
}

export function isValidTimestamp(value) {
  if (typeof value !== 'string' || !TIMESTAMP_PATTERN.test(value)) {
    return false;
  }

  const [, , minutes, seconds] = value.match(/^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$/) || [];
  return Number(minutes) < 60 && Number(seconds) < 60;
}

function pad(value, length) {
  return String(value).padStart(length, '0');
}
