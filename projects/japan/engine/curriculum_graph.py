#!/usr/bin/env python3
"""
engine/curriculum_graph.py — Topological Curriculum & Grammar Cluster Graph
Extracts, orders, and clusters unstudied grammar points (N4, N3, N2) into coherent batches.
Strictly <= 200 lines invariant.
"""

import json
import os
from typing import Any, Dict, List

BASE_DIR = "/opt/japan"
GRAMMAR_FILE = os.path.join(BASE_DIR, "japanese", "grammar_progress.json")
POINTS_FILE = os.path.join(BASE_DIR, "japanese", "bunpro_grammar_points.json")


def load_json_safe(path: str, default: Any = None) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def get_unstudied_by_level() -> Dict[str, List[Dict[str, Any]]]:
    gp = load_json_safe(GRAMMAR_FILE, {})
    unstudied = gp.get("unstudied_by_level", {})
    return {
        "N4": unstudied.get("N4", []),
        "N3": unstudied.get("N3", []),
        "N2": unstudied.get("N2", []),
        "N1": unstudied.get("N1", []),
    }


def cluster_n4_points(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Orders N4 unstudied points so related grammatical structures are studied together."""
    def n4_sort_key(p: Dict[str, Any]) -> int:
        title = p.get("title", "")
        # Aspectual structures (tokoro, bakari, nagara)
        if any(w in title for w in ["ところ", "ばかり", "ながら", "ている"]):
            return 10
        # Modals of obligation and permission (nakereba, nakutemo, te mo ii)
        if any(w in title for w in ["なければ", "なくても", "てはいけない", "てもいい", "べき"]):
            return 20
        # Desire, intent, plan (tsumori, yotei, hoshii, tagaru)
        if any(w in title for w in ["つもり", "よてい", "ほしい", "たがる", "ようとおもう"]):
            return 30
        # Conditionals and reasons (tara, nara, ba, node, noni)
        if any(w in title for w in ["たら", "なら", "ば", "ので", "のに", "し"]):
            return 40
        # Passives and Causatives (rareru, saseru)
        if any(w in title for w in ["られる", "させる"]):
            return 50
        # Comparison and questions (yori, hou ga, dochira, ka dou ka)
        if any(w in title for w in ["より", "ほうが", "どちら", "かとうか", "かい"]):
            return 60
        # Default by ID
        return 100 + p.get("id", 0)

    return sorted(points, key=n4_sort_key)


def cluster_n3_points(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Orders N3 points into high-yield clusters for MEXT Part B."""
    def n3_sort_key(p: Dict[str, Any]) -> int:
        title = p.get("title", "")
        # High-yield Part B connectors: ni shite wa, hanmen, ni suginai, ni chigainai
        if any(w in title for w in ["にしては", "反面", "にすぎない", "に相違ない", "にちがいない", "わけ"]):
            return 10
        # Causative-passive and compound forms
        if any(w in title for w in ["させられる", "切る", "直す", "出す", "込む", "抜く"]):
            return 20
        # Formal speech & Keigo (Sonkeigo/Kenjougo expressions)
        if any(w in title for w in ["お～になる", "お～する", "ご～", "いただく", "くださる", "参る"]):
            return 30
        # Complex conditionals and concession (tatoe, mono nara, ba koso)
        if any(w in title for w in ["たとえ", "ものなら", "ばこそ", "わりに", "くせに"]):
            return 40
        # Temporal and situational (sai, totan, tabi ni, uchi ni)
        if any(w in title for w in ["際", "とたん", "たびに", "うちに", "最中"]):
            return 50
        return 100 + p.get("id", 0)

    return sorted(points, key=n3_sort_key)


def get_curriculum_stream() -> Dict[str, List[Dict[str, Any]]]:
    raw = get_unstudied_by_level()
    n4_ordered = cluster_n4_points(raw["N4"])
    n3_ordered = cluster_n3_points(raw["N3"])
    n2_ordered = sorted(raw["N2"], key=lambda p: p.get("id", 0))

    return {
        "N4": n4_ordered,
        "N3": n3_ordered,
        "N2": n2_ordered,
        "totals": {
            "N4": len(n4_ordered),
            "N3": len(n3_ordered),
            "N2": len(n2_ordered),
            "total_unstudied": len(n4_ordered) + len(n3_ordered) + len(n2_ordered),
        }
    }


if __name__ == "__main__":
    stream = get_curriculum_stream()
    print("Curriculum stream extracted:")
    print(f"  N4: {stream['totals']['N4']} points")
    print(f"  N3: {stream['totals']['N3']} points")
    print(f"  N2: {stream['totals']['N2']} points")
    print(f"  Top 3 N4 ordered: {[p['title'] for p in stream['N4'][:3]]}")
    print(f"  Top 3 N3 ordered: {[p['title'] for p in stream['N3'][:3]]}")
