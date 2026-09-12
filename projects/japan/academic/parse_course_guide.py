#!/usr/bin/env python3
"""
Accurate Parser for MEXT Japanese Studies Course Guide Index PDF using pypdf.
Extracts all 70 participating Japanese universities into structured JSON.
"""

import os
import re
import json
import pypdf

PDF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "applications", "2026_Course_Guide_Index.pdf")
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "applications", "universities_database.json")


def parse_index():
    reader = pypdf.PdfReader(PDF_PATH)
    full_text = "\n".join([page.extract_text() for page in reader.pages[1:]])  # skip title page
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    # Pattern for start line: e.g. "1 北海道大学"
    start_pattern = re.compile(r"^(\d+)\s+([\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf]+.*)$")
    # Pattern for end line: e.g. "... ・・・・・ 1 (a)(b)"
    end_pattern = re.compile(r"(.*?)\s+・+\s+(\d+)\s+(\([ab\(\)]+\))$")

    universities = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m_start = start_pattern.match(line)
        if m_start:
            uni_id = int(m_start.group(1))
            name_ja = m_start.group(2).strip()
            
            # Next line usually English name
            name_en = ""
            if i + 1 < len(lines):
                name_en = lines[i + 1].strip()
            
            # Next line usually Japanese location
            loc_ja = ""
            if i + 2 < len(lines):
                loc_ja = lines[i + 2].strip()

            # Next line usually English location with dots, page, and course type
            m_end = None
            adv = 3
            while adv <= 5 and (i + adv) < len(lines):
                check_line = lines[i + adv]
                m_check = end_pattern.search(check_line)
                if m_check:
                    m_end = m_check
                    break
                adv += 1

            if m_end:
                loc_en = m_end.group(1).strip()
                page = int(m_end.group(2))
                raw_type = m_end.group(3)
                course_types = []
                if "(a)" in raw_type:
                    course_types.append("a")
                if "(b)" in raw_type:
                    course_types.append("b")

                category = "National University (国立大学)"
                if uni_id == 55:
                    category = "Public University (公立大学)"
                elif uni_id >= 56:
                    category = "Private University (私立大学)"

                # Regions
                region = "Other"
                loc_lower = loc_en.lower()
                if "tokyo" in loc_lower or "saitama" in loc_lower or "chiba" in loc_lower or "kanagawa" in loc_lower or "yokohama" in loc_lower:
                    region = "Kanto (Tokyo Area)"
                elif "kyoto" in loc_lower or "osaka" in loc_lower or "kobe" in loc_lower or "hyogo" in loc_lower or "nara" in loc_lower:
                    region = "Kansai (Kyoto/Osaka Area)"
                elif "hokkaido" in loc_lower or "sapporo" in loc_lower:
                    region = "Hokkaido"
                elif "sendai" in loc_lower or "miyagi" in loc_lower or "aomori" in loc_lower or "iwate" in loc_lower or "akita" in loc_lower or "yamagata" in loc_lower or "fukushima" in loc_lower:
                    region = "Tohoku"
                elif "fukuoka" in loc_lower or "kyushu" in loc_lower or "nagasaki" in loc_lower or "kumamoto" in loc_lower or "kagoshima" in loc_lower:
                    region = "Kyushu"
                elif "nagoya" in loc_lower or "aichi" in loc_lower or "shizuoka" in loc_lower:
                    region = "Chubu / Tokai"
                elif "hiroshima" in loc_lower or "okayama" in loc_lower:
                    region = "Chugoku"

                universities.append({
                    "id": uni_id,
                    "name_ja": name_ja,
                    "name_en": name_en,
                    "location_ja": loc_ja,
                    "location_en": loc_en,
                    "region": region,
                    "guide_page": page,
                    "course_types": course_types,
                    "course_types_str": " & ".join([f"Type ({t})" for t in course_types]),
                    "focus": "Culture, Affairs & History" if course_types == ["a"] else ("Language Proficiency" if course_types == ["b"] else "Both Language & Culture/History"),
                    "category": category
                })
                i += adv + 1
                continue
        i += 1

    # Remove duplicates and sort by ID
    unique_unis = {u["id"]: u for u in universities}.values()
    sorted_unis = sorted(unique_unis, key=lambda x: x["id"])
    return sorted_unis


def main():
    unis = parse_index()
    print(f"Extracted {len(unis)} universities from {PDF_PATH}")
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(unis, f, indent=2, ensure_ascii=False)
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
