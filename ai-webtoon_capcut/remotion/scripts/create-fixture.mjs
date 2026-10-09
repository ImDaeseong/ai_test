/** Generate deterministic fixture media without committing binary media files. */
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';

const output = path.resolve('public', 'fixture');
await mkdir(output, {recursive: true});
const palettes = [['#101827','#6d5dfc'],['#111b2d','#0ea5e9'],['#211327','#ec4899']];
for (let index = 1; index <= 3; index += 1) {
  const [start, end] = palettes[index - 1];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${start}"/><stop offset="1" stop-color="${end}"/></linearGradient></defs><rect width="960" height="540" fill="url(#g)"/><circle cx="${220 + index * 130}" cy="270" r="150" fill="rgba(255,255,255,.12)"/><text x="480" y="285" text-anchor="middle" fill="white" font-family="Arial" font-size="72" font-weight="700">PANEL ${index}</text></svg>`;
  await writeFile(path.join(output, `panel-0${index}.svg`), svg, 'utf8');
}
const sampleRate = 44100;
const seconds = 30;
const samples = sampleRate * seconds;
const wav = Buffer.alloc(44 + samples * 2);
wav.write('RIFF', 0); wav.writeUInt32LE(36 + samples * 2, 4); wav.write('WAVE', 8); wav.write('fmt ', 12);
wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22); wav.writeUInt32LE(sampleRate, 24);
wav.writeUInt32LE(sampleRate * 2, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write('data', 36); wav.writeUInt32LE(samples * 2, 40);
for (let sample = 0; sample < samples; sample += 1) {
  const envelope = Math.min(1, sample / (sampleRate * 0.3), (samples - sample) / (sampleRate * 0.3));
  const value = Math.sin((2 * Math.PI * 220 * sample) / sampleRate) * 0.035 * envelope;
  wav.writeInt16LE(Math.round(value * 32767), 44 + sample * 2);
}
await writeFile(path.join(output, 'tone.wav'), wav);
console.log('Generated deterministic 30-second fixture media.');
