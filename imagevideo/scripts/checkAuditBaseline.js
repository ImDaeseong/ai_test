import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** Compare npm audit output with the explicitly reviewed exception boundary. */
export function evaluateAudit(report, baseline) {
  const errors = [];
  const vulnerabilities = report?.vulnerabilities;
  const counts = report?.metadata?.vulnerabilities;
  if (!vulnerabilities || !counts) {
    return ['npm audit JSON is missing vulnerability metadata.'];
  }

  const allowedPackages = new Set(baseline.allowedPackages ?? []);
  const allowedSources = new Set(baseline.allowedAdvisorySources ?? []);
  for (const [name, vulnerability] of Object.entries(vulnerabilities)) {
    if (!allowedPackages.has(name)) {
      errors.push(`Unreviewed vulnerable package: ${name}.`);
    }
    for (const item of vulnerability.via ?? []) {
      if (typeof item === 'object' && !allowedSources.has(item.source)) {
        errors.push(`Unreviewed advisory source ${item.source} for ${name}.`);
      }
    }
  }

  for (const severity of ['critical', 'high', 'moderate', 'low']) {
    const actual = Number(counts[severity] ?? 0);
    const maximum = Number(baseline.maximumSeverityCounts?.[severity] ?? 0);
    if (actual > maximum) {
      errors.push(`${severity} vulnerabilities increased: ${actual} > ${maximum}.`);
    }
  }
  return errors;
}

function main() {
  const baseline = JSON.parse(fs.readFileSync(path.join(ROOT, 'audit-baseline.json'), 'utf8'));
  const npmCli = process.env.npm_execpath;
  const command = npmCli ? process.execPath : 'npm';
  const args = npmCli ? [npmCli, 'audit', '--json'] : ['audit', '--json'];
  const result = spawnSync(command, args, {cwd: ROOT, encoding: 'utf8', shell: false});
  let report;
  try {
    report = JSON.parse(result.stdout);
  } catch {
    console.error(result.error?.message || result.stderr?.trim() || 'npm audit did not return JSON.');
    process.exitCode = 1;
    return;
  }
  const errors = evaluateAudit(report, baseline);
  if (errors.length) {
    console.error(`Audit baseline failed:\n- ${errors.join('\n- ')}`);
    process.exitCode = 1;
    return;
  }
  const counts = report.metadata.vulnerabilities;
  console.log(`Audit baseline PASS_WITH_HOLD: critical=${counts.critical}, high=${counts.high}, moderate=${counts.moderate}, low=${counts.low}.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main();
}
