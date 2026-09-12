"""Encodes and decodes EDOPro / YGOPro binary .yrp replay files."""

import struct
import time
from typing import List, Tuple
from .models import DeckData, YrpMeta

HEADER_MAGIC = 0x31707279  # 'yrp1'
DEFAULT_VERSION = 0x1360   # Standard YGOPro version
HEADER_STRUCT = "<6I8s"    # id, version, flag, seed, datasize, start_time, props[8]
CONFIG_STRUCT = "<3iI"     # start_lp, start_hand, draw_count, duel_flag


class YrpWriter:
    """Serializes metadata and response bytes into YGOPro/EDOPro .yrp binary format."""

    @staticmethod
    def pack(meta: YrpMeta) -> bytes:
        """Serializes a YrpMeta container into a complete .yrp binary file."""
        # 1. Player names (UTF-16LE, 40 bytes each)
        p1_name_bytes = YrpWriter._pack_name(meta.p1_name)
        p2_name_bytes = YrpWriter._pack_name(meta.p2_name)

        # 2. Duel config block (16 bytes: lp, hand, draw, flag)
        config_bytes = struct.pack(
            CONFIG_STRUCT,
            meta.start_lp,
            meta.start_hand,
            meta.draw_count,
            meta.opt,
        )

        # 3. Main & Extra decks
        p1_deck_bytes = YrpWriter._pack_deck(meta.p1_deck)
        p2_deck_bytes = YrpWriter._pack_deck(meta.p2_deck)

        # 4. Action response payload
        payload = p1_name_bytes + p2_name_bytes + config_bytes + p1_deck_bytes + p2_deck_bytes + meta.data

        # 5. Header (32 bytes)
        start_time = meta.start_time if getattr(meta, "start_time", 0) > 0 else int(time.time())
        datasize = 0  # 0 for uncompressed replays

        header_bytes = struct.pack(
            HEADER_STRUCT,
            meta.replay_id,
            meta.version,
            meta.flag,
            meta.seed,
            datasize,
            start_time,
            b"\x00" * 8,
        )

        return header_bytes + payload

    @staticmethod
    def _pack_name(name: str) -> bytes:
        """Encodes player name into exactly 20 uint16 chars (40 bytes) UTF-16LE."""
        encoded = name.encode("utf-16-le")[:38]
        return encoded + b"\x00" * (40 - len(encoded))

    @staticmethod
    def _pack_deck(deck: DeckData) -> bytes:
        """Encodes main and extra deck cards."""
        main_cards = [int(c) for c in deck.main if c > 0]
        extra_cards = [int(c) for c in deck.extra if c > 0]
        m_bytes = struct.pack(f"<I{len(main_cards)}I", len(main_cards), *main_cards)
        e_bytes = struct.pack(f"<I{len(extra_cards)}I", len(extra_cards), *extra_cards)
        return m_bytes + e_bytes

    @staticmethod
    def unpack_header(raw: bytes) -> Tuple[int, int, int, int, int]:
        """Reads header fields: (magic, version, flag, seed, datasize)."""
        if len(raw) < 32:
            raise ValueError(f"Replay file too small ({len(raw)} bytes), expected >= 32")
        magic, ver, flag, seed, datasize, _start_time, _props = struct.unpack(HEADER_STRUCT, raw[:32])
        return magic, ver, flag, seed, datasize

    @staticmethod
    def encode_response_packet(response_bytes: bytes) -> bytes:
        """Prefixes a player response with 1-byte length for .yrp action stream."""
        length = len(response_bytes)
        if length > 255:
            raise ValueError(f"Response packet exceeds 255 bytes limit: {length}")
        return struct.pack("B", length) + response_bytes
