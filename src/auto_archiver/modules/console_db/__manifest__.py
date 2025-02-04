{
    "name": "Console Database",
    "type": ["database"],
    "requires_setup": False,
    "dependencies": {
        "python": ["loguru"],
    },
    "description": """
Provides a simple database implementation that outputs archival results and status updates to the console.

### Features
- Logs the status of archival tasks directly to the console, including:
  - started
  - failed (with error details)
  - aborted
  - done (with optional caching status)
- Useful for debugging or lightweight setups where no external database is required.

### Setup
No additional configuration is required.
""",
}
