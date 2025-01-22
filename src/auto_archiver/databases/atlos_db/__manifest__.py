{
    "name": "Atlos Database",
    "type": ["database"],
    "entry_point": "atlos_db:AtlosDb",
    "requires_setup": True,
    "external_dependencies":
        {"python": ["loguru",
                    ""],
         "bin": [""]},
    "configs": {},
    "description": """
Handles integration with the Atlos platform for managing archival results.

### Features
- Outputs archival results to the Atlos API for storage and tracking.
- Updates failure status with error details when archiving fails.
- Processes and formats metadata, including ISO formatting for datetime fields.
- Skips processing for items without an Atlos ID.

### Setup
Required configs:
- atlos_url: Base URL for the Atlos API.
- api_token: Authentication token for API access.
"""
,
}
