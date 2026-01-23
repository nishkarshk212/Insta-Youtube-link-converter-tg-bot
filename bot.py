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

def _download_video(url: str, dirpath: pathlib.Path) -> tuple[pathlib.Path, str]:
    base = _sanitize_filename(str(uuid.uuid4()))
    outtmpl = str(dirpath / (base + ".%(ext)s"))
    video_title = "Unknown Title"
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'Unknown')
            speed = d.get('_speed_str', 'Unknown')
            eta = d.get('_eta_str', 'Unknown')
            print(f"Downloading: {percent} at {speed}, ETA: {eta}")
    
    ydl_opts = {
        "format": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [progress_hook],
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        # Extract video info first to get the title
        info = ydl.extract_info(url, download=False)
        video_title = info.get('title', 'Unknown Title')
        # Now download the video
        ydl.download([url])
    
    files = list(dirpath.glob(base + ".*"))
    return files[0], video_title

def _download_audio_high(url: str, dirpath: pathlib.Path) -> tuple[pathlib.Path, str]:
    base = _sanitize_filename(str(uuid.uuid4()))
    outtmpl = str(dirpath / (base + ".%(ext)s"))
    video_title = "Unknown Title"
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'Unknown')
            speed = d.get('_speed_str', 'Unknown')
            eta = d.get('_eta_str', 'Unknown')
            print(f"Downloading: {percent} at {speed}, ETA: {eta}")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [progress_hook],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        # Extract video info first to get the title
        info = ydl.extract_info(url, download=False)
        video_title = info.get('title', 'Unknown Title')
        # Now download the audio
        ydl.download([url])
    
    files = list(dirpath.glob(base + ".mp3"))
    if files:
        return files[0], video_title
    files = list(dirpath.glob(base + ".*"))
    return files[0], video_title

def _download_audio_medium(url: str, dirpath: pathlib.Path) -> tuple[pathlib.Path, str]:
    base = _sanitize_filename(str(uuid.uuid4()))
    outtmpl = str(dirpath / (base + ".%(ext)s"))
    video_title = "Unknown Title"
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'Unknown')
            speed = d.get('_speed_str', 'Unknown')
            eta = d.get('_eta_str', 'Unknown')
            print(f"Downloading: {percent} at {speed}, ETA: {eta}")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [progress_hook],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        # Extract video info first to get the title
        info = ydl.extract_info(url, download=False)
        video_title = info.get('title', 'Unknown Title')
        # Now download the audio
        ydl.download([url])
    
    files = list(dirpath.glob(base + ".mp3"))
    if files:
        return files[0], video_title
    files = list(dirpath.glob(base + ".*"))
    return files[0], video_title

def _download_audio_low(url: str, dirpath: pathlib.Path) -> tuple[pathlib.Path, str]:
    base = _sanitize_filename(str(uuid.uuid4()))
    outtmpl = str(dirpath / (base + ".%(ext)s"))
    video_title = "Unknown Title"
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'Unknown')
            speed = d.get('_speed_str', 'Unknown')
            eta = d.get('_eta_str', 'Unknown')
            print(f"Downloading: {percent} at {speed}, ETA: {eta}")
    
    ydl_opts = {
        "format": "worstaudio/worst",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [progress_hook],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }
        ],
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        # Extract video info first to get the title
        info = ydl.extract_info(url, download=False)
        video_title = info.get('title', 'Unknown Title')
        # Now download the audio
        ydl.download([url])
    
    files = list(dirpath.glob(base + ".mp3"))
    if files:
        return files[0], video_title
    files = list(dirpath.glob(base + ".*"))
    return files[0], video_title

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
    welcome_message = """👋 *Welcome to Instagram & YouTube Link Converter Bot!*

🤖 *Bot Information:*
• *Name:* Instagram & YouTube Link Converter
• *Function:* Download videos/audio from Instagram, YouTube, and other platforms
• *Features:*
  • Download videos in MP4 format
  • Extract audio as MP3
  • Transcribe audio to text (requires OpenAI API)
• *Usage:*
  • Send any Instagram or YouTube link and choose your preferred action
  • Or use: `/download "link"` for direct conversion
  • Use `/video` or `/audio` for specific format conversion

ᴊᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ :- @Titanic_bots
ᴊᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ  :-  @hacker_unity_212
"""
    
    # Send the welcome message with formatting
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /download command with link argument"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a link.\n"
            "Usage: `/download \"link\"`\n"
            "Example: `/download https://www.youtube.com/watch?v=example`",
            parse_mode="Markdown"
        )
        return
    
    url = " ".join(context.args).strip()
    # Remove quotes if present
    url = url.strip('"\'')
    
    if not _extract_url(url):
        await update.message.reply_text("❌ Invalid URL provided. Please provide a valid YouTube or Instagram link.")
        return
    
    # Store URL and show quality selection menu
    context.user_data["pending_url"] = url
    await update.message.reply_text("Choose download quality:", reply_markup=_build_download_menu())

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /video command with link argument"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a link.\n"
            "Usage: `/video \"link\"`\n"
            "Example: `/video https://www.youtube.com/watch?v=example`",
            parse_mode="Markdown"
        )
        return
    
    url = " ".join(context.args).strip()
    # Remove quotes if present
    url = url.strip('"\'')
    
    if not _extract_url(url):
        await update.message.reply_text("❌ Invalid URL provided. Please provide a valid YouTube or Instagram link.")
        return
    
    # Store URL and show video quality selection
    context.user_data["pending_url"] = url
    await update.message.reply_text("📹 Select video quality:", reply_markup=_build_video_quality_menu())

