#!/usr/bin/env node
/**
 * Deterministic Layout, Overlap & Truncation Audit Daemon
 * Strictly <= 200 lines.
 */

import fs from "node:fs";
import path from "node:path";

const IGNORE_DIRS = new Set(["node_modules", ".next", ".git", "dist", ".venv", ".local", "data", ".local", "data"]);
const SUSPICIOUS_TRUNCATE = /(?:class|className)=["'][^"']*\btruncate\b[^"']*["']/;
const FIXED_WIDE_CONTAINER = /(?:class|className)=["'][^"']*\b(?:w|min-w)-\[(?:[4-9]\d{2}|1\d{3})px\][^"']*["']/;

export function auditLayoutFile(filePath, code) {
  const lines = code.split("\n");
  const issues = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check 1: Truncate without title or tooltip (accessibility & info loss)
    if (SUSPICIOUS_TRUNCATE.test(line)) {
      const windowStart = Math.max(0, i - 3);
      const windowEnd = Math.min(lines.length, i + 5);
      const snippet = lines.slice(windowStart, windowEnd).join(" ");
      const hasTitle = /title=/.test(snippet) || /aria-label=/.test(snippet);
      if (!hasTitle && !line.includes("no-audit")) {
        issues.push({
          line: i + 1,
          severity: "WARN",
          rule: "TRUNCATE_WITHOUT_TOOLTIP",
          msg: "Element uses 'truncate' without title/tooltip. Info may be illegible on small viewports."
        });
      }
    }

    // Check 2: Fixed wide container exceeding standard mobile width (>380px)
    if (FIXED_WIDE_CONTAINER.test(line) && !line.includes("max-w-")) {
      issues.push({
        line: i + 1,
        severity: "WARN",
        rule: "MOBILE_VIEWPORT_OVERFLOW_RISK",
        msg: "Container defines fixed width > 380px without responsive max-w constraint, risking horizontal bleed."
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
    } else if (entry.isFile() && [".html", ".css", ".tsx", ".jsx", ".js"].includes(path.extname(entry.name))) {
      const code = fs.readFileSync(fullPath, "utf-8");
      const fileIssues = auditLayoutFile(fullPath, code);
      if (fileIssues.length > 0) {
        issues.push({ file: fullPath, fileIssues });
      }
    }
  }
  return issues;
}

export function runLayoutAudit(targetDir) {
  const issues = scanDirectory(targetDir);
  console.log(`\n📐 [Layout & Overlap Audit] Scanning layout boundaries in ${targetDir}...`);

  if (issues.length === 0) {
    console.log("✅ Zero layout overflow or unhandled truncation issues detected.");
    return 0;
  }

  let warnCount = 0;
  for (const item of issues) {
    console.log(`  📄 ${item.file}`);
    for (const issue of item.fileIssues) {
      warnCount++;
      console.log(`    [${issue.severity}] Line ${issue.line}: ${issue.rule} - ${issue.msg}`);
    }
  }
  return warnCount > 0 ? 1 : 0;
}

if (process.argv[1] && process.argv[1].endsWith("audit-layout.mjs")) {
  const target = process.argv[2] || process.cwd();
  process.exit(runLayoutAudit(path.resolve(target)));
}
