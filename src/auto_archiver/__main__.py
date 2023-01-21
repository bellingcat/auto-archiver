from . import Config
from . import ArchivingOrchestrator

def main():
    config = Config()
    config.parse()
    orchestrator = ArchivingOrchestrator(config)
    orchestrator.feed()


if __name__ == "__main__":
    main()
