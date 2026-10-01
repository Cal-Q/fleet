#!/usr/bin/env python3
"""
api/routes/anki_fsrs_routes.py — FSRS Memory Model & Recalibration Endpoints
Provides live FSRS metrics, per-deck weights, and on-demand recalibration.
Strictly <= 200 lines invariant.
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.fsrs_optimizer import load_deck_weights
from core.fsrs_daemon import load_card_states, run_daily_fsrs_recalibration

router = APIRouter(tags=["anki_fsrs"])


class FSRSRecalibratePayload(BaseModel):
    target_retention: float = 0.90
    apply_to_anki: bool = True


@router.get("/api/anki/fsrs/stats")
def get_fsrs_stats() -> Dict[str, Any]:
    try:
        deck_weights = load_deck_weights()
        card_states = load_card_states()
        total_cards = len(card_states)

        avg_s = sum(c.get("stability", 0.0) for c in card_states.values()) / max(1, total_cards)
        avg_d = sum(c.get("difficulty", 0.0) for c in card_states.values()) / max(1, total_cards)
        avg_r = sum(c.get("retrievability", 0.0) for c in card_states.values()) / max(1, total_cards)

        return {
            "status": "ok",
            "summary": {
                "total_calibrated_cards": total_cards,
                "avg_stability_days": round(avg_s, 2),
                "avg_difficulty": round(avg_d, 2),
                "avg_retrievability": round(avg_r, 4),
                "active_decks_optimized": len(deck_weights)
            },
            "decks": deck_weights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/anki/fsrs/recalibrate")
def post_fsrs_recalibrate(payload: FSRSRecalibratePayload) -> Dict[str, Any]:
    try:
        res = run_daily_fsrs_recalibration(
            target_retention=payload.target_retention,
            apply_to_anki=payload.apply_to_anki
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
