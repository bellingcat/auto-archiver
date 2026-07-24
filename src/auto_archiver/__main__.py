"""Entry point for the auto_archiver package."""

from auto_archiver.core.orchestrator import ArchivingOrchestrator
import sys


def main():
    # NOTE: Slightly awkward ergonomics for running the CLI invocation, may need to revise.
    if "--status-check" in sys.argv:
        from auto_archiver.modules.platform_status.status_cli import run_status_check_cli

        sys.exit(run_status_check_cli(sys.argv[1:]))

    for _ in ArchivingOrchestrator()._command_line_run(sys.argv[1:]):
        pass


if __name__ == "__main__":
    main()
