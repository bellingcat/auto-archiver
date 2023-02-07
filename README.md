# Auto Archiver
Read the [article about Auto Archiver on bellingcat.com](https://www.bellingcat.com/resources/2022/09/22/preserve-vital-online-content-with-bellingcats-auto-archiver-tool/).


Python tool to automatically archive social media posts, videos, and images from a Google Sheets, the console, and more. Uses different archivers depending on the platform, and can save content to local storage, S3 bucket (Digital Ocean Spaces, AWS, ...), and Google Drive. If using Google Sheets as the source for links, it will be updated with information about the archived content. It can be run manually or on an automated basis.

There are 3 ways to use the auto-archiver
1. (simplest) via docker `docker ... TODO`
2. (pypi) `pip install auto-archiver`
3. (legacy) clone and manually install from repo (see legacy [tutorial video](https://youtu.be/VfAhcuV2tLQ))
