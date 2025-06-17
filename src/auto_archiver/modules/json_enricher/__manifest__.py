{
    "name": "JSON Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "dependencies": {
        "python": ["loguru"],
    },
    "configs": {},
    "description": """

    Writes all archiving process metadata to a JSON file so it can be parsed by other tools. As this is an Enricher, it will not contain the final stored URLs. 
	
	WARNING: The resulting JSON may reveal sensitive information about the computer and settings in which the archiving process was run. 

    """,
}
