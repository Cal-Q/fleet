"""Deck update pipeline: regenerates Writing Practice and Kanji To Kana."""

from __future__ import annotations

import os

from .anki_deck_manager import AnkiDeckManager
from .anki_direct_writer import sync_deck_sql, sync_decks_batch
from .dictionary_explorer import DictionaryExplorer
from .k_dictionary import KDictionary
from .kanji_merge_manager import get_all_studied_kanji, get_kanji_images
from .models import AddOrUpdateInfo
from .pipeline_helpers import (
    dict_add,
    distinct,
    generate_partial_kanji_cached,
    group_by,
    MixedKanji,
)
from .vocab_resolver_cache import get_or_resolve_vocab


def get_decks(
    deck_manager: AnkiDeckManager, dictionary_explorer: DictionaryExplorer
) -> dict[str, list[AddOrUpdateInfo]]:
    studied_kanji = get_all_studied_kanji(deck_manager)
    conn = dictionary_explorer._conn
    kanji_images = get_kanji_images(conn)

    source_vocab = dictionary_explorer.get_source_english_to_kana()
    all_top_results = get_or_resolve_vocab(conn, deck_manager, dictionary_explorer, source_vocab)

    existing_combos: set[str] = set()
    mixed_kanjis: list[MixedKanji] = []

    for item in all_top_results:
        valid_mixed: list[str] = []
        has_alt = False
        kana = item["research_kana"]
        furigana_map = item.get("furigana", {})

        for kanji_word in item["kanji_words"]:
            if any(not deck_manager.is_allowed_character(c) for c in kanji_word):
                continue

            segs = furigana_map.get(kanji_word)
            mixed = generate_partial_kanji_cached(
                deck_manager, kanji_word, kana, studied_kanji, segs
            )
            if any(deck_manager.is_allowed_kanji_character(c) for c in mixed):
                has_alt = True
                valid_mixed.append(mixed)

        if not has_alt:
            valid_mixed.append(kana)

        for eng in item["senses"]:
            for mixed in valid_mixed:
                key = f"{eng}|{kana}|{mixed}"
                if key not in existing_combos:
                    existing_combos.add(key)
                    mixed_kanjis.append(MixedKanji(english=eng, kana=kana, kanji=mixed))

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

    # Kanji To Kana: 1 card per Kanji form + attach Kodansha image if single kanji
    kanji_combined = KDictionary()
    for kana, items in group_by(mixed_kanjis, lambda m: m.kana):
        for kanji, kanji_group in group_by(items, lambda m: m.kanji):
            english_meanings = distinct(m.english for m in kanji_group)
            bulleted_english = "<br>".join(f"- {e}" for e in english_meanings)
            kanji_combined.add_combination(kanji, f"{kana}<br>{bulleted_english}")

    kanji_to_kana = kanji_combined.get_add_or_update_info("Form", "Meaning")
    for item in kanji_to_kana:
        form = item.fields_and_values.get("Form", "")
        if len(form) == 1 and form in kanji_images:
            item.fields_and_values["Image"] = kanji_images[form]
        else:
            item.fields_and_values["Image"] = ""

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
    }


def execute_updates(collection_path: str, update_info: dict[str, list[AddOrUpdateInfo]]) -> None:
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
            ),
        ],
    )

