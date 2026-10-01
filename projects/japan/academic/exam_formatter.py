#!/usr/bin/env python3
"""
academic/exam_formatter.py — Question Text Cleaning & Task Type Inference.
Strictly <= 200 lines invariant.
"""

import re
from typing import Any, Dict


def clean_question_text(text: str) -> str:
    """Strips repetitive carrier prompt boilerplate leaving pure Japanese."""
    if not text:
        return ""
    p1 = r"^(つぎの|次の)\s*(ぶんの|文の|文章の).*?[?？。]\s*\n?"
    cleaned = re.sub(p1, "", text, flags=re.DOTALL)
    p2 = r"^.*?どう\s*(よみますか|かきますか|読みますか|書きますか)[?？。]?\s*\n?"
    cleaned = re.sub(p2, "", cleaned, flags=re.DOTALL)
    p3 = r"^.*?どれを\s*(いれますか|入れますか)[?？。]?\s*\n?"
    cleaned = re.sub(p3, "", cleaned, flags=re.DOTALL)
    p4 = r"^.*?最も\s*適当な\s*ものは\s*どれですか[?？。]?\s*\n?"
    cleaned = re.sub(p4, "", cleaned, flags=re.DOTALL)
    p5 = r"^.*?どれが\s*(入りますか|はいりますか)[?？。]?\s*\n?"
    cleaned = re.sub(p5, "", cleaned, flags=re.DOTALL)
    return cleaned.strip() if cleaned.strip() else text.strip()


def derive_task_type(q: Dict[str, Any]) -> str:
    """Derives a concise, instant-scan task badge."""
    cat = q.get("category", "")
    qtext = q.get("question", "")
    if "★" in qtext:
        return "ORDINE FRASE ★"
    if any(k in cat for k in ["Writing", "Homophone", "Lookalike"]):
        return "SCRITTURA KANJI"
    if any(k in cat for k in ["Reading", "Fonetica", "Jukujikun", "熟字訓"]):
        return "LETTURA KANJI"
    if any(k in cat for k in ["Particle", "Grammar", "Form", "Conditional"]):
        return "GRAMMATICA & PARTICELLE"
    return "COMPLETAMENTO FRASE"
