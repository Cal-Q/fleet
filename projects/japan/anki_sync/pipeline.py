"""Deck update pipeline: regenerates Writing Practice and Kanji To Kana."""

from __future__ import annotations

import json
import os

from . import jmdict_index
from .anki_deck_manager import AnkiDeckManager
from .anki_direct_writer import sync_deck_sql, sync_decks_batch
from .dictionary_explorer import DictionaryExplorer
from .k_dictionary import KDictionary
from .kanji_merge_manager import get_all_studied_kanji, get_kanji_images
from .models import AddOrUpdateInfo
from .pipeline_helpers import (
    DISALLOWED_MISC_TAGS,
    MixedKanji,
    dict_add,
    distinct,
    filter_valid_reading_elements,
    generate_partial_kanji_cached,
    group_by,
    is_entry_archaic,
    resolve_all_single_kanji_meanings,
)


def get_decks(
    deck_manager: AnkiDeckManager, dictionary_explorer: DictionaryExplorer
) -> dict[str, list[AddOrUpdateInfo]]:
    conn = dictionary_explorer._conn
    cursor = conn.execute("SELECT kanji FROM kanji_catalog WHERE in_anki = 1")
    studied_kanji = {r[0] for r in cursor.fetchall()}
    kanji_images = get_kanji_images(conn)

    cursor = conn.execute("SELECT id FROM entries WHERE in_anki = 1 AND is_name_entry = 0")
    active_entry_ids = {r[0] for r in cursor.fetchall()}
    entries_map = jmdict_index.hydrate_entries(conn, active_entry_ids)

    existing_combos: set[str] = set()
    mixed_kanjis: list[MixedKanji] = []

    for eid, entry in entries_map.items():
        if is_entry_archaic(entry):
            continue

        kana_readings = [r.reading for r in entry.reading_elements if not any(deck_manager.is_allowed_kanji_character(c) for c in r.reading)]
        if not kana_readings and entry.readings:
            kana_readings = [list(entry.readings)[0]]
        if not kana_readings:
            continue
        valid_forms = filter_valid_reading_elements(entry, deck_manager) or kana_readings[:1]
        for kr in kana_readings:
            senses_formatted = []
            for sense in entry.senses:
                if (sense.stagr and kr not in sense.stagr) or any(t in DISALLOWED_MISC_TAGS for t in sense.misc):
                    continue
                gloss_texts = [g.text for g in sense.glosses if g.text]
                if not gloss_texts:
                    continue
                eng = ", ".join(gloss_texts)
                for pos in sense.part_of_speech:
                    if pos == "transitive verb": eng += " [Vt]"
                    elif pos == "intransitive verb": eng += " [Vi]"
                    elif pos == "noun or participle which takes the aux. verb suru": eng += " [Vs]"
                for bonus in sense.get_bonus_info():
                    eng += " [Ko]" if bonus == "word usually written using kana alone" else f" ({bonus})"
                senses_formatted.append(eng)
            for eng in senses_formatted:
                for form in valid_forms:
                    key = f"{eng}|{kr}|{form}"
                    if key not in existing_combos:
                        existing_combos.add(key)
                        mixed_kanjis.append(MixedKanji(english=eng, kana=kr, kanji=form))

    # Kodansha database: keyword -> studied kanji, kanji -> kodansha id
    keyword_kanji_map: dict[str, list[str]] = {}
    kanji_to_code: dict[str, int] = {}

    for kanji_id, kanji_str, keyword in dictionary_explorer.get_kodansha_kanji():
        try:
            kanji = kanji_str.strip()[0]
            dict_add(kanji_to_code, kanji, int(kanji_id))
            if kanji in studied_kanji:
                keyword_kanji_map.setdefault(keyword, []).append(kanji)
        except (IndexError, ValueError):
            pass

    # Kanji To Kana & Kanji Image Deck Meaning
    kanji_combined = KDictionary()
    for kana, items in group_by(mixed_kanjis, lambda m: m.kana):
        for kanji, kanji_group in group_by(items, lambda m: m.kanji):
            english_meanings = distinct(m.english for m in kanji_group)
            bulleted_english = "<br>".join(f"- {e}" for e in english_meanings)
            kanji_combined.add_combination(kanji, f"{kana}<br>{bulleted_english}")

    raw_kanji_to_kana = kanji_combined.get_add_or_update_info("Form", "Meaning")
    kanji_to_kana: list[AddOrUpdateInfo] = []
    kanji_image_meanings: list[AddOrUpdateInfo] = []
    single_kanji_meanings: dict[str, str] = resolve_all_single_kanji_meanings(conn, studied_kanji)
    for item in raw_kanji_to_kana:
        form = item.fields_and_values.get("Form", "")
        meaning = item.fields_and_values.get("Meaning", "")
        if len(form) == 1 and deck_manager.is_allowed_kanji_character(form):
            single_kanji_meanings[form] = meaning
            continue
        item.fields_and_values["Image"] = ""
        kanji_to_kana.append(item)

    for kanji_char in studied_kanji:
        meaning_val = single_kanji_meanings.get(kanji_char, "")
        img_val = kanji_images.get(kanji_char, "")
        kanji_image_meanings.append(
            AddOrUpdateInfo(fields_and_values={"Kanji": kanji_char, "Meaning": meaning_val, "Image": img_val})
        )

    # Writing Practice deck
    keyword_to_id: dict[str, str] = {}
    writing_practice_dict = KDictionary()

    for keyword, kanji_list in keyword_kanji_map.items():
        for kanji_str in kanji_list:
            k = kanji_str[0]
            final_keyword = keyword
            if len(kanji_list) > 1:
                others = [x for x in kanji_list if x != kanji_str]
                final_keyword = f"{keyword} (not {', '.join(others)})"

            id_ = kanji_to_code[k]
            alpha_id = (
                chr(ord("A") + id_ // 676 % 26) + chr(ord("A") + id_ // 26 % 26) + chr(ord("A") + id_ % 26)
            )
            unicode_hex = f"{ord(k):04X}"
            text = f'{k}<br><img src="0{unicode_hex}.svg">'

            writing_practice_dict.add_combination(final_keyword, text)
            dict_add(keyword_to_id, final_keyword, alpha_id)

    writing_practice = writing_practice_dict.get_add_or_update_info("Front", "Back")
    for item in writing_practice:
        kw = item.fields_and_values["Front"]
        item.fields_and_values["Order"] = keyword_to_id[kw]

    return {
        "Writing Practice": writing_practice,
        "Kanji To Kana": kanji_to_kana,
        "Kanji Image Meaning": kanji_image_meanings,
    }


def execute_updates(collection_path: str, update_info: dict[str, list[AddOrUpdateInfo]]) -> None:
    from .kanji_merge_manager import merge_vocab_srs_to_image_deck

    sync_decks_batch(
        collection_path,
        [
            (
                "[JAP]\x1f[TRAVEL]\x1fKanji - Image Deck",
                "Kanji Image Model",
                "Kanji",
                update_info.get("Kanji Image Meaning", []),
                True,
                True,
            ),
        ],
    )
    merge_vocab_srs_to_image_deck(collection_path)
    sync_decks_batch(
        collection_path,
        [
            (
                "[JAP]\x1fKanji -> Writing Practice",
                "Kanji Writing",
                "Front",
                update_info["Writing Practice"],
                True,
            ),
            (
                "[JAP]\x1f[TRAVEL]\x1fJapanese -> Phonetic + Meaning",
                "KanjiToKana",
                "Form",
                update_info["Kanji To Kana"],
                True,
                True,
                None,
            ),
        ],
    )
