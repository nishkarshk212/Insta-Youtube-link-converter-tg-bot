import os
import re
import asyncio
import tempfile
import uuid
import pathlib
import subprocess
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from yt_dlp import YoutubeDL

def _get_token(name: str) -> Optional[str]:
    v = os.getenv(name)
    if v:
        return v.strip()
    cwd = pathlib.Path.cwd()
    script_dir = pathlib.Path(__file__).resolve().parent
    p = cwd / (name + ".txt")
    if p.exists():
        try:
            s = p.read_text(encoding="utf-8").strip()
            if "=" in s:
                k, val = s.split("=", 1)
                if k.strip() in (name, name.lower(), name.upper()):
                    return val.strip().strip('"').strip("'")
            return s
        except Exception:
            pass
    p2 = script_dir / (name + ".txt")
    if p2.exists():
        try:
            s = p2.read_text(encoding="utf-8").strip()
            if "=" in s:
                k, val = s.split("=", 1)
                if k.strip() in (name, name.lower(), name.upper()):
                    return val.strip().strip('"').strip("'")
            return s
        except Exception:
            pass
    envf = cwd / ".env"
    if envf.exists():
        try:
            for line in envf.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, val = line.split("=", 1)
                    if k.strip() == name:
                        return val.strip().strip('"').strip("'")
        except Exception:
            pass
    envf2 = script_dir / ".env"
    if envf2.exists():
        try:
            for line in envf2.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, val = line.split("=", 1)
                    if k.strip() == name:
                        return val.strip().strip('"').strip("'")
        except Exception:
            pass
    return None

def _valid_token(s: Optional[str]) -> bool:
    if not s:
        return False
    s = s.strip()
    if ":" not in s:
        return False
    p = s.split(":", 1)
    return p[0].isdigit() and len(p[1]) >= 10

def _tmp_dir() -> pathlib.Path:
    d = pathlib.Path(tempfile.mkdtemp(prefix="tg_media_"))
    return d

def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)

def _download_video(url: str, dirpath: pathlib.Path) -> pathlib.Path:
    base = _sanitize_filename(str(uuid.uuid4()))
    outtmpl = str(dirpath / (base + ".%(ext)s"))
    ydl_opts = {
        "format": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    files = list(dirpath.glob(base + ".*"))
    return files[0]

def _download_audio(url: str, dirpath: pathlib.Path) -> pathlib.Path:
    base = _sanitize_filename(str(uuid.uuid4()))
    outtmpl = str(dirpath / (base + ".%(ext)s"))
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    files = list(dirpath.glob(base + ".mp3"))
    if files:
        return files[0]
    files = list(dirpath.glob(base + ".*"))
    return files[0]

def _ensure_size(path: pathlib.Path, max_bytes: int, kind: str) -> pathlib.Path:
    if path.stat().st_size <= max_bytes:
        return path
    if not _has_ffmpeg():
        return path
    out = path.with_name(path.stem + "_small" + (".mp4" if kind == "video" else ".mp3"))
    if kind == "video":
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-vf",
            "scale='min(640,iw)':-2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            "900k",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(out),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(out),
        ]
    subprocess.run(cmd, check=True)
    return out if out.exists() else path

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Send a YouTube/Instagram/video URL.")

def _build_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Download Video", callback_data="action_video")],
        [InlineKeyboardButton("Download Audio", callback_data="action_audio")],
        [InlineKeyboardButton("Transcribe Lyrics", callback_data="action_transcribe")],
    ]
    return InlineKeyboardMarkup(buttons)

def _extract_url(text: str) -> Optional[str]:
    m = re.search(r"(https?://\S+)", text)
    return m.group(1) if m else None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    url = _extract_url(update.message.text.strip())
    if not url:
        await update.message.reply_text("Provide a valid media URL.")
        return
    context.user_data["pending_url"] = url
    await update.message.reply_text("Choose an action:", reply_markup=_build_menu())

async def _send_video(chat_id: int, path: pathlib.Path, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
    with path.open("rb") as f:
        await context.bot.send_video(chat_id=chat_id, video=InputFile(f, filename=path.name))

async def _send_audio(chat_id: int, path: pathlib.Path, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_AUDIO)
    with path.open("rb") as f:
        await context.bot.send_audio(chat_id=chat_id, audio=InputFile(f, filename=path.name))

def _openai_transcribe(path: pathlib.Path) -> Optional[str]:
    key = _get_token("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        with path.open("rb") as f:
            res = client.audio.transcriptions.create(model="whisper-1", file=f)
        return getattr(res, "text", None) or getattr(res, "transcription", None)
    except Exception:
        return None

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    url = context.user_data.get("pending_url")
    if not url:
        await query.message.reply_text("No URL found, send a link first.")
        return
    tmp = _tmp_dir()
    try:
        if query.data == "action_video":
            p = _download_video(url, tmp)
            p2 = _ensure_size(p, 48 * 1024 * 1024, "video")
            await _send_video(query.message.chat_id, p2, context)
        elif query.data == "action_audio":
            p = _download_audio(url, tmp)
            p2 = _ensure_size(p, 48 * 1024 * 1024, "audio")
            await _send_audio(query.message.chat_id, p2, context)
        elif query.data == "action_transcribe":
            a = _download_audio(url, tmp)
            a2 = _ensure_size(a, 48 * 1024 * 1024, "audio")
            text = _openai_transcribe(a2)
            if text:
                await query.message.reply_text(text)
            else:
                await query.message.reply_text("Transcription unavailable. Set OPENAI_API_KEY.")
    finally:
        for f in tmp.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            tmp.rmdir()
        except Exception:
            pass

def main() -> None:
    token = _get_token("TELEGRAM_BOT_TOKEN")
    if not _valid_token(token):
        raise RuntimeError("Invalid TELEGRAM_BOT_TOKEN. Put it in env, .env or TELEGRAM_BOT_TOKEN.txt")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(CallbackQueryHandler(handle_action))
    app.run_polling()

if __name__ == "__main__":
    main()
