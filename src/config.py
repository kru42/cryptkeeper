import configparser
from typing import Any, Dict


class Config:
    def __init__(self, config_file: str = "config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def get_section(self, section: str) -> Dict[str, str]:
        return dict(self.config[section])

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback: int = None) -> int:
        return self.config.getint(section, key, fallback=fallback)
