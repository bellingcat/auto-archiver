from dataclasses import dataclass


@dataclass
class SeleniumConfig:
    timeout_seconds: int = 120
    window_width: int = 1400
    window_height: int = 2000
