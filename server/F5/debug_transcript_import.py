# debug_transcript_import.py
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi

print("MODULE PATH:", youtube_transcript_api.__file__)
print("HAS list_transcripts:", hasattr(YouTubeTranscriptApi, "list_transcripts"))
print("DIR:", dir(YouTubeTranscriptApi))