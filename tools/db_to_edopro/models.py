"""Data models for DuelingBook to EDOPro replay converter."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

# ocgcore Duel Option Flags
DUEL_OBSOLETE_RULING = 0x08
DUEL_PSEUDO_SHUFFLE = 0x10
MASTER_RULE_1 = 0x00010000
DEFAULT_EDISON_OPT = MASTER_RULE_1 | DUEL_PSEUDO_SHUFFLE | DUEL_OBSOLETE_RULING


class ActionKind(Enum):
    """Normalized player action categories."""
    DRAW = "DRAW"
    SUMMON = "SUMMON"
    SPECIAL_SUMMON = "SPECIAL_SUMMON"
    SET_MONSTER = "SET_MONSTER"
    SET_ST = "SET_ST"
    ACTIVATE = "ACTIVATE"
    ATTACK = "ATTACK"
    TO_GRAVE = "TO_GRAVE"
    BANISH = "BANISH"
    DAMAGE = "DAMAGE"
    TARGET = "TARGET"
    PHASE = "PHASE"
    SURRENDER = "SURRENDER"
    UNKNOWN = "UNKNOWN"


@dataclass
class CardData:
    name: str
    card_id: int = 0
    passcode: int = 0
    card_type: str = ""


@dataclass
class DeckData:
    main: List[int] = field(default_factory=list)
    extra: List[int] = field(default_factory=list)
    side: List[int] = field(default_factory=list)


@dataclass
class PlayerState:
    username: str
    rating: int = 0
    deck: DeckData = field(default_factory=DeckData)
    lp: int = 8000


@dataclass
class ParsedAction:
    kind: ActionKind
    player: int
    card_name: str = ""
    passcode: int = 0
    zone: str = ""
    value: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class ReplayGame:
    game_number: int
    player1: PlayerState
    player2: PlayerState
    actions: List[ParsedAction] = field(default_factory=list)
    winner: Optional[str] = None


@dataclass
class YrpMeta:
    """EDOPro / YGOPro replay file metadata."""
    replay_id: int = 0x31707279  # 'yrp1'
    version: int = 0x1360
    flag: int = 0x10             # REPLAY_UNIFORM = 0x10
    seed: int = 0
    start_lp: int = 8000
    start_hand: int = 5
    draw_count: int = 1
    opt: int = DEFAULT_EDISON_OPT
    p1_name: str = "Player 1"
    p1_deck: DeckData = field(default_factory=DeckData)
    p2_name: str = "Player 2"
    p2_deck: DeckData = field(default_factory=DeckData)
    start_time: int = 0
    data: bytes = b""
