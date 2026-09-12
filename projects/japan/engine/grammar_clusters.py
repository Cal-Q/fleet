#!/usr/bin/env python3
"""
tools/grammar_clusters.py — MEXT High-Yield Grammar Classification & Sorting
Groups grammar rules into 4 surgical clusters for Part B / Oral interview:
  1. Keigo (Sonkeigo / Kenjougo / Teineigo)
  2. Compound Verbs (複合動詞)
  3. Functional Conjunctions of Contrast & Cause (対比・接続詞)
  4. Modality & Inference (モダリティ・推量)
Strictly <= 200 lines invariant.
"""

from typing import Any, Dict, Optional, Tuple

CLUSTER_KEIGO = "Cluster 1: Keigo (敬語)"
CLUSTER_COMPOUND = "Cluster 2: Verbi Composti (複合動詞)"
CLUSTER_CONTRAST = "Cluster 3: Connettivi di Contrasto (対比・接続詞)"
CLUSTER_MODALITY = "Cluster 4: Modalità & Inferenza (モダリティ・推量)"

CLUSTER_RANKS = {
    CLUSTER_KEIGO: 1,
    CLUSTER_COMPOUND: 2,
    CLUSTER_CONTRAST: 3,
    CLUSTER_MODALITY: 4,
}

CLUSTER_DESCRIPTIONS = {
    CLUSTER_KEIGO: "Priorità MEXT: Indispensabile per Parte B (Quesiti 9-10) e colloquio orale con la commissione.",
    CLUSTER_COMPOUND: "Priorità MEXT: Fondamentale per Parte B (verbi a reggenza sintattica complessa).",
    CLUSTER_CONTRAST: "Priorità MEXT: Chiave per la comprensione del testo saggistico e disgiunzioni argomentative.",
    CLUSTER_MODALITY: "Priorità MEXT: Costrutti di deduzione e sfumatura soggettiva essenziali per Parte B e C.",
}


def classify_mext_cluster(g: Dict[str, Any]) -> Optional[str]:
    """Identifies if a grammar point belongs to one of the 4 MEXT high-frequency clusters."""
    t = g.get("title", "")
    all_t = f"{t} {g.get('meaning', '')} {g.get('structure', '')}".lower()

    # 1. Keigo
    keigo_keywords = [
        "keigo", "honorific", "humble", "敬語", "尊敬", "謙譲",
        "お～になる", "お～する", "お〜する", "いらっしゃる", "おいで",
        "おっしゃる", "なさる", "召し上がる", "ご覧になる", "参る",
        "申す", "存じる", "拝見", "伺う", "いただく", "でございます", "ございます"
    ]
    if any(k in all_t for k in keigo_keywords):
        return CLUSTER_KEIGO

    # 2. Compound Verbs
    v_compounds = ["切る", "込む", "抜く", "通す", "止む", "終える", "だす", "つづける", "なおす"]
    if any(k in t for k in v_compounds) or "compound verb" in all_t:
        return CLUSTER_COMPOUND

    # 3. Conjunctions / Contrast
    contrast_keywords = [
        "比べて", "反面", "一方", "にもかかわらず", "からといって", "わりに",
        "にしては", "に対して", "に関して", "にとって", "向け", "向き",
        "うちに", "たびに", "ついでに", "どころか", "反して", "反する"
    ]
    if any(k in t for k in contrast_keywords):
        return CLUSTER_CONTRAST

    # 4. Modality / Inference
    modality_keywords = [
        "わけ", "はず", "に違いない", "かもしれない", "おそれがある",
        "かねない", "に決まっている", "にすぎない", "ざるを得ない",
        "っこない", "に相違ない", "ようがない", "得ない"
    ]
    if any(k in t for k in modality_keywords):
        return CLUSTER_MODALITY

    return None


def grammar_sort_key(g: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """
    Sorting order:
      Tier 1: N4 unstudied lessons (September sprint to close N4).
              Sub-ordered: High-yield clusters first, then canonical ID.
      Tier 2: N3 & N2 High-Yield MEXT Clusters (October - December surgery).
              Sub-ordered by Cluster 1 -> 2 -> 3 -> 4, then N3 before N2, then ID.
      Tier 3: Remaining N3 points by canonical ID.
      Tier 4: Remaining N2 points by canonical ID.
      Tier 5: N1 / Hyōgai points.
    """
    lvl = g.get("level", "N1")
    cluster = classify_mext_cluster(g)
    c_rank = CLUSTER_RANKS.get(cluster, 9)
    gid = int(g.get("id", 0))

    if lvl == "N4":
        return (1, c_rank, 0, gid)
    if lvl in ("N3", "N2") and cluster:
        lvl_weight = 1 if lvl == "N3" else 2
        return (2, c_rank, lvl_weight, gid)
    if lvl == "N3":
        return (3, 9, 0, gid)
    if lvl == "N2":
        return (4, 9, 0, gid)
    if lvl == "N1":
        return (5, 9, 0, gid)
    return (6, 9, 0, gid)
