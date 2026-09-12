"""Port of the clean/normalized data shapes from JMdict.cs and JMnedict.cs.

These are hydrated on demand from a SQLite index (see jmdict_index.py/dictionary_explorer.py)
rather than held all at once in memory — the original C# (and this project's first Python
pass) loaded every JMdict+JMnedict entry into RAM permanently, which is fine with .NET's
headroom but too much for this server's memory budget. `slots=True` throughout trims
per-instance overhead further (dataclasses give every instance a `__dict__` by default; slots
removes that).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Gloss:
    text: str | None = None
    language: str = "eng"


@dataclass(slots=True)
class CrossReference:
    readings: list[str] = field(default_factory=list)
    sense_number: int | None = None

    @staticmethod
    def parse(xref: str | None) -> "CrossReference | None":
        if not xref or not xref.strip():
            return None

        cr = CrossReference()
        for raw in xref.split("・"):
            token = raw.strip() if raw else ""
            if not token:
                continue

            try:
                # Only a token that's purely an integer counts as the sense number,
                # matching C#'s int.TryParse (which rejects trailing garbage).
                n = int(token)
            except ValueError:
                cr.readings.append(token)
                continue

            if cr.sense_number is None:
                cr.sense_number = n

        return cr


@dataclass(slots=True)
class Sense:
    stagk: list[str] = field(default_factory=list)
    stagr: list[str] = field(default_factory=list)
    part_of_speech: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    field_: list[str] = field(default_factory=list)
    misc: list[str] = field(default_factory=list)
    sense_info: list[str] = field(default_factory=list)
    dialects: list[str] = field(default_factory=list)
    glosses: list[Gloss] = field(default_factory=list)

    _parsed_cross_references: list[CrossReference] | None = field(default=None, repr=False, compare=False)

    def get_bonus_info(self) -> set[str]:
        return set(self.sense_info) | set(self.field_) | set(self.misc) | set(self.dialects)

    def has_gloss(self, english_lower: str) -> bool:
        return any(g.text is not None and g.text.lower() == english_lower for g in self.glosses)

    @property
    def parsed_cross_references(self) -> list[CrossReference]:
        if self._parsed_cross_references is not None:
            return self._parsed_cross_references

        parsed = []
        for xref in self.cross_references:
            cr = CrossReference.parse(xref)
            if cr is not None:
                parsed.append(cr)
        self._parsed_cross_references = parsed
        return parsed


@dataclass(slots=True)
class ReadingElement:
    reading: str
    info: list[str] = field(default_factory=list)
    priority: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FuriganaSegment:
    ruby: str
    rt: str | None = None  # None if kana only


@dataclass(slots=True, unsafe_hash=True)
class CleanJMdictEntry:
    """Equality/hash are based on `id` (the SQLite row id) only — every other field is
    `compare=False`. This replaces the old reference-equality trick (the C# CLEAN_JMdictEntry
    never overrode Equals/GetHashCode, so identity happened to double as "same entry" since
    each entry existed as exactly one shared object). Now that entries are hydrated fresh per
    query instead of shared from one big in-memory index, two hydrations of the *same*
    underlying entry must still compare equal — hence id-based equality instead of identity."""

    id: int = 0
    senses: list[Sense] = field(default_factory=list, compare=False)
    reading_elements: list[ReadingElement] = field(default_factory=list, compare=False)
    readings: set[str] = field(default_factory=set, compare=False)
    is_name_entry: bool = field(default=False, compare=False)
