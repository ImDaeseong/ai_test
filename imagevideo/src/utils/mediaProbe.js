import fs from 'node:fs/promises';
import {spawn} from 'node:child_process';

export async function validateFinalMediaOutput({mediaPath, planPath}) {
  const stat = await fs.stat(mediaPath).catch(() => null);
  if (!stat || !stat.isFile()) {
    throw new Error(`Final media file is missing: ${mediaPath}`);
  }
  if (stat.size <= 0) {
    throw new Error(`Final media file is empty: ${mediaPath}`);
  }

  const plan = JSON.parse(await fs.readFile(planPath, 'utf8'));
  const expectedResolution = parseResolution(plan?.project?.resolution);
  const expectedDuration = timestampToSeconds(plan?.project?.duration_total);
  const probe = await ffprobe(mediaPath);
  const video = probe.streams.find((stream) => stream.codec_type === 'video');
  const audio = probe.streams.find((stream) => stream.codec_type === 'audio');
  const durationSeconds = Number(probe.format?.duration ?? video?.duration ?? 0);

  const errors = [];

  if (!video) {
    errors.push('Final MP4 has no video stream.');
  } else {
    if (video.codec_name !== 'h264') {
      errors.push(`Final MP4 video codec must be h264, got ${video.codec_name}.`);
    }
    if (expectedResolution && (Number(video.width) !== expectedResolution.width || Number(video.height) !== expectedResolution.height)) {
      errors.push(`Final MP4 resolution must be ${expectedResolution.width}x${expectedResolution.height}, got ${video.width}x${video.height}.`);
    }
  }

  if (!audio) {
    errors.push('Final MP4 has no audio stream.');
  } else if (audio.codec_name !== 'aac') {
    errors.push(`Final MP4 audio codec must be aac, got ${audio.codec_name}.`);
  }

  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    errors.push('Final MP4 duration must be greater than zero.');
  }

  if (expectedDuration > 0 && durationSeconds > 0 && Math.abs(durationSeconds - expectedDuration) > 1.5) {
    errors.push(`Final MP4 duration ${durationSeconds.toFixed(3)}s differs from timeline ${expectedDuration.toFixed(3)}s by more than 1.5s.`);
  }

  if (errors.length > 0) {
    throw new Error(`ffprobe validation failed:\n- ${errors.join('\n- ')}`);
  }

  return {
    width: Number(video.width),
    height: Number(video.height),
    videoCodec: video.codec_name,
    audioCodec: audio.codec_name,
    durationSeconds,
    size: stat.size
  };
}

export function ffprobe(mediaPath) {
  return new Promise((resolve, reject) => {
    const child = spawn('ffprobe', [
      '-v',
      'error',
      '-print_format',
      'json',
      '-show_format',
      '-show_streams',
      mediaPath
    ], {
      cwd: process.cwd(),
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });

    child.on('error', (error) => {
      if (error.code === 'ENOENT') {
        reject(new Error('ffprobe is not installed or not available on PATH.'));
      } else {
        reject(error);
      }
    });

    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`ffprobe failed with exit code ${code}: ${stderr.trim()}`));
        return;
      }

      try {
        resolve(JSON.parse(stdout));
      } catch {
        reject(new Error('ffprobe returned invalid JSON.'));
      }
    });
  });
}

function parseResolution(value) {
  const match = typeof value === 'string' ? value.match(/^(\d+)x(\d+)$/) : null;
  if (!match) {
    return null;
  }
  return {width: Number(match[1]), height: Number(match[2])};
}

function timestampToSeconds(timestamp) {
  const match = typeof timestamp === 'string' ? timestamp.match(/^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$/) : null;
  if (!match) {
    return 0;
  }
  const [, hours, minutes, seconds, milliseconds] = match;
  return Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds) + Number(milliseconds) / 1000;
}
