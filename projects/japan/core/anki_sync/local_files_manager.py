"""Port of LocalFilesManager.cs, minus the WinForms dialog fallback (no UI headlessly available).

Paths come from config.json only; a missing/invalid path fails loudly, naming exactly which
config.json key is wrong, instead of popping a file-picker dialog.
"""

import json
import os


class ConfigError(Exception):
    pass


class LocalFilesManager:
    def __init__(self, base_directory: str):
        config_path = os.path.join(base_directory, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8-sig") as f:
                self._config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._config = {}

    def _get_path(self, config_key: str, is_folder: bool = False) -> str:
        value = self._config.get(config_key)
        if not value:
            raise ConfigError(f'config.json is missing a value for "{config_key}".')

        if is_folder and not os.path.isdir(value):
            raise ConfigError(f'config.json\'s "{config_key}" points to a folder that doesn\'t exist: {value}')

        if not is_folder and not os.path.isfile(value):
            raise ConfigError(f'config.json\'s "{config_key}" points to a file that doesn\'t exist: {value}')

        return value

    def get_anki_collection_path(self) -> str:
        return self._get_path("AnkiCollectionPath")

    def get_jmdict_file_path(self) -> str:
        return self._get_path("JMdictPath")

    def get_jmenumdict_file_path(self) -> str:
        return self._get_path("JMenumdictPath")

    def get_furigana_file_path(self) -> str:
        return self._get_path("FuriganaPath")
