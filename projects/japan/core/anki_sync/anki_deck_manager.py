import os
import sqlite3
"""Port of AnkiDeckManager.cs, minus the unused AnkiConnect plumbing (TryExecutePayload,
BackupDeck, GetDeckNames, SyncAnkiDeck) — confirmed dead code, never called by the pipeline
that used to live in Form1_Load/GetDecks/ExecuteUpdates.
"""

import enum

from . import anki_direct_reader
from .models import SOURCE_KANJI


class JapaneseCharType(enum.Enum):
    HIRAGANA = "Hiragana"
    KATAKANA = "Katakana"
    KANJI = "Kanji"
    PUNCTUATION = "Punctuation"
    NUMBER = "Number"
    OTHER = "Other"


def get_japanese_char_type(c: str) -> JapaneseCharType:
    code = ord(c)

    # Hiragana: U+3040-U+309F
    if 0x3040 <= code <= 0x309F:
        return JapaneseCharType.HIRAGANA

    # Katakana: U+30A0-U+30FF
    if 0x30A0 <= code <= 0x30FF:
        return JapaneseCharType.KATAKANA

    # Full-width Japanese numbers: U+FF10-U+FF19
    if 0xFF10 <= code <= 0xFF19:
        return JapaneseCharType.NUMBER

    # Numbers: ASCII 0-9 (and any other Unicode digit, matching char.IsDigit)
    if c.isdigit():
        return JapaneseCharType.NUMBER

    # Full-width punctuation and other symbols: U+FF00-U+FFEF
    if 0xFF00 <= code <= 0xFFEF:
        return JapaneseCharType.PUNCTUATION

    # Full-width punctuation: U+3000-U+303F
    if 0x3000 <= code <= 0x303F:
        return JapaneseCharType.PUNCTUATION

    return JapaneseCharType.OTHER


class AnkiDeckManager:
    def __init__(self, collection_path: str):
        self._collection_path = collection_path
        self._decks: dict[str, list] = {}
        self._allowed_kanji: dict[str, int] | None = None
        self.failed_characters: set[str] = set()

    def initialize(self) -> None:
        self._decks = anki_direct_reader.read_all_decks(self._collection_path)

    def try_get_deck(self, deck_name: str) -> tuple[bool, list | None]:
        cards = self._decks.get(deck_name)
        if cards is not None:
            return True, cards
        cards = self._decks.get(deck_name.replace("::", "\x1f"))
        if cards is not None:
            return True, cards
        return False, None

    def _get_allowed_kanji(self) -> dict[str, int]:
        if self._allowed_kanji is not None:
            return self._allowed_kanji

        base_project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dict_path = os.path.join(base_project_dir, "data", "dict_index.sqlite3")
        if not os.path.isfile(dict_path):
            dict_path = "/opt/japan/data/dict_index.sqlite3"
        kanjis_contained: dict[str, int] = {}
        if os.path.isfile(dict_path):
            conn = sqlite3.connect(dict_path)
            cur = conn.cursor()
            cur.execute("SELECT kanji, number FROM source_kanji_images")
            for kanji, number in cur.fetchall():
                kanjis_contained[kanji.strip()[0]] = int(number)
            conn.close()

        # Fallback to deck if database table empty
        if not kanjis_contained:
            _, kanji_deck = self.try_get_deck(SOURCE_KANJI)
            kanji_deck = kanji_deck or []
            for item in kanji_deck:
                kanjis_contained[item.note.fields["Kanji"].strip()[0]] = int(item.note.fields["Number"])

        self._allowed_kanji = kanjis_contained
        return self._allowed_kanji

    def is_allowed_kanji_character(self, kanji: str) -> bool:
        if not kanji:
            return False
        c = kanji[0]
        code = ord(c)
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0xF900 <= code <= 0xFAFF:
            return True
        return c in self._get_allowed_kanji()

    def is_allowed_non_kanji_character(self, character: str) -> bool:
        char_type = get_japanese_char_type(character)
        if char_type in (JapaneseCharType.OTHER, JapaneseCharType.NUMBER):
            return False
        return True

    def _is_allowed_character2(self, character: str) -> bool:
        if self.is_allowed_kanji_character(character):
            return True
        return self.is_allowed_non_kanji_character(character)

    def is_allowed_character(self, character: str) -> bool:
        allowed = self._is_allowed_character2(character)
        if not allowed:
            self.failed_characters.add(character)
        return allowed
