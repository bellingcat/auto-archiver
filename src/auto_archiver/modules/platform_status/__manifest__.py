{
    # per https://github.com/bellingcat/auto-archiver/issues/340
    "name": "Local Testing for Platform Status",
    "version": 0.1,
    "type": [],
    "requires_setup": False,
    "dependencies": {},
    "configs": {},
    "description": """
        Defines the `PlatformStatus` record schema and the status-check runner used to track
        which platforms and content types (e.g. Twitter video, Instagram photo) can currently be archived
        successfully, producing a standardized JSON report of results. 

        Runnable locally via `auto-archiver --status-check`, or programmatically via
        `auto_archiver.modules.platform_status.status_runner.run_status_checks()`.
""",
}
