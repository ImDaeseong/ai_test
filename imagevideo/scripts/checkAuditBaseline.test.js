import assert from 'node:assert/strict';
import test from 'node:test';

import {evaluateAudit} from './checkAuditBaseline.js';

const baseline = {
  maximumSeverityCounts: {critical: 0, high: 1, moderate: 0, low: 0},
  allowedPackages: ['vite'],
  allowedAdvisorySources: [123]
};

function report({name = 'vite', source = 123, critical = 0, high = 1} = {}) {
  return {
    vulnerabilities: {[name]: {via: [{source}]}},
    metadata: {vulnerabilities: {critical, high, moderate: 0, low: 0}}
  };
}

test('audit baseline accepts only the reviewed package and advisory', () => {
  assert.deepEqual(evaluateAudit(report(), baseline), []);
});

test('audit baseline detects a new vulnerable package', () => {
  assert.match(evaluateAudit(report({name: 'new-package'}), baseline).join('\n'), /Unreviewed vulnerable package/);
});

test('audit baseline detects a new advisory on an allowed package', () => {
  assert.match(evaluateAudit(report({source: 999}), baseline).join('\n'), /Unreviewed advisory source/);
});

test('audit baseline detects severity growth', () => {
  assert.match(evaluateAudit(report({high: 2}), baseline).join('\n'), /high vulnerabilities increased/);
});
