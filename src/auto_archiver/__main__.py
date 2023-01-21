from . import ConfigV2
from . import ArchivingOrchestrator

def main():
    config = ConfigV2()
    config.parse()
    orchestrator = ArchivingOrchestrator(config)
    orchestrator.feed()


if __name__ == "__main__":
    main()
