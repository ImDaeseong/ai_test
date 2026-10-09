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

/** Require the installable production path to contain no known npm audit findings. */
export function evaluateRuntimeAudit(report, baseline) {
  if (!baseline.runtimeMustBeClean) return [];
  const counts = report?.metadata?.vulnerabilities;
  if (!counts) return ['Runtime npm audit JSON is missing vulnerability metadata.'];
  return Number(counts.total ?? 0) === 0
    ? []
    : [`Runtime dependencies contain ${counts.total} known vulnerabilities.`];
}

function runAudit(extraArgs = []) {
  const npmCli = process.env.npm_execpath;
  const command = npmCli ? process.execPath : 'npm';
  const args = npmCli ? [npmCli, 'audit', '--json', ...extraArgs] : ['audit', '--json', ...extraArgs];
  const result = spawnSync(command, args, {cwd: ROOT, encoding: 'utf8', shell: false});
  try {
    return JSON.parse(result.stdout);
  } catch {
    throw new Error(result.error?.message || result.stderr?.trim() || 'npm audit did not return JSON.');
  }
}

function main() {
  const baseline = JSON.parse(fs.readFileSync(path.join(ROOT, 'audit-baseline.json'), 'utf8'));
  try {
    const report = runAudit();
    const runtimeReport = runAudit(['--omit=dev']);
    const errors = [...evaluateAudit(report, baseline), ...evaluateRuntimeAudit(runtimeReport, baseline)];
    if (errors.length) {
      console.error(`Audit baseline failed:\n- ${errors.join('\n- ')}`);
      process.exitCode = 1;
      return;
    }
    const counts = report.metadata.vulnerabilities;
    console.log(`Audit baseline PASS_WITH_HOLD: runtime=0; development-only critical=${counts.critical}, high=${counts.high}, moderate=${counts.moderate}, low=${counts.low}.`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main();
}
