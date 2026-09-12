#!/usr/bin/env node
/**
 * Deterministic Interactive Feedback Audit Daemon
 * Strictly <= 200 lines.
 */

import fs from "node:fs";
import path from "node:path";

const IGNORE_DIRS = new Set(["node_modules", ".next", ".git", "dist", ".venv", ".local", "data", ".local", "data"]);
const ACTIVE_FEEDBACK_REGEX = /(?::active|\bactive:(?:scale|opacity|translate|brightness|bg-|border-))/;
const TRANSITION_REGEX = /\btransition(?:-[a-z]+)?\b/;

export function auditFeedbackFile(filePath, code, allCss = "") {
  const lines = code.split("\n");
  const issues = [];
  const ext = path.extname(filePath);

  if (ext === ".css") {
    // Check if buttons defined in this CSS have active tactile states in this or companion CSS
    const btnMatches = code.match(/\.[a-zA-Z0-9_-]+-btn|\.btn-[a-zA-Z0-9_-]+/g) || [];
    for (const btnClass of btnMatches) {
      const hasActive = code.includes(`${btnClass}:active`) || code.includes(`${btnClass}:active`) || allCss.includes(`${btnClass}:active`) || allCss.includes(".btn:active");
      if (!hasActive && !btnClass.includes("no-audit")) {
        issues.push({
          line: 1,
          severity: "WARN",
          rule: "BUTTON_MISSING_ACTIVE_STATE",
          msg: `CSS class '${btnClass}' lacks :active tactile transform scale state.`
        });
      }
    }
    return issues;
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const isButton = /<button\b/.test(line);
    const hasOnClick = /onClick=\{|\bonclick=/.test(line);

    if (isButton || hasOnClick) {
      const windowEnd = Math.min(lines.length, i + 6);
      const snippet = lines.slice(i, windowEnd).join(" ");
      const classMatch = snippet.match(/(?:className|class)=(?:\{`([^`]+)`\}|["']([^"']+)["'])/);

      if (classMatch) {
        const classNames = classMatch[1] || classMatch[2] || "";
        const hasFeedback = ACTIVE_FEEDBACK_REGEX.test(classNames);
        const hasCompanionCss = (classNames.includes("btn") && (code.includes(".btn:active") || allCss.includes(".btn:active"))) ||
                                (classNames.includes("mode-btn") && (code.includes(".mode-btn:active") || allCss.includes(".mode-btn:active"))) ||
                                (classNames.includes("composer-chip") && (code.includes(".composer-chip:active") || allCss.includes(".composer-chip:active"))) ||
                                (classNames.includes("suggestion-chip") && (code.includes(".suggestion-chip:active") || allCss.includes(".suggestion-chip:active"))) ||
                                (classNames.includes("tap-press") && (code.includes(".tap-press:active") || allCss.includes(".tap-press:active")));

        if (!hasFeedback && !hasCompanionCss && !line.includes("no-audit") && !classNames.includes("backdrop")) {
          issues.push({
            line: i + 1,
            severity: "WARN",
            rule: "INTERACTIVE_MISSING_TACTILE_FEEDBACK",
            msg: `Clickable element '${classNames}' lacks tactile active feedback (active:scale-* or :active transform).`
          });
        }
      }
    }
  }
  return issues;
}

export function scanDirectory(dir, issues = []) {
  if (!fs.existsSync(dir)) return issues;

  let allCss = "";
  function gatherCss(curDir) {
    const list = fs.readdirSync(curDir, { withFileTypes: true });
    for (const item of list) {
      if (IGNORE_DIRS.has(item.name)) continue;
      const sub = path.join(curDir, item.name);
      if (item.isDirectory()) gatherCss(sub);
      else if (item.isFile() && item.name.endsWith(".css")) {
        try { allCss += "\n" + fs.readFileSync(sub, "utf-8"); } catch (_) {}
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
        const fileIssues = auditFeedbackFile(fullPath, code, allCss);
        if (fileIssues.length > 0) {
          issues.push({ file: fullPath, fileIssues });
        }
      }
    }
  }
  walk(dir);
  return issues;
}

export function runInteractiveAudit(targetDir) {
  const issues = scanDirectory(targetDir);
  console.log(`\n👆 [Interactive Feedback Audit] Scanning tactile response in ${targetDir}...`);

  if (issues.length === 0) {
    console.log("✅ Zero dead UI elements: all interactive controls have tactile feedback.");
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

if (process.argv[1] && process.argv[1].endsWith("audit-interactive-feedback.mjs")) {
  const target = process.argv[2] || process.cwd();
  process.exit(runInteractiveAudit(path.resolve(target)));
}
