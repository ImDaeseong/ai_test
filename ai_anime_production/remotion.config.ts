import {Config} from '@remotion/cli/config';
import fs from 'node:fs';

const browserCandidates = [
  process.env.REMOTION_BROWSER_EXECUTABLE,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean) as string[];

const browserExecutable = browserCandidates.find((candidate) => fs.existsSync(candidate));

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(4);

if (browserExecutable) {
  Config.setBrowserExecutable(browserExecutable);
}
