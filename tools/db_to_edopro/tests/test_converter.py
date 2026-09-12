"""Automated unit tests for DB to EDOPro converter."""

import json
import os
import struct
import tempfile
import unittest

from tools.db_to_edopro.card_mapper import CardMapper
from tools.db_to_edopro.db_parser import DBLoader
from tools.db_to_edopro.models import DeckData, YrpMeta
from tools.db_to_edopro.translator import ReplayTranslator
from tools.db_to_edopro.yrp_writer import HEADER_MAGIC, YrpWriter
from tools.db_to_edopro.cli import convert_file


class TestDBToEDOPro(unittest.TestCase):

    def test_card_mapper_resolution(self):
        mapper = CardMapper()
        # Direct name lookup
        self.assertEqual(mapper.resolve("Deep Sea Diva"), 40640057)
        self.assertEqual(mapper.resolve("Heavy Storm"), 19613556)
        # Dict with serial_number
        c_dict = {"name": "Custom Card", "serial_number": "72302403"}
        self.assertEqual(mapper.resolve(c_dict), 72302403)

    def test_yrp_writer_structure(self):
        meta = YrpMeta(
            p1_name="Drayz",
            p1_deck=DeckData(main=[40640057, 72302403], extra=[44508094]),
            p2_name="AlexDyManss",
            p2_deck=DeckData(main=[26202165, 21502796], extra=[]),
            data=b"\x04\x00\x00\x00\x00",
        )
        packed = YrpWriter.pack(meta)
        magic, ver, flag, seed, datasize = YrpWriter.unpack_header(packed)

        self.assertEqual(magic, HEADER_MAGIC)
        self.assertEqual(ver, 0x1360)
        self.assertEqual(flag, 0x10)
        self.assertGreater(len(packed), 32)

    def test_end_to_end_conversion(self):
        sample_db_json = {
            "id": 999999,
            "format": "edison",
            "rated": 1,
            "player1": {
                "username": "EdisonPro1",
                "rating": 1640,
                "main": [40640057, 19613556, 44095762],
                "extra": [44508094],
            },
            "player2": {
                "username": "EdisonPro2",
                "rating": 1615,
                "main": [26202165, 21502796],
                "extra": [],
            },
            "plays": [
                {"play": "Pick first", "seconds": 2},
                {"play": "Start turn", "username": "EdisonPro1", "seconds": 5},
                {
                    "play": "Normal Summon",
                    "username": "EdisonPro1",
                    "seconds": 10,
                    "card": {"name": "Deep Sea Diva", "serial_number": "40640057"},
                },
                {
                    "play": "Set S/T",
                    "username": "EdisonPro1",
                    "seconds": 15,
                    "card": {"name": "Mirror Force", "serial_number": "44095762"},
                },
                {"play": "To End Phase", "username": "EdisonPro1", "seconds": 20},
            ],
        }

        loader = DBLoader()
        games = loader.parse(sample_db_json)
        self.assertEqual(len(games), 1)

        g = games[0]
        self.assertEqual(g.player1.username, "EdisonPro1")
        self.assertEqual(g.player1.rating, 1640)
        self.assertEqual(len(g.actions), 5)

        translator = ReplayTranslator(g)
        yrp_meta = translator.convert_to_yrp()
        packed_yrp = YrpWriter.pack(yrp_meta)

        self.assertTrue(packed_yrp.startswith(b"\x79\x72\x70\x31"))
        self.assertGreater(len(yrp_meta.data), 0)

        # Test CLI conversion to disk
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as json_f:
            json.dump(sample_db_json, json_f)
            json_path = json_f.name

        out_yrp = json_path + ".yrp"
        try:
            summary = convert_file(json_path, out_yrp, game_num=1)
            self.assertIn("Converted Game 1", summary)
            self.assertTrue(os.path.exists(out_yrp))
            self.assertGreater(os.path.getsize(out_yrp), 50)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)
            if os.path.exists(out_yrp):
                os.remove(out_yrp)


if __name__ == "__main__":
    unittest.main()