async def audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /audio command with link argument"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a link.\n"
            "Usage: `/audio \"link\"`\n"
            "Example: `/audio https://www.youtube.com/watch?v=example`",
            parse_mode="Markdown"
        )
        return
    
    url = " ".join(context.args).strip()
    # Remove quotes if present
    url = url.strip('"\'')
    
    if not _extract_url(url):
        await update.message.reply_text("❌ Invalid URL provided. Please provide a valid YouTube or Instagram link.")
        return
    
    # Store URL and show audio quality selection
    context.user_data["pending_url"] = url
    await update.message.reply_text("🎵 Select audio quality:", reply_markup=_build_audio_quality_menu())

def _build_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📹 Download Video", callback_data="choose_video_quality")],
        [InlineKeyboardButton("🎵 Download Audio", callback_data="choose_audio_quality")],
        [InlineKeyboardButton("📝 Transcribe Lyrics", callback_data="action_transcribe")],
    ]
    return InlineKeyboardMarkup(buttons)

def _build_download_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📹 Video", callback_data="choose_video_quality")],
        [InlineKeyboardButton("🎵 Audio", callback_data="choose_audio_quality")],
        [InlineKeyboardButton("📝 Transcribe", callback_data="action_transcribe")],
    ]
    return InlineKeyboardMarkup(buttons)

