import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

import {evaluateAudit, evaluateRuntimeAudit} from './checkAuditBaseline.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const baseline = {
  runtimeMustBeClean: true,
  maximumSeverityCounts: {critical: 0, high: 0, moderate: 0, low: 0},
  allowedPackages: [],
  allowedAdvisorySources: []
};

function report({name = 'vite', source = 123, critical = 0, high = 1} = {}) {
  return {
    vulnerabilities: {[name]: {via: [{source}]}},
    metadata: {vulnerabilities: {critical, high, moderate: 0, low: 0}}
  };
}

test('audit baseline accepts a completely clean dependency tree', () => {
  const clean = {
    vulnerabilities: {},
    metadata: {vulnerabilities: {critical: 0, high: 0, moderate: 0, low: 0, total: 0}}
  };
  assert.deepEqual(evaluateAudit(clean, baseline), []);
});

test('audit baseline rejects any vulnerable package', () => {
  assert.match(evaluateAudit(report(), baseline).join('\n'), /Unreviewed vulnerable package/);
});

test('audit baseline detects a new advisory on an allowed package', () => {
  assert.match(evaluateAudit(report({source: 999}), baseline).join('\n'), /Unreviewed advisory source/);
});

test('audit baseline detects severity growth', () => {
  assert.match(evaluateAudit(report({high: 2}), baseline).join('\n'), /high vulnerabilities increased/);
});

test('runtime audit must remain free of known vulnerabilities', () => {
  const clean = {metadata: {vulnerabilities: {total: 0}}};
  const vulnerable = {metadata: {vulnerabilities: {total: 1}}};
  assert.deepEqual(evaluateRuntimeAudit(clean, baseline), []);
  assert.match(evaluateRuntimeAudit(vulnerable, baseline).join('\n'), /Runtime dependencies contain 1/);
});

test('inactive Motion Canvas GUI and Vite server stay outside the installable package', () => {
  const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const installed = {...packageJson.dependencies, ...packageJson.devDependencies};
  for (const name of [
    '@motion-canvas/2d',
    '@motion-canvas/core',
    '@motion-canvas/ffmpeg',
    '@motion-canvas/ui',
    '@motion-canvas/vite-plugin',
    'vite'
  ]) {
    assert.equal(installed[name], undefined, `${name} must not return to the active dependency tree`);
  }
  assert.equal(packageJson.scripts['motion:dev'], undefined);
  assert.equal(packageJson.scripts['motion:build'], undefined);
});
