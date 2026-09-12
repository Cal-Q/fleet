"""Fuzzy and cross-reference search matcher for JMdict entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .jmdict_models import CleanJMdictEntry, ReadingElement, Sense

if TYPE_CHECKING:
    from .anki_deck_manager import AnkiDeckManager
    from .dictionary_explorer import DictionaryExplorer


@dataclass(slots=True)
class JMdictSearchResult:
    research_english: str = ""
    research_kana: str = ""
    generated_from_entry: CleanJMdictEntry | None = None
    entry: CleanJMdictEntry | None = None
    found_correct: bool = False


def get_score_fast(reading_element: ReadingElement) -> int:
    score = 0
    for item in reading_element.priority:
        if item.startswith("nf"):
            try:
                number = int(item[2:])
                score += 50 - number
            except ValueError:
                pass
        elif item == "news1":
            score += 5
        elif item == "news2":
            score += 4
        elif item == "ichi1":
            score += 3
        elif item == "ichi2":
            score += 2
        elif item == "spec1":
            score += 3
        elif item == "spec2":
            score += 2
        elif item in ("gai1", "gai2"):
            score += 1
    return score


def try_search_grouped(
    explorer: DictionaryExplorer, deck_manager: AnkiDeckManager, english: str, kana: str
) -> tuple[bool, list[JMdictSearchResult]]:
    matching_entries: list[JMdictSearchResult] = []
    english_lower = english.lower()

    values = explorer.get_entries(kana)
    if not values:
        return False, matching_entries

    for value in values:
        matching_senses: list[Sense] = []
        correct_readings: list[ReadingElement] = list(value.reading_elements)

        for initial_sense in value.senses:
            if not initial_sense.has_gloss(english_lower):
                continue

            found_cross_reference = False
            another_entry_has_meaning = False

            if initial_sense.parsed_cross_references:
                for cross_reference in initial_sense.parsed_cross_references:
                    readings = cross_reference.readings
                    if not readings:
                        continue

                    candidate_entries: set[CleanJMdictEntry] | None = None
                    possible = True
                    for r in readings:
                        matches = explorer.get_entries(r)
                        if not matches:
                            possible = False
                            break

                        if candidate_entries is None:
                            candidate_entries = set(matches)
                        else:
                            candidate_entries &= set(matches)

                        if not candidate_entries:
                            possible = False
                            break

                    if not possible or candidate_entries is None:
                        continue

                    target_sense_idx = cross_reference.sense_number

                    for entry_to_check in candidate_entries:
                        if entry_to_check == value or entry_to_check.is_name_entry:
                            continue

                        check_index = (
                            target_sense_idx - 1
                            if (target_sense_idx is not None and target_sense_idx > 0)
                            else 0
                        )

                        if check_index >= len(entry_to_check.senses):
                            continue

                        if kana not in entry_to_check.readings:
                            continue

                        contains_gloss = False
                        s = entry_to_check.senses[check_index]
                        for g in s.glosses:
                            if g.text is not None and g.text.lower() == english_lower:
                                contains_gloss = True
                                break

                        if not contains_gloss:
                            continue

                        another_entry_has_meaning = True

                        for xref in s.parsed_cross_references:
                            if xref.readings and all(xr in value.readings for xr in xref.readings):
                                found_cross_reference = True
                                break

                        if found_cross_reference:
                            break
                    if found_cross_reference:
                        break

                if not found_cross_reference and another_entry_has_meaning:
                    continue

            matching_senses.append(initial_sense)
            suitable_readings: list[tuple[ReadingElement, int]] = []

            for el in correct_readings:
                is_match = False
                is_kanji = any(deck_manager.is_allowed_kanji_character(c) for c in el.reading)

                if is_kanji:
                    if not initial_sense.stagk or el.reading in initial_sense.stagk:
                        is_match = True
                else:
                    if all(deck_manager.is_allowed_character(c) for c in el.reading):
                        if not initial_sense.stagr or el.reading in initial_sense.stagr:
                            is_match = True

                if is_match:
                    suitable_readings.append((el, get_score_fast(el)))

            if suitable_readings:
                max_score = max(score for _, score in suitable_readings)
                if max_score > 0:
                    correct_readings = [el for el, score in suitable_readings if score > 0]
                else:
                    correct_readings = [el for el, _ in suitable_readings]

        if correct_readings and matching_senses:
            reading_set = {r.reading for r in correct_readings}
            matching_entries.append(
                JMdictSearchResult(
                    generated_from_entry=value,
                    entry=CleanJMdictEntry(
                        reading_elements=list(correct_readings),
                        senses=list(matching_senses),
                        readings=reading_set,
                    ),
                    research_english=english,
                    research_kana=kana,
                )
            )

    is_correct = len(matching_entries) > 0
    for item in matching_entries:
        item.found_correct = is_correct

    return is_correct, matching_entries
