"""Port of K_Dictionary.cs: combines multiple values seen for the same key into one
'<br><br>'-joined, sorted string, then hands back AddOrUpdateInfo rows for the writer."""

from .hashset_multimap import HashSetMultiMap
from .models import AddOrUpdateInfo


class KDictionary(HashSetMultiMap):
    def try_get_combined_value(self, key: str) -> tuple[bool, str]:
        found, values = self.try_get_value(key)
        if not found:
            return False, ""
        return True, "<br><br>".join(sorted(values))

    def get_add_or_update_info(self, key_field_name: str, value_field_name: str) -> list[AddOrUpdateInfo]:
        result = []
        for key in self._data:
            _, value = self.try_get_combined_value(key)
            result.append(AddOrUpdateInfo({key_field_name: key, value_field_name: value}))
        return result
