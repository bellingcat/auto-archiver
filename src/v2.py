

from abc import ABC
from configs.v2config import ConfigV2
from orchestrator import ArchivingOrchestrator

config = ConfigV2()
config.parse()

orchestrator = ArchivingOrchestrator(config)

orchestrator.feed()
