#!/usr/bin/env python3
"""
engine/study_batch.py — Study Batch Façade
Re-exports batch executors for Kanji, Vocab, and Grammar.
Strictly <= 200 lines invariant.
"""

from engine.study_batch_kanji import add_kanji_batch
from engine.study_batch_vocab import add_vocab_batch
from engine.study_batch_grammar import add_grammar_batch

__all__ = [
    "add_kanji_batch",
    "add_vocab_batch",
    "add_grammar_batch",
]
