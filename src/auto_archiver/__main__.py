"""Entry point for the auto_archiver package."""

from auto_archiver.core.orchestrator import ArchivingOrchestrator
import sys


def main():
    for _ in ArchivingOrchestrator()._command_line_run(sys.argv[1:]):
        pass


if __name__ == "__main__":
    main()
