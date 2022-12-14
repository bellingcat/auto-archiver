
from __future__ import annotations
from ast import List
from typing import Any, Union, Dict
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class Media:
    filename: str
    id: str = None
    hash: str = None
    cdn_url: str = None
    hash: str = None

