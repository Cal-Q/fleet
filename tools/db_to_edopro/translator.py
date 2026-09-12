"""Translates normalized DB actions into EDOPro engine response stream."""

import struct
from typing import List, Tuple
from .models import ActionKind, DeckData, ParsedAction, ReplayGame, YrpMeta, DEFAULT_EDISON_OPT
from .yrp_writer import YrpWriter

CMD_SUMMON = 0
CMD_SPECIAL_SUMMON = 1
CMD_REPOSITION = 2
CMD_SET_MONSTER = 3
CMD_SET_ST = 4
CMD_ACTIVATE = 5
CMD_TO_BATTLE = 6
CMD_TO_END = 7

BATTLE_ATTACK = 0
BATTLE_TO_M2 = 2
BATTLE_TO_END = 3


class ReplayTranslator:
    """Converts a parsed DB game into an EDOPro response stream."""

    def __init__(self, game: ReplayGame) -> None:
        self.game = game
        self.p1_deck, self.p1_hand = self._order_deck(game.player1.deck, 0)
        self.p2_deck, self.p2_hand = self._order_deck(game.player2.deck, 1)
        self.p1_field: List[int] = []
        self.p2_field: List[int] = []

    def convert_to_yrp(self, seed: int = 0) -> YrpMeta:
        """Converts the game into a YrpMeta ready for binary serialization."""
        response_bytes = bytearray()

        for action in self.game.actions:
            packets = self._translate_action(action)
            for pkt in packets:
                response_bytes.extend(YrpWriter.encode_response_packet(pkt))

        meta = YrpMeta(
            seed=seed,
            opt=DEFAULT_EDISON_OPT,
            p1_name=self.game.player1.username,
            p1_deck=self.p1_deck,
            p2_name=self.game.player2.username,
            p2_deck=self.p2_deck,
            data=bytes(response_bytes),
        )
        return meta

    def _order_deck(self, original_deck: DeckData, player_idx: int) -> Tuple[DeckData, List[int]]:
        """Reorders main deck so ocgcore pops cards in exact DB sequence."""
        played_cards: List[int] = []
        for a in self.game.actions:
            if a.player == player_idx and a.passcode > 0:
                if a.kind in (ActionKind.SUMMON, ActionKind.SPECIAL_SUMMON, ActionKind.SET_MONSTER, ActionKind.SET_ST, ActionKind.ACTIVATE):
                    played_cards.append(a.passcode)

        opening_hand = played_cards[:5]
        # Pad opening hand if fewer than 5 unique played cards
        pool = list(original_deck.main)
        for c in opening_hand:
            if c in pool:
                pool.remove(c)

        while len(opening_hand) < 5 and pool:
            opening_hand.append(pool.pop(0))

        # In ocgcore, cards are drawn from list_main.back() (pop_back).
        # We put remaining cards at front, and reversed opening hand at back.
        reordered_main = pool + list(reversed(opening_hand))
        new_deck = DeckData(main=reordered_main, extra=list(original_deck.extra), side=list(original_deck.side))
        return new_deck, list(opening_hand)

    def _translate_action(self, action: ParsedAction) -> List[bytes]:
        """Translates a single action into one or more engine response packets."""
        packets: List[bytes] = []

        if action.kind == ActionKind.DRAW:
            self._handle_draw(action.player, action.passcode)
        elif action.kind in (ActionKind.SUMMON, ActionKind.SPECIAL_SUMMON):
            cmd = CMD_SUMMON if action.kind == ActionKind.SUMMON else CMD_SPECIAL_SUMMON
            packets.append(self._encode_summon(action.player, action.passcode, cmd))
            packets.append(self._encode_pass_chain())
        elif action.kind == ActionKind.SET_MONSTER:
            packets.append(self._encode_summon(action.player, action.passcode, CMD_SET_MONSTER))
        elif action.kind == ActionKind.SET_ST:
            packets.append(self._encode_summon(action.player, action.passcode, CMD_SET_ST))
        elif action.kind == ActionKind.ACTIVATE:
            packets.append(self._encode_activate(action.player, action.passcode))
            packets.append(self._encode_pass_chain())
        elif action.kind == ActionKind.ATTACK:
            atk_idx = self._get_field_index(action.player, action.passcode)
            packets.append(struct.pack("<I", (atk_idx << 16) | BATTLE_ATTACK))
            packets.append(self._encode_pass_chain())
        elif action.kind == ActionKind.PHASE:
            packets.append(struct.pack("<I", CMD_TO_END))

        return packets

    def _handle_draw(self, player: int, passcode: int) -> None:
        hand = self.p1_hand if player == 0 else self.p2_hand
        if passcode > 0:
            hand.append(passcode)

    def _encode_summon(self, player: int, passcode: int, cmd_type: int) -> bytes:
        hand = self.p1_hand if player == 0 else self.p2_hand
        card_idx = hand.index(passcode) if passcode in hand else 0
        if passcode in hand:
            hand.pop(card_idx)
            field = self.p1_field if player == 0 else self.p2_field
            field.append(passcode)
        return struct.pack("<I", (card_idx << 16) | cmd_type)

    def _encode_activate(self, player: int, passcode: int) -> bytes:
        hand = self.p1_hand if player == 0 else self.p2_hand
        card_idx = hand.index(passcode) if passcode in hand else 0
        if passcode in hand:
            hand.pop(card_idx)
        return struct.pack("<I", (card_idx << 16) | CMD_ACTIVATE)

    def _get_field_index(self, player: int, passcode: int) -> int:
        field = self.p1_field if player == 0 else self.p2_field
        return field.index(passcode) if passcode in field else 0

    def _encode_pass_chain(self) -> bytes:
        return struct.pack("<i", -1)
