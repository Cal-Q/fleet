"""Resolves card names and DB card IDs to official Konami passcodes."""

from typing import Any, Dict, Optional

# Well-known staple passcodes for Edison format fallbacks
KNOWN_PASSCODES: Dict[str, int] = {
    "Deep Sea Diva": 40640057,
    "Spined Gillman": 72302403,
    "Heavy Storm": 19613556,
    "Mystical Space Typhoon": 5318639,
    "Caius the Shadow Monarch": 4929256,
    "Brain Control": 87910978,
    "Mirror Force": 44095762,
    "Solemn Judgment": 41420027,
    "Torrential Tribute": 53582587,
    "Sangan": 26202165,
    "Ryko, Lightsworn Hunter": 21502796,
    "Gorz the Emissary of Darkness": 44330098,
    "Stardust Dragon": 44508094,
    "Goyo Guardian": 73891874,
    "Ally of Justice Catastor": 26593852,
    "Black Rose Dragon": 73580471,
    "Brionac, Dragon of the Ice Barrier": 50321796,
    "Substitoad": 40418351,
    "Ronintoadin": 9126351,
    "Dupe Frog": 46239604,
    "Swap Frog": 91034681,
    "Treeborn Frog": 12538374,
    "Pot of Avarice": 67169062,
    "Dark Armed Dragon": 65192027,
    "Plaguespreader Zombie": 33420078,
    "Mezuki": 92826944,
    "Cyber Dragon": 70095154,
    "Blackwing - Gale the Whirlwind": 34834866,
    "Blackwing - Bora the Spear": 49003716,
    "Blackwing - Sirocco the Dawn": 75498415,
    "Blackwing - Blizzard the Far North": 22835145,
    "Blackwing - Kalut the Moon Shadow": 8529136,
    "Blackwing Armed Wing": 7691398,
    "Blackwing Armor Master": 69031175,
    "Icarus Attack": 53567095,
    "Royal Oppression": 93016201,
    "Bottomless Trap Hole": 29401950,
    "Dimensional Prison": 70342110,
    "Book of Moon": 14087893,
    "Smashing Ground": 97169186,
    "Foolish Burial": 81439173,
    "Allure of Darkness": 14757227,
    "Destiny Hero - Malicious": 9411399,
    "Elemental Hero Stratos": 40044918,
    "Miracle Fusion": 45906428,
    "Elemental Hero Absolute Zero": 40854824,
    "Colossal Fighter": 49826746,
    "Thought Ruler Archfiend": 82044279,
    "Armory Arm": 63468625,
}

import os
import sqlite3

NAME_OVERRIDES: Dict[str, str] = {
    "Mystical Space Typhoon": "Mystical Space Typhoon",
    "MST": "Mystical Space Typhoon",
}


class CardMapper:
    """Provides passcode lookup with caching and cards.cdb fallback."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._cache: Dict[str, int] = dict(KNOWN_PASSCODES)
        if not db_path:
            cand = os.path.join(os.path.dirname(__file__), "cards.cdb")
            if os.path.exists(cand):
                db_path = cand
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        if self.db_path and os.path.exists(self.db_path):
            try:
                self._conn = sqlite3.connect(self.db_path)
            except Exception:
                self._conn = None

    def resolve(self, card_obj: Any) -> int:
        """Extracts or resolves a card passcode from DB card representation."""
        if not card_obj:
            return 0

        if isinstance(card_obj, int):
            return card_obj if card_obj > 1000 else self._lookup_id(card_obj)

        if isinstance(card_obj, dict):
            serial = card_obj.get("serial_number")
            if serial and str(serial).strip().isdigit():
                val = int(str(serial).strip())
                if val > 0:
                    name = card_obj.get("name")
                    if name:
                        self._cache[name] = val
                    return val

            for key in ("passcode", "code", "id"):
                if key in card_obj and str(card_obj[key]).isdigit():
                    val = int(card_obj[key])
                    if val > 1000:
                        return val

            name = card_obj.get("name")
            if name:
                return self.resolve_by_name(name)

        if isinstance(card_obj, str):
            return self.resolve_by_name(card_obj)

        return 0

    def resolve_by_name(self, name: str) -> int:
        """Looks up passcode by card name string."""
        clean = name.strip().strip('"')
        clean = NAME_OVERRIDES.get(clean, clean)
        if clean in self._cache:
            return self._cache[clean]

        lower = clean.lower()
        for k, v in self._cache.items():
            if k.lower() == lower:
                return v

        if self._conn:
            try:
                cur = self._conn.cursor()
                cur.execute("SELECT id FROM texts WHERE name = ? COLLATE NOCASE LIMIT 1", (clean,))
                row = cur.fetchone()
                if row and row[0] > 0:
                    self._cache[clean] = row[0]
                    return row[0]
            except Exception:
                pass

        return 0

    def register(self, name: str, passcode: int) -> None:
        """Manually registers a card passcode mapping."""
        if name and passcode > 0:
            self._cache[name.strip()] = passcode

    def _lookup_id(self, internal_id: int) -> int:
        """Placeholder for internal DB card id to passcode lookup."""
        return internal_id
