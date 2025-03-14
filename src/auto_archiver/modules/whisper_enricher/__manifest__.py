{
    "name": "Whisper Enricher",
    "type": ["enricher"],
    "requires_setup": True,
    "dependencies": {
        "python": ["s3_storage", "loguru", "requests"],
    },
    "configs": {
        "api_endpoint": {
            "required": True,
            "help": "WhisperApi api endpoint, eg: https://whisperbox-api.com/api/v1, a deployment of https://github.com/bellingcat/whisperbox-transcribe.",
        },
        "api_key": {"required": True, "help": "WhisperApi api key for authentication"},
        "include_srt": {
            "default": False,
            "type": "bool",
            "help": "Whether to include a subtitle SRT (SubRip Subtitle file) for the video (can be used in video players).",
        },
        "timeout": {
            "default": 90,
            "type": "int",
            "help": "How many seconds to wait at most for a successful job completion.",
        },
        "action": {
            "default": "translate",
            "help": "which Whisper operation to execute",
            "choices": ["transcribe", "translate", "language_detection"],
        },
    },
    "description": """
    Integrates with a Whisper API service to transcribe, translate, or detect the language of audio and video files.

    ### Features
    - Submits audio or video files to a Whisper API deployment for processing.
    - Supports operations such as transcription, translation, and language detection.
    - Optionally generates SRT subtitle files for video content.
    - Integrates with S3-compatible storage systems to make files publicly accessible for processing.
    - Handles job submission, status checking, artifact retrieval, and cleanup.

    ### Notes
    - Requires a Whisper API endpoint and API key for authentication.
    - Only compatible with S3-compatible storage systems for media file accessibility.
    - ** This stores the media files in S3 prior to enriching them as Whisper requires public URLs to access the media files.
    - Handles multiple jobs and retries for failed or incomplete processing.
    """,
}
