"""Parses DuelingBook JSON replay logs into normalized structures."""

from typing import Any, Dict, List, Optional
from .models import ActionKind, DeckData, ParsedAction, PlayerState, ReplayGame
from .card_mapper import CardMapper

PLAY_MAPPING: Dict[str, ActionKind] = {
    "Draw card": ActionKind.DRAW,
    "Normal Summon": ActionKind.SUMMON,
    "S. Summon ATK": ActionKind.SPECIAL_SUMMON,
    "SS ATK": ActionKind.SPECIAL_SUMMON,
    "S. Summon DEF": ActionKind.SPECIAL_SUMMON,
    "SS DEF": ActionKind.SPECIAL_SUMMON,
    "Special Summon": ActionKind.SPECIAL_SUMMON,
    "Set Monster": ActionKind.SET_MONSTER,
    "Set S/T": ActionKind.SET_ST,
    "Activate": ActionKind.ACTIVATE,
    "Attack": ActionKind.ATTACK,
    "To Graveyard": ActionKind.TO_GRAVE,
    "To Grave": ActionKind.TO_GRAVE,
    "To GY": ActionKind.TO_GRAVE,
    "Banish": ActionKind.BANISH,
    "Banish FD": ActionKind.BANISH,
    "Change LP": ActionKind.DAMAGE,
    "Target": ActionKind.TARGET,
    "Surrender": ActionKind.SURRENDER,
    "Admit defeat": ActionKind.SURRENDER,
}


class DBLoader:
    """Extracts decks, player info, and actions from raw DB JSON."""

    def __init__(self, mapper: Optional[CardMapper] = None) -> None:
        self.mapper = mapper or CardMapper()
        self.slot_to_card: Dict[int, Any] = {}

    def parse(self, raw: Dict[str, Any]) -> List[ReplayGame]:
        """Parses DuelingBook payload into a list of ReplayGame objects."""
        # 1. Pre-register all cards found in plays
        self._scan_and_register_cards(raw.get("plays", []))

        # 2. Extract players and decks
        p1 = self._parse_player(raw.get("player1", {}), default_name="Player 1")
        p2 = self._parse_player(raw.get("player2", {}), default_name="Player 2")

        # 3. Parse action stream & segment into games
        plays = raw.get("plays", [])
        raw_games = self._segment_games(plays)

        results: List[ReplayGame] = []
        for idx, g_plays in enumerate(raw_games, start=1):
            actions = self._parse_actions(g_plays, p1.username, p2.username)
            game = ReplayGame(
                game_number=idx,
                player1=PlayerState(p1.username, p1.rating, p1.deck, 8000),
                player2=PlayerState(p2.username, p2.rating, p2.deck, 8000),
                actions=actions,
            )
            results.append(game)

        if not results:
            results.append(ReplayGame(1, p1, p2, []))

        return results

    def _scan_and_register_cards(self, plays: List[Dict[str, Any]]) -> None:
        """Collects card names and serial numbers across all play events."""
        for p in plays:
            slot = p.get("id")
            c = p.get("card")
            if slot and isinstance(slot, int) and c and isinstance(c, dict):
                self.slot_to_card[slot] = c
            if isinstance(c, dict) and "name" in c:
                code = self.mapper.resolve(c)
                if code > 0:
                    self.mapper.register(c["name"], code)
            for c in p.get("cards", []):
                if isinstance(c, dict) and "name" in c:
                    code = self.mapper.resolve(c)
                    if code > 0:
                        self.mapper.register(c["name"], code)

    def _resolve_deck_item(self, item: Any, default_fallback: int = 14087893) -> int:
        """Resolves DB slot ID or card object to Konami passcode."""
        if isinstance(item, int) and item in self.slot_to_card:
            res = self.mapper.resolve(self.slot_to_card[item])
            if res > 0:
                return res
        res = self.mapper.resolve(item)
        if res > 1000:
            return res
        return default_fallback

    def _parse_player(self, p_data: Dict[str, Any], default_name: str) -> PlayerState:
        name = p_data.get("username", default_name)
        rating = int(p_data.get("rating", 0) or 0)
        main_cards = [self._resolve_deck_item(c) for c in p_data.get("main", [])]
        extra_cards = [
            self._resolve_deck_item(c, default_fallback=44508094)
            for c in p_data.get("extra", [])
            if (isinstance(c, int) and c in self.slot_to_card) or not isinstance(c, int)
        ]
        side_cards = [self._resolve_deck_item(c) for c in p_data.get("side", [])]
        deck = DeckData(main=main_cards, extra=extra_cards, side=side_cards)
        return PlayerState(username=name, rating=rating, deck=deck)

    def _segment_games(self, plays: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Splits plays into matches/games based on match reset markers."""
        games: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = []

        for p in plays:
            play_name = p.get("play", "")
            if play_name in ("Begin next duel", "Back to RPS") and current:
                games.append(current)
                current = []
            current.append(p)

        if current:
            games.append(current)
        return games

    def _parse_actions(
        self, plays: List[Dict[str, Any]], p1_name: str, p2_name: str
    ) -> List[ParsedAction]:
        actions: List[ParsedAction] = []
        for p in plays:
            play_name = p.get("play", "")
            owner_name = p.get("username") or p.get("owner", "")
            player_idx = 0 if owner_name == p1_name else 1

            kind = PLAY_MAPPING.get(play_name, ActionKind.UNKNOWN)

            card_obj = p.get("card") or {}
            card_name = card_obj.get("name", "") if isinstance(card_obj, dict) else ""
            passcode = self.mapper.resolve(card_obj)

            act = ParsedAction(
                kind=kind,
                player=player_idx,
                card_name=card_name,
                passcode=passcode,
                zone=str(p.get("zone", "")),
                value=int(p.get("value", 0) or 0),
                raw=p,
            )
            actions.append(act)
        return actions