def _build_video_quality_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("HD Quality (480p)", callback_data="action_video_hd")],
        [InlineKeyboardButton("SD Quality (360p)", callback_data="action_video_sd")],
        [InlineKeyboardButton("Low Quality (240p)", callback_data="action_video_low")],
        [InlineKeyboardButton("Back", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(buttons)

def _build_audio_quality_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("High Quality (MP3 192kbps)", callback_data="action_audio_high")],
        [InlineKeyboardButton("Medium Quality (MP3 128kbps)", callback_data="action_audio_medium")],
        [InlineKeyboardButton("Low Quality (MP3 64kbps)", callback_data="action_audio_low")],
        [InlineKeyboardButton("Back", callback_data="back_to_main")],
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
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
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
    
    # Handle quality selection menus
    if query.data == "choose_video_quality":
        await query.message.edit_text("📹 Select video quality:", reply_markup=_build_video_quality_menu())
        return
    elif query.data == "choose_audio_quality":
        await query.message.edit_text("🎵 Select audio quality:", reply_markup=_build_audio_quality_menu())
        return
    elif query.data == "back_to_main":
        await query.message.edit_text("Choose an action:", reply_markup=_build_menu())
        return
    
    if not url:
        await query.message.reply_text("No URL found, send a link first.")
        return
    
    # Send initial message to inform user about download start
    initial_msg = await query.message.reply_text("📥 Starting download...")
    
    tmp = _tmp_dir()
    try:
        if query.data in ["action_video", "action_video_hd"]:
            p, video_title = _download_video(url, tmp)
            # Update message with video title
            await initial_msg.edit_text(f"🎬 Video: {video_title}\n📊 Download complete, preparing to send...")
            p2 = _ensure_size(p, 48 * 1024 * 1024, "video")
            await _send_video(query.message.chat_id, p2, context)
        elif query.data == "action_video_sd":
            # SD video format with lower resolution
            base = _sanitize_filename(str(uuid.uuid4()))
            outtmpl = str(tmp / (base + ".%(ext)s"))
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', 'Unknown')
                    speed = d.get('_speed_str', 'Unknown')
                    eta = d.get('_eta_str', 'Unknown')
                    print(f"Downloading: {percent} at {speed}, ETA: {eta}")
            
            ydl_opts = {
                "format": "bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360][ext=mp4]/best[height<=360]",
                "merge_output_format": "mp4",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "progress_hooks": [progress_hook],
            }
            
            video_title = "Unknown Title"
            with YoutubeDL(ydl_opts) as ydl:
                # Extract video info first to get the title
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown Title')
                # Now download the video
                ydl.download([url])
            
            files = list(tmp.glob(base + ".*"))
            p = files[0]
            
            # Update message with video title
            await initial_msg.edit_text(f"🎬 Video: {video_title}\n📊 Download complete, preparing to send...")
            p2 = _ensure_size(p, 48 * 1024 * 1024, "video")
            await _send_video(query.message.chat_id, p2, context)
        elif query.data == "action_video_low":
            # Low quality video format
            base = _sanitize_filename(str(uuid.uuid4()))
            outtmpl = str(tmp / (base + ".%(ext)s"))
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', 'Unknown')
                    speed = d.get('_speed_str', 'Unknown')
                    eta = d.get('_eta_str', 'Unknown')
                    print(f"Downloading: {percent} at {speed}, ETA: {eta}")
            
            ydl_opts = {
                "format": "bestvideo[height<=240][ext=mp4]+bestaudio/best[height<=240][ext=mp4]/best[height<=240]",
                "merge_output_format": "mp4",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "progress_hooks": [progress_hook],
            }
            
            video_title = "Unknown Title"
            with YoutubeDL(ydl_opts) as ydl:
                # Extract video info first to get the title
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown Title')
                # Now download the video
                ydl.download([url])
            
            files = list(tmp.glob(base + ".*"))
            p = files[0]
            
            # Update message with video title
            await initial_msg.edit_text(f"🎬 Video: {video_title}\n📊 Download complete, preparing to send...")
            p2 = _ensure_size(p, 48 * 1024 * 1024, "video")
            await _send_video(query.message.chat_id, p2, context)
        elif query.data in ["action_audio", "action_audio_high"]:
            p, video_title = _download_audio_high(url, tmp)
            # Update message with audio title
            await initial_msg.edit_text(f"🎵 Audio: {video_title}\n📊 Download complete, preparing to send...")
            p2 = _ensure_size(p, 48 * 1024 * 1024, "audio")
            await _send_audio(query.message.chat_id, p2, context)
        elif query.data == "action_audio_medium":
            p, video_title = _download_audio_medium(url, tmp)
            # Update message with audio title
            await initial_msg.edit_text(f"🎵 Audio: {video_title}\n📊 Download complete, preparing to send...")
            p2 = _ensure_size(p, 48 * 1024 * 1024, "audio")
            await _send_audio(query.message.chat_id, p2, context)
        elif query.data == "action_audio_low":
            p, video_title = _download_audio_low(url, tmp)
            # Update message with audio title
            await initial_msg.edit_text(f"🎵 Audio: {video_title}\n📊 Download complete, preparing to send...")
            p2 = _ensure_size(p, 48 * 1024 * 1024, "audio")
            await _send_audio(query.message.chat_id, p2, context)
        elif query.data == "action_transcribe":
            a, video_title = _download_audio_high(url, tmp)
            # Update message with transcription info
            await initial_msg.edit_text(f"📝 Transcribing: {video_title}\n📊 Processing audio for transcription...")
            a2 = _ensure_size(a, 48 * 1024 * 1024, "audio")
            text = _openai_transcribe(a2)
            if text:
                await query.message.reply_text(text)
            else:
                await query.message.reply_text("Transcription unavailable. Set OPENAI_API_KEY.")
    except Exception as e:
        await query.message.reply_text(f"❌ Error occurred: {str(e)}")
    finally:
        # Clean up temp files
        for f in tmp.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            tmp.rmdir()
        except Exception:
            pass
        # Delete the initial message after processing
        try:
            await initial_msg.delete()
        except Exception:
            pass

def main() -> None:
    print("🚀 Starting Instagram & YouTube Link Converter Bot...")
    token = _get_token("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found!")
        print("💡 Please add your bot token to .env file as: TELEGRAM_BOT_TOKEN=your_token_here")
        return
    if not _valid_token(token):
        print(f"❌ Error: Invalid TELEGRAM_BOT_TOKEN format: {token[:10]}...")
        print("💡 Please ensure your token is in the correct format (digits:letters_and_symbols)")
        return
    try:
        app = ApplicationBuilder().token(token).build()
        # Register command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("download", download_command))
        app.add_handler(CommandHandler("video", video_command))
        app.add_handler(CommandHandler("audio", audio_command))
        # Register message and callback handlers
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
        app.add_handler(CallbackQueryHandler(handle_action))
        print("✅ Bot initialized successfully! Now listening for messages...")
        print("💬 Bot is ready to convert Instagram/YouTube links")
        print("🔧 Available commands: /start, /download, /video, /audio")
        app.run_polling()
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        print("💡 Check if your bot token is correct and has internet connectivity")

if __name__ == "__main__":
    main()
