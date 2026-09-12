"""Port of HashSetDictionary<T,T2> from K_Dictionary.cs: a key -> set-of-values multimap.

K_Dictionary.cs's own K_Dictionary class extends this specifically for (str, str) with the
"<br><br>"-joining logic on top (see k_dictionary.py); DictionaryExplorer uses this generic
shape directly for its reading/entry/sense/gloss indices.
"""


class HashSetMultiMap:
    def __init__(self):
        self._data: dict = {}

    def add_combination(self, key, value) -> None:
        self._data.setdefault(key, set()).add(value)

    def has_combination(self, key, value) -> bool:
        return value in self._data.get(key, ())

    def try_get_value(self, key) -> tuple[bool, set | None]:
        values = self._data.get(key)
        return (values is not None), values
