""" Entry point for the auto_archiver package. """
from auto_archiver.core.orchestrator import ArchivingOrchestrator
import sys

def main():
    ArchivingOrchestrator()._command_line_run(sys.argv[1:])

if __name__ == "__main__":
    main()
