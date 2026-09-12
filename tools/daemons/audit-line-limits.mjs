#!/usr/bin/env node
/**
 * Deterministic Line Limit & Modular Invariant Audit Daemon
 * Strictly <= 200 lines per source file invariant across all projects.
 */

import fs from "node:fs";
import path from "node:path";

const MAX_LINES = 200;
const VALID_EXTS = new Set([".ts", ".tsx", ".js", ".mjs", ".css", ".py", ".html", ".sh"]);
const IGNORE_DIRS = new Set(["node_modules", ".next", ".git", "__pycache__", "dist", ".venv", ".local", "data", ".local", "data", "env", ".local"]);

export function scanDirectory(dir, issues = []) {
  if (!fs.existsSync(dir)) return issues;
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    if (IGNORE_DIRS.has(entry.name) || entry.name.startsWith(".local")) continue;
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      scanDirectory(fullPath, issues);
    } else if (entry.isFile()) {
      if (entry.name.endsWith(".user.js") || entry.name.endsWith(".min.js")) continue;
      const ext = path.extname(entry.name);
      if (VALID_EXTS.has(ext)) {
        try {
          const lines = fs.readFileSync(fullPath, "utf-8").split("\n").length;
          if (lines > MAX_LINES) {
            issues.push({ file: fullPath, lines, max: MAX_LINES });
          }
        } catch (e) {
          // Skip unreadable or stale remote inode
        }
      }
    }
  }
  return issues;
}

export function runLineLimitAudit(targetDir) {
  const issues = scanDirectory(targetDir);
  console.log(`\n📏 [Line Limit Audit] Checking <= ${MAX_LINES} lines in ${targetDir}...`);

  if (issues.length === 0) {
    console.log(`✅ All audited files strictly satisfy <= ${MAX_LINES} lines invariant.`);
    return 0;
  }

  console.error(`❌ Found ${issues.length} file(s) exceeding ${MAX_LINES} lines:`);
  for (const issue of issues) {
    console.error(`  - ${issue.file}: ${issue.lines} lines (limit: ${issue.max})`);
  }
  return 1;
}

if (process.argv[1] && process.argv[1].endsWith("audit-line-limits.mjs")) {
  const target = process.argv[2] || process.cwd();
  process.exit(runLineLimitAudit(path.resolve(target)));
}
