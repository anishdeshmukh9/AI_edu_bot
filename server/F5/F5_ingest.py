import cv2
import yt_dlp
import time
from langchain_core.documents import Document
from .F5_transcript import load_transcript
from .F5_ocr import ocr_frame
from .F5_vector import create_faiss
from pathlib import Path
import uuid
import logging

logger = logging.getLogger(__name__)


def get_stream_url(video_url: str, max_height=360) -> str:
    """
    Get YouTube stream URL
    Uses m3u8 format which works better with current YouTube restrictions
    """
    ydl_opts = {
        # Use format that's available (m3u8 or direct mp4)
        "format": f"best[height<={max_height}]",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return info["url"]


def ingest_video(youtube_url: str, base_dir: Path):
    # Extract video_id
    if "youtu.be/" in youtube_url:
        video_id = youtube_url.split("youtu.be/")[1].split("?")[0]
    else:
        video_id = youtube_url.split("v=")[1].split("&")[0]

    logger.info(f"🎥 Starting video ingestion for: {video_id}")
    logger.info(f"📺 YouTube URL: {youtube_url}")
    
    # 1️⃣ Transcript - What the teacher SAYS (PRIMARY SOURCE)
    logger.info("📝 Step 1/3: Loading transcript...")
    transcript = load_transcript(video_id)
    
    if not transcript:
        logger.warning("⚠️ WARNING: No transcript found! AI will only have OCR text (visual content).")
        logger.warning("⚠️ This will result in POOR quality answers. The AI won't know what the instructor said.")
    else:
        logger.info(f"✓ Transcript loaded: {len(transcript)} segments")

    docs = []
    transcript_count = 0
    for t in transcript:
        # Enhanced metadata for transcript
        docs.append(
            Document(
                page_content=t["text"],
                metadata={
                    "start": t["start"],
                    "end": t["end"],
                    "source": "speech",
                    "type": "transcript",
                    "video_id": video_id,
                },
            )
        )
        transcript_count += 1

    # 2️⃣ Stream + OCR - What appears on SCREEN (formulas, diagrams, text) (SUPPLEMENTARY)
    logger.info("🖼️ Step 2/3: Processing video frames with OCR...")
    stream_url = get_stream_url(youtube_url, max_height=360)
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        raise RuntimeError("Failed to open video stream")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    sample_every_sec = 8          # Sample every 8 seconds
    frame_interval = int(fps * sample_every_sec)

    frame_count = 0
    max_frames = 120              # ~16 min max for demo

    logger.info(f"📊 Video FPS: {fps}, Sampling every {sample_every_sec} seconds")
    ocr_count = 0
    
    while cap.isOpened() and max_frames > 0:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            
            # Use OCR
            text = ocr_frame(frame)

            if text and len(text.strip()) > 10:
                # Enhanced metadata for OCR content
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "start": timestamp,
                            "end": timestamp + sample_every_sec,
                            "source": "visual",
                            "type": "ocr",
                            "video_id": video_id,
                            "content_type": "screen_content",  # Additional marker
                        },
                    )
                )
                max_frames -= 1
                ocr_count += 1
                if ocr_count % 10 == 0:
                    logger.info(f"  Processed {ocr_count} frames with OCR...")

        frame_count += 1

    cap.release()
    logger.info(f"✓ OCR processing complete: {ocr_count} frames processed")

    # 3️⃣ Store vectors
    logger.info("💾 Step 3/3: Creating vector database...")
    faiss_dir = base_dir / str(uuid.uuid4())
    create_faiss(docs, str(faiss_dir))
    
    transcript_docs = len([d for d in docs if d.metadata['source'] == 'speech'])
    ocr_docs = len([d for d in docs if d.metadata['source'] == 'visual'])
    
    logger.info(f"✓ Vector database created at: {faiss_dir}")
    logger.info(f"📊 Total documents: {len(docs)}")
    logger.info(f"   - Transcript (SPEECH - PRIMARY): {transcript_docs} documents")
    logger.info(f"   - OCR (SCREEN - SUPPLEMENTARY): {ocr_docs} documents")
    
    if transcript_docs == 0:
        logger.error("❌ CRITICAL: No transcript documents! AI responses will be LOW QUALITY!")
        logger.error("❌ The AI will only have visual content (OCR) and won't know what was actually explained.")
    else:
        logger.info("✓ Ingestion complete! Ready for queries.")

    return str(faiss_dir)