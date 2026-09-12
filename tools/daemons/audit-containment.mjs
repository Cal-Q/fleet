#!/usr/bin/env node
/**
 * Deterministic Boundary Containment & Anti-Clipping Audit Daemon
 * Strictly <= 200 lines.
 */

import fs from "node:fs";
import path from "node:path";

const IGNORE_DIRS = new Set(["node_modules", ".next", ".git", "dist", ".venv", ".local", "data", ".local", "data"]);

export function auditContainmentFile(filePath, code) {
  const lines = code.split("\n");
  const issues = [];
  const ext = path.extname(filePath);

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check 1: Scrollable containers must contain overscroll to prevent scroll chaining
    if (/(?:overflow-y:\s*auto|overflow-x:\s*auto|overflow:\s*auto|overflow-y-auto|overflow-x-auto)/.test(line)) {
      const windowEnd = Math.min(lines.length, i + 8);
      const snippet = lines.slice(i, windowEnd).join(" ");
      const hasOverscrollContain = /(?:overscroll-behavior|overscroll-contain|overscroll-(?:y|x)-contain)/.test(snippet);

      if (!hasOverscrollContain && !line.includes("no-audit")) {
        issues.push({
          line: i + 1,
          severity: "WARN",
          rule: "SCROLLABLE_CONTAINER_MISSING_OVERSCROLL_CONTAIN",
          msg: "Scrollable container lacks 'overscroll-behavior: contain'. May cause unwanted parent scroll chaining."
        });
      }
    }

    // Check 2: Single-screen apps should use svh or dvh instead of raw 100vh
    if (/(?:height:\s*100vh\b|h-screen\b)/.test(line) && !line.includes("100svh") && !line.includes("h-svh") && !line.includes("h-dvh") && !line.includes("no-audit")) {
      issues.push({
        line: i + 1,
        severity: "INFO",
        rule: "USE_100SVH_OVER_RAW_100VH",
        msg: "Use 100svh / 100dvh instead of raw 100vh to prevent mobile URL bar layout shift."
      });
    }
  }
  return issues;
}

export function scanDirectory(dir, issues = []) {
  if (!fs.existsSync(dir)) return issues;
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    if (IGNORE_DIRS.has(entry.name)) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      scanDirectory(fullPath, issues);
    } else if (entry.isFile() && [".html", ".css", ".tsx", ".jsx"].includes(path.extname(entry.name))) {
      const code = fs.readFileSync(fullPath, "utf-8");
      const fileIssues = auditContainmentFile(fullPath, code);
      if (fileIssues.length > 0) {
        issues.push({ file: fullPath, fileIssues });
      }
    }
  }
  return issues;
}

export function runContainmentAudit(targetDir) {
  const issues = scanDirectory(targetDir);
  console.log(`\n📦 [Boundary Containment Audit] Checking containment in ${targetDir}...`);

  if (issues.length === 0) {
    console.log("✅ Zero boundary containment or clipping issues detected.");
    return 0;
  }

  let warnCount = 0;
  for (const item of issues) {
    console.log(`  📄 ${item.file}`);
    for (const issue of item.fileIssues) {
      if (issue.severity === "WARN") warnCount++;
      const color = issue.severity === "WARN" ? "\x1b[33m" : "\x1b[36m";
      console.log(`    ${color}[${issue.severity}] Line ${issue.line}: ${issue.rule} - ${issue.msg}\x1b[0m`);
    }
  }
  return warnCount > 0 ? 1 : 0;
}

if (process.argv[1] && process.argv[1].endsWith("audit-containment.mjs")) {
  const target = process.argv[2] || process.cwd();
  process.exit(runContainmentAudit(path.resolve(target)));
}
