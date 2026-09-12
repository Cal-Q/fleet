"""XML parsing for JMdict_e.xml and JMnedict.xml -> CleanJMdictEntry.

Ported from the XmlSerializer-driven classes in JMdict.cs / JMnedict.cs. Both files declare
hundreds of custom entities (e.g. &v5r;) in an internal DTD subset; those are *internal*
general entities, which xml.etree.ElementTree (via expat) expands automatically with no special
configuration, unlike the XmlReaderSettings dance the C# code needed.

Streams entries with iterparse + elem.clear() so a 100k+-entry file doesn't have to sit fully
parsed in memory at once (matches the performance intent of the original code without needing a
third-party parser).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Iterator

from .jmdict_models import CleanJMdictEntry, Gloss, ReadingElement, Sense

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _text(elem: ET.Element, tag: str) -> str | None:
    child = elem.find(tag)
    return child.text if child is not None else None


def _text_list(elem: ET.Element, tag: str) -> list[str]:
    return [child.text or "" for child in elem.findall(tag)]


def _parse_reading_elements(entry: ET.Element) -> list[ReadingElement]:
    """k_ele/r_ele share the same keb/reb + *_inf/*_pri tag shape in both JMdict and JMnedict."""
    reading_elements: list[ReadingElement] = []

    for sub in entry.findall("k_ele"):
        reading = _text(sub, "keb")
        if reading is not None:
            reading_elements.append(
                ReadingElement(reading=reading, info=_text_list(sub, "ke_inf"), priority=_text_list(sub, "ke_pri"))
            )

    for sub in entry.findall("r_ele"):
        reading = _text(sub, "reb")
        if reading is not None:
            reading_elements.append(
                ReadingElement(reading=reading, info=_text_list(sub, "re_inf"), priority=_text_list(sub, "re_pri"))
            )

    return reading_elements


def _is_eligible(info: list[str]) -> bool:
    for item in info:
        if "search-only" in item or "rarely" in item or "out-dated" in item:
            return False
    return True


def _parse_gloss(elem: ET.Element) -> Gloss:
    return Gloss(text=elem.text, language=elem.get(_XML_LANG) or "eng")


def _parse_sense(elem: ET.Element) -> Sense:
    return Sense(
        stagk=_text_list(elem, "stagk"),
        stagr=_text_list(elem, "stagr"),
        part_of_speech=_text_list(elem, "pos"),
        cross_references=_text_list(elem, "xref"),
        antonyms=_text_list(elem, "ant"),
        field_=_text_list(elem, "field"),
        misc=_text_list(elem, "misc"),
        sense_info=_text_list(elem, "s_inf"),
        dialects=_text_list(elem, "dial"),
        glosses=[_parse_gloss(g) for g in elem.findall("gloss")],
    )


def iter_jmdict_entries(xml_path: str) -> Iterator[CleanJMdictEntry]:
    """Main JMdict_e.xml dictionary. Reading elements flagged search-only/rarely/out-dated are
    dropped, matching CLEAN_JMdictEntry's JMdictEntry constructor."""
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "entry":
            continue

        entry = CleanJMdictEntry(senses=[_parse_sense(s) for s in elem.findall("sense")])
        for re_ in _parse_reading_elements(elem):
            if _is_eligible(re_.info):
                entry.readings.add(re_.reading)
                entry.reading_elements.append(re_)

        yield entry
        elem.clear()


def iter_jmnedict_entries(xml_path: str) -> Iterator[CleanJMdictEntry]:
    """JMnedict.xml (names dictionary). No eligibility filtering here — the C# Name_Entry
    constructor includes every reading element unconditionally, and part-of-speech is always
    empty since names don't carry one."""
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "entry":
            continue

        senses = []
        for trans in elem.findall("trans"):
            glosses = [_parse_gloss(d) for d in trans.findall("trans_det")]
            senses.append(
                Sense(
                    part_of_speech=[],
                    cross_references=_text_list(trans, "xref"),
                    sense_info=_text_list(trans, "name_type"),
                    glosses=glosses,
                )
            )

        entry = CleanJMdictEntry(is_name_entry=True, senses=senses)
        for re_ in _parse_reading_elements(elem):
            entry.readings.add(re_.reading)
            entry.reading_elements.append(re_)

        yield entry
        elem.clear()
