# F8/_F8_supabase_audio.py

import os
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()

def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Supabase credentials missing. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
        )

    return create_client(url, key)


def upload_audio(file_path: str, user_id: str, chat_id: str) -> str:
    supabase = get_supabase_client()

    file_name = f"gita_audio/{user_id}/{chat_id}.mp3"

    with open(file_path, "rb") as f:
        supabase.storage.from_("gita-audio").upload(
            file_name,
            f,
            {"content-type": "audio/mpeg"}
        )

    return supabase.storage.from_("gita-audio").get_public_url(file_name)