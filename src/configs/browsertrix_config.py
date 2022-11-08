from dataclasses import dataclass

@dataclass
class BrowsertrixConfig:
    enabled: bool
    profile: str
    timeout_seconds: str
