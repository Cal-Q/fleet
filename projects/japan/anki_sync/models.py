"""Shared data shapes and deck-name constants (port of AnkiDeckManager.cs's nested types)."""

from dataclasses import dataclass, field

SOURCE_KODANSHA = "[SOURCE] The Kodansha Kanji Learners Course"
SOURCE_KANJI = "[JAP]\x1f[TRAVEL]\x1fKanji - Image Deck"
SOURCE_ENGLISH_TO_KANA = "[SOURCE] English -> Kana"


@dataclass(slots=True)
class AnkiNote:
    note_id: int = 0
    fields: dict = field(default_factory=dict)


@dataclass(slots=True)
class AnkiCard:
    card_id: int = 0
    note_id: int = 0
    reps: int = 0
    note: AnkiNote = field(default_factory=AnkiNote)


@dataclass(slots=True)
class AddOrUpdateInfo:
    fields_and_values: dict
