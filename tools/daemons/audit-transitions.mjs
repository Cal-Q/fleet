#!/usr/bin/env node
/**
 * Deterministic Transition & Fluid Motion Audit Daemon
 * Strictly <= 200 lines.
 */

import fs from "node:fs";
import path from "node:path";

const ANIM_REGEX = /(?:animate-|transition|fadeIn|scaleIn|pulse|transform)/;
const IGNORE_DIRS = new Set(["node_modules", ".next", ".git", "dist", ".venv", ".local", "data", ".local", "data"]);

export function auditTransitionFile(filePath, code, cssRules = "") {
  const lines = code.split("\n");
  const issues = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (/(?:modal|drawer|dialog|sidebar)/i.test(line) && /(?:class=|className=)/.test(line)) {
      const windowEnd = Math.min(lines.length, i + 6);
      const snippet = lines.slice(i, windowEnd).join(" ");
      const hasInlineAnim = ANIM_REGEX.test(snippet);
      const hasCssAnim = cssRules && /(?:\.sidebar|\.modal|\.gemini-modal|\.drawer)[^{]*\{[^}]*(?:transition|animation)/.test(cssRules);

      if (!hasInlineAnim && !hasCssAnim && !line.includes("no-audit")) {
        issues.push({
          line: i + 1,
          severity: "WARN",
          rule: "MODAL_DRAWER_MISSING_TRANSITION",
          msg: "Modal, drawer, or dialog container lacks entrance/exit transition animation."
        });
      }
    }

    if (/(?:mode-switch|tab-nav|tab-header)/i.test(line) && /(?:class=|className=)/.test(line)) {
      const windowEnd = Math.min(lines.length, i + 5);
      const snippet = lines.slice(i, windowEnd).join(" ");
      const hasInlineAnim = ANIM_REGEX.test(snippet);
      const hasCssAnim = cssRules && /(?:\.mode-switch|\.mode-btn|\.tab)[^{]*\{[^}]*(?:transition|animation)/.test(cssRules);

      if (!hasInlineAnim && !hasCssAnim && !line.includes("no-audit")) {
        issues.push({
          line: i + 1,
          severity: "WARN",
          rule: "TAB_SWITCH_MISSING_TRANSITION",
          msg: "Tab or mode switcher lacks smooth transition animation."
        });
      }
    }
  }
  return issues;
}

export function scanDirectory(dir, issues = []) {
  if (!fs.existsSync(dir)) return issues;

  let cssRules = "";
  function gatherCss(curDir) {
    const list = fs.readdirSync(curDir, { withFileTypes: true });
    for (const item of list) {
      if (IGNORE_DIRS.has(item.name)) continue;
      const sub = path.join(curDir, item.name);
      if (item.isDirectory()) gatherCss(sub);
      else if (item.isFile() && item.name.endsWith(".css")) {
        try { cssRules += "\n" + fs.readFileSync(sub, "utf-8"); } catch (_) {}
      }
    }
  }
  gatherCss(dir);

  function walk(curDir) {
    const list = fs.readdirSync(curDir, { withFileTypes: true });
    for (const entry of list) {
      if (IGNORE_DIRS.has(entry.name)) continue;
      const fullPath = path.join(curDir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.isFile() && [".html", ".css", ".tsx", ".jsx"].includes(path.extname(entry.name))) {
        const code = fs.readFileSync(fullPath, "utf-8");
        const fileIssues = auditTransitionFile(fullPath, code, cssRules);
        if (fileIssues.length > 0) {
          issues.push({ file: fullPath, fileIssues });
        }
      }
    }
  }
  walk(dir);
  return issues;
}

export function runTransitionsAudit(targetDir) {
  const issues = scanDirectory(targetDir);
  console.log(`\n🌊 [Transitions Audit] Checking fluid animations in ${targetDir}...`);

  if (issues.length === 0) {
    console.log("✅ All modals, drawers, and state toggles enforce fluid animations.");
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

if (process.argv[1] && process.argv[1].endsWith("audit-transitions.mjs")) {
  const target = process.argv[2] || process.cwd();
  process.exit(runTransitionsAudit(path.resolve(target)));
}
