"""
Archivers are responsible for retrieving the content from various external platforms.
They act as specialized modules, each tailored to interact with a specific platform,
service, or data source. The archivers collectively enable the tool to comprehensively
collect and preserve a variety of content types, such as posts, images, videos and metadata.

"""
from .archiver import Archiver
