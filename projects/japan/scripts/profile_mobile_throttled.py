#!/usr/bin/env python3
"""
scripts/profile_mobile_throttled.py
Progressive CPU throttling & mobile viewport profiler for Redmi Note 7 emulation.
Strictly <= 200 lines, <= 100 cols.
"""

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.chrome_cdp import ChromeRunner


def profile_rate(runner, rate: int):
    print(f"\n--- Testing CPU Throttling Rate: {rate}x ---")
    runner.set_cpu_throttling(rate)
    time.sleep(0.5)

    res = runner.evaluate("""
    (async () => {
        let longTasks = [];
        let observer = null;
        try {
            observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    longTasks.push({
                        duration: Math.round(entry.duration),
                        startTime: Math.round(entry.startTime)
                    });
                }
            });
            observer.observe({ entryTypes: ['longtask'] });
        } catch (e) {}

        // 1. Measure flip
        const t0 = performance.now();
        window.ankiFlipCard();
        const flipMs = Math.round((performance.now() - t0) * 10) / 10;

        await new Promise(r => setTimeout(r, 150));

        // 2. Measure answer
        const t1 = performance.now();
        window.ankiAnswerCard(3);
        const answerMs = Math.round((performance.now() - t1) * 10) / 10;

        await new Promise(r => setTimeout(r, 200));
        if (observer) observer.disconnect();

        return { flipMs, answerMs, longTasks };
    })()
    """, timeout=25.0)
    return res


def run_progressive_profiling():
    print("=" * 60)
    print("REDMI NOTE 7 PROGRESSIVE CPU THROTTLING PROFILER")
    print("Viewport: 393x851, DPR: 2.75, Touch Enabled")
    print("=" * 60)

    runner = ChromeRunner("https://japan.calq.it/anki")
    runner.start()
    try:
        runner.emulate_mobile(width=393, height=851, dpr=2.75)
        time.sleep(2.5)

        # Launch study session
        runner.evaluate("window.ankiOpenDeckOverview(1774737216111, 'Giapponese • Travel Pack')")
        time.sleep(1.0)
        runner.evaluate("window.ankiLaunchStudySession()")
        time.sleep(1.5)

        rates = [1, 4, 6, 8, 10, 12, 16]
        results = {}

        for r in rates:
            res = profile_rate(runner, r)
            results[r] = res
            print(f"[{r}x Throttling] Flip: {res.get('flipMs')}ms | "
                  f"Answer: {res.get('answerMs')}ms | "
                  f"LongTasks: {len(res.get('longTasks', []))} "
                  f"{res.get('longTasks')}")
            if (res.get('flipMs', 0) > 500 or res.get('answerMs', 0) > 500):
                print(f"[!] Bottleneck detected at {r}x throttling (>500ms)!")

        return results
    finally:
        runner.close()


if __name__ == "__main__":
    run_progressive_profiling()
