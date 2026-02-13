from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
import logging

logger = logging.getLogger(__name__)

def load_transcript(video_id: str):
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(["en"])
            data = transcript.fetch()
            logger.info(f"✓ English transcript loaded for {video_id}")

        except NoTranscriptFound:
            transcript = next(iter(transcript_list))
            if transcript.is_translatable:
                data = transcript.translate("en").fetch()
                logger.info(
                    f"✓ Translated {transcript.language_code} → English"
                )
            else:
                data = transcript.fetch()
                logger.info(
                    f"✓ Using {transcript.language_code} transcript"
                )

    except (NoTranscriptFound, TranscriptsDisabled):
        logger.error(
            f"✗ Captions visible in UI but NOT exposed via API: {video_id}"
        )
        return []

    except Exception as e:
        logger.exception(f"✗ Transcript error for {video_id}: {e}")
        return []

    # 🔥 FIX IS HERE
    return [
        {
            "text": t.text,
            "start": t.start,
            "end": t.start + (t.duration or 0),
        }
        for t in data
        if t.text.strip()
    ]