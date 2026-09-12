#!/usr/bin/env node
/**
 * Deterministic Quint Controller - Master UI/UX & Architecture Auditor
 * Executes all 5 audit daemons against a project.
 * Strictly <= 200 lines.
 */

import path from "node:path";
import { runLineLimitAudit } from "./audit-line-limits.mjs";
import { runTransitionsAudit } from "./audit-transitions.mjs";
import { runLayoutAudit } from "./audit-layout.mjs";
import { runInteractiveAudit } from "./audit-interactive-feedback.mjs";
import { runContainmentAudit } from "./audit-containment.mjs";

export function runAllAudits(targetDir) {
  const absTarget = path.resolve(targetDir);
  console.log("=================================================================");
  console.log(" 🛡️  MASTER FLEET // DETERMINISTIC QUINT CONTROLLER AUDIT");
  console.log(` Target Directory: ${absTarget}`);
  console.log("=================================================================");

  const results = [
    { name: "Line Limits (<=200 Lines)", code: runLineLimitAudit(absTarget) },
    { name: "Fluid Transitions & Motion", code: runTransitionsAudit(absTarget) },
    { name: "Layout & Overlap Bounds", code: runLayoutAudit(absTarget) },
    { name: "Interactive Tactile Feedback", code: runInteractiveAudit(absTarget) },
    { name: "Boundary Containment & Anti-Clipping", code: runContainmentAudit(absTarget) }
  ];

  console.log("\n=================================================================");
  console.log(" 📊 AUDIT SCORECARD");
  console.log("=================================================================");

  let failed = 0;
  for (const res of results) {
    const status = res.code === 0 ? "✅ PASS" : "❌ FAIL";
    console.log(`  ${status}  -  ${res.name}`);
    if (res.code !== 0) failed++;
  }

  console.log("=================================================================");
  if (failed === 0) {
    console.log("🎉 ALL 5 DETERMINISTIC DAEMONS PASSED (100% COMPLIANT)\n");
    return 0;
  } else {
    console.error(`🛑 ${failed} AUDIT DAEMON(S) FAILED. Action required before deployment.\n`);
    return 1;
  }
}

const target = process.argv[2] || process.cwd();
process.exit(runAllAudits(target));
