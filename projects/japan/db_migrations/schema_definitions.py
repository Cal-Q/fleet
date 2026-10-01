"""DDL schema definitions for unified SQLite tables."""

from __future__ import annotations

import sqlite3


def setup_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS kanji_catalog (
            id INTEGER PRIMARY KEY,
            kanji TEXT UNIQUE NOT NULL,
            keyword TEXT NOT NULL,
            jlpt_level TEXT NOT NULL,
            on_reading TEXT,
            kun_reading TEXT,
            main_on_reading TEXT,
            diagram TEXT,
            image TEXT,
            in_anki INTEGER DEFAULT 0,
            is_study_target INTEGER DEFAULT 0,
            status TEXT DEFAULT 'unstudied',
            reps INTEGER DEFAULT 0,
            last_studied_at INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS ix_kanji_catalog_char ON kanji_catalog(kanji);
        CREATE INDEX IF NOT EXISTS ix_kanji_catalog_in_anki ON kanji_catalog(in_anki);
        CREATE INDEX IF NOT EXISTS ix_kanji_catalog_target ON kanji_catalog(is_study_target, status);
        CREATE INDEX IF NOT EXISTS ix_kanji_catalog_level ON kanji_catalog(jlpt_level);

        CREATE TABLE IF NOT EXISTS bunpro_grammar_points (
            id INTEGER PRIMARY KEY,
            level TEXT NOT NULL,
            title TEXT NOT NULL,
            meaning TEXT,
            category TEXT,
            url TEXT,
            in_anki INTEGER DEFAULT 0,
            is_study_target INTEGER DEFAULT 1,
            status TEXT DEFAULT 'locked',
            matched_sentences INTEGER DEFAULT 0,
            total_sentences INTEGER DEFAULT 0,
            studied_at INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS ix_grammar_points_in_anki ON bunpro_grammar_points(in_anki);
        CREATE INDEX IF NOT EXISTS ix_grammar_points_target ON bunpro_grammar_points(is_study_target, status);
        CREATE INDEX IF NOT EXISTS ix_grammar_points_level ON bunpro_grammar_points(level);

        CREATE TABLE IF NOT EXISTS jlpt_vocab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vocab_id TEXT,
            level TEXT NOT NULL,
            word TEXT NOT NULL,
            reading TEXT NOT NULL,
            raw TEXT,
            in_anki INTEGER DEFAULT 0,
            is_study_target INTEGER DEFAULT 1,
            status TEXT DEFAULT 'unstudied',
            reps INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS ix_jlpt_vocab_in_anki ON jlpt_vocab(in_anki);
        CREATE INDEX IF NOT EXISTS ix_jlpt_vocab_target ON jlpt_vocab(is_study_target, status);
        CREATE INDEX IF NOT EXISTS ix_jlpt_vocab_word ON jlpt_vocab(word, reading);

        CREATE TABLE IF NOT EXISTS bunpro_grammar_details (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            meaning TEXT,
            level TEXT,
            structure TEXT,
            caution TEXT,
            nuance TEXT,
            register TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_grammar_details_title ON bunpro_grammar_details(title);
        CREATE INDEX IF NOT EXISTS ix_grammar_details_level ON bunpro_grammar_details(level);

        CREATE TABLE IF NOT EXISTS bunpro_grammar_sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grammar_id INTEGER NOT NULL,
            japanese TEXT NOT NULL,
            english TEXT NOT NULL,
            clean_jp TEXT,
            clean_en TEXT,
            audio_url TEXT
        );
        CREATE TABLE IF NOT EXISTS source_english_to_kana (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english TEXT NOT NULL,
            kana TEXT NOT NULL,
            in_anki INTEGER DEFAULT 0,
            is_study_target INTEGER DEFAULT 1,
            status TEXT DEFAULT 'studying',
            reps INTEGER DEFAULT 0,
            last_studied_at INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS ix_source_eng_kana ON source_english_to_kana(kana);
        """
    )
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(source_english_to_kana)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if existing_cols:
        for col, col_type in [
            ("in_anki", "INTEGER DEFAULT 0"),
            ("is_study_target", "INTEGER DEFAULT 1"),
            ("status", "TEXT DEFAULT 'studying'"),
            ("reps", "INTEGER DEFAULT 0"),
            ("last_studied_at", "INTEGER DEFAULT 0"),
        ]:
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE source_english_to_kana ADD COLUMN {col} {col_type}")
