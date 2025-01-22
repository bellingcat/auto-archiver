""" Entry point for the auto_archiver package. """
from auto_archiver.core.orchestrator import ArchivingOrchestrator

def main():
    ArchivingOrchestrator().run()

if __name__ == "__main__":
    main()
