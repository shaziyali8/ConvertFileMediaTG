import os
import logging
import asyncio
import time
import shutil
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID", "-1003086504750")

def get_media_type(document):
    """
    Determines if a document is an image or video based on mime_type or file extension.
    """
    mime_type = document.mime_type
    file_name = document.file_name

    if mime_type:
        if mime_type.startswith('image/'):
            return 'image'
        if mime_type.startswith('video/'):
            return 'video'

    if file_name:
        ext = os.path.splitext(file_name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']:
            return 'image'
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']:
            return 'video'

    return None

async def progress(current, total, status_msg, action_text, last_update_time):
    """
    Progress callback for downloading and uploading.
    Updates the message text at most once every few seconds to avoid flood limits.
    """
    now = time.time()
    if now - last_update_time[0] < 3 and current != total:
        return

    last_update_time[0] = now
    try:
        percentage = current * 100 / total
        await status_msg.edit_text(f"{action_text}: {percentage:.1f}%")
    except Exception as e:
        # Ignore errors if message is not modified or other flood waits (log silently)
        pass

async def generate_thumbnail(video_path, thumb_path):
    """
    Generates a thumbnail from a video file using ffmpeg (asynchronous).
    """
    try:
        # Take a frame at 00:00:01
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_path, "-ss", "00:00:01",
            "-vframes", "1", "-vf", "scale=320:-1",
            thumb_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()

        if os.path.exists(thumb_path):
            return True
    except Exception as e:
        logging.error(f"Error generating thumbnail: {e}")
    return False

def main():
    if not TOKEN or not API_ID or not API_HASH:
        print("Error: BOT_TOKEN, API_ID, and API_HASH environment variables are required.")
        return

    app = Client(
        "media_converter_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=TOKEN
    )

    @app.on_message(filters.command("start"))
    async def start_command(client: Client, message: Message):
        chat_id = message.chat.id
        await message.reply_text(
            f"Hello! Send me an image or video file (as Document) and I will convert it to media.\n"
            f"This version supports downloading and re-uploading with thumbnails.\n\n"
            f"Current Chat ID: `{chat_id}`",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    @app.on_message(filters.document)
    async def handle_document(client: Client, message: Message):
        document = message.document
        logging.info(f"Received document: {document.file_name} ({document.mime_type}, Size: {document.file_size})")

        media_type = get_media_type(document)

        if not media_type:
            logging.info("File type not supported/detected.")
            # Optionally tell the user?
            return

        status_msg = await message.reply_text("Status: Initializing download...")

        # Paths
        file_name = document.file_name or f"downloaded_file_{message.id}"
        # Ensure unique path to avoid collisions
        local_path = f"downloads/{message.id}_{file_name}"
        thumb_path = f"downloads/{message.id}_thumb.jpg"

        os.makedirs("downloads", exist_ok=True)

        try:
            # 1. Download
            start_time = time.time()
            last_update = [0]

            await message.download(
                file_name=local_path,
                progress=progress,
                progress_args=(status_msg, "Downloading", last_update)
            )

            await status_msg.edit_text("Status: Download complete. Processing/Generating thumbnail...")

            # 2. Handle Thumbnail
            final_thumb_path = None

            # If document already has a thumbnail, try to download it
            if document.thumbs:
                try:
                    # Download the largest thumbnail
                    final_thumb_path = await client.download_media(document.thumbs[-1].file_id, file_name=thumb_path)
                except Exception as e:
                    logging.warning(f"Could not download existing thumbnail: {e}")

            # If no thumbnail from document (or download failed), and it's a video, generate one
            if not final_thumb_path and media_type == 'video':
                if await generate_thumbnail(local_path, thumb_path):
                    final_thumb_path = thumb_path

            # 3. Upload
            await status_msg.edit_text("Status: Uploading...")
            last_update = [0]
            sent_message = None

            if media_type == 'image':
                sent_message = await client.send_photo(
                    chat_id=message.chat.id,
                    photo=local_path,
                    caption="Here is your image as media.",
                    reply_to_message_id=message.id,
                    progress=progress,
                    progress_args=(status_msg, "Uploading", last_update)
                )
            elif media_type == 'video':
                sent_message = await client.send_video(
                    chat_id=message.chat.id,
                    video=local_path,
                    thumb=final_thumb_path,
                    caption="Here is your video as media.",
                    reply_to_message_id=message.id,
                    supports_streaming=True,
                    progress=progress,
                    progress_args=(status_msg, "Uploading", last_update)
                )

            # 4. Forward
            destinations = []
            if CHANNEL_ID: destinations.append(("Channel", int(CHANNEL_ID) if CHANNEL_ID.lstrip('-').isdigit() else CHANNEL_ID))
            if GROUP_ID: destinations.append(("Group", int(GROUP_ID) if GROUP_ID.lstrip('-').isdigit() else GROUP_ID))

            forwarded_to = []
            errors = []

            for name, dest_chat_id in destinations:
                try:
                    # Forward the NEW media message
                    if sent_message:
                        await sent_message.copy(chat_id=dest_chat_id, caption=f"New {media_type} received.")
                        forwarded_to.append(name)
                except Exception as e:
                    logging.error(f"Failed to forward to {name}: {e}")
                    errors.append(f"{name} ({e})")

            # Final Status
            final_text = "Status: Done!"
            if forwarded_to:
                final_text = "Status: Sent to you and forwarded to " + " and ".join(forwarded_to) + "!"
            if errors:
                final_text += f"\nFailed to forward to: {', '.join(errors)}"

            await status_msg.edit_text(final_text)

        except Exception as e:
            logging.error(f"Error processing file: {e}")
            await status_msg.edit_text(f"Error: {str(e)}")
        finally:
            # 5. Cleanup
            if os.path.exists(local_path):
                os.remove(local_path)
            if final_thumb_path and os.path.exists(final_thumb_path):
                os.remove(final_thumb_path)

    print("Bot is starting...")
    app.run()

if __name__ == '__main__':
    main()
