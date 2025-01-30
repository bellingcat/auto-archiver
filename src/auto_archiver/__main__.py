""" Entry point for the auto_archiver package. """
from auto_archiver.core.orchestrator import ArchivingOrchestrator
import sys

def main():
    ArchivingOrchestrator().run(sys.argv)

if __name__ == "__main__":
    main()
