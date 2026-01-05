import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

def get_media_type(document):
    """
    Determines if a document is an image or video based on mime_type or file extension.
    Args:
        document: A telegram.Document object or similar object with mime_type and file_name attributes.
    Returns:
        str: 'image', 'video', or None.
    """
    mime_type = document.mime_type
    file_name = document.file_name

    # Check mime type first
    if mime_type:
        if mime_type.startswith('image/'):
            return 'image'
        if mime_type.startswith('video/'):
            return 'video'

    # Fallback to extension
    if file_name:
        ext = os.path.splitext(file_name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']:
            return 'image'
        if ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']:
            return 'video'

    return None

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles document uploads. Checks if the document is an image or video,
    downloads it, and sends it back as media (photo/video), and forwards to a channel.
    """
    document = update.message.document
    media_type = get_media_type(document)

    if not media_type:
        return

    progress_msg = await update.message.reply_text("Status: Downloading file...")

    try:
        # Get file object
        new_file = await context.bot.get_file(document.file_id)

        # Download file to memory
        file_content = await new_file.download_as_bytearray()

        await context.bot.edit_message_text(
            chat_id=update.message.chat_id,
            message_id=progress_msg.message_id,
            text="Status: Converting and Uploading..."
        )

        media_bytes = bytes(file_content)

        # Send back to user
        if media_type == 'image':
            await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=media_bytes,
                caption="Here is your image as media.",
                reply_to_message_id=update.message.message_id
            )
        elif media_type == 'video':
            await context.bot.send_video(
                chat_id=update.message.chat_id,
                video=media_bytes,
                caption="Here is your video as media.",
                reply_to_message_id=update.message.message_id,
                supports_streaming=True
            )

        # Forward to channel if configured
        if CHANNEL_ID:
            try:
                if media_type == 'image':
                    await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=media_bytes,
                        caption="New image received."
                    )
                elif media_type == 'video':
                    await context.bot.send_video(
                        chat_id=CHANNEL_ID,
                        video=media_bytes,
                        caption="New video received.",
                        supports_streaming=True
                    )
                final_text = "Status: Sent to you and forwarded to channel!"
            except Exception as e:
                logging.error(f"Failed to forward to channel: {e}")
                final_text = f"Status: Sent to you, but failed to forward to channel ({e})."
        else:
            final_text = "Status: Sent to you (Channel ID not configured)."

        await context.bot.edit_message_text(
            chat_id=update.message.chat_id,
            message_id=progress_msg.message_id,
            text=final_text
        )

    except Exception as e:
        logging.error(f"Error processing file: {e}")
        await context.bot.edit_message_text(
            chat_id=update.message.chat_id,
            message_id=progress_msg.message_id,
            text=f"Error processing request: {e}"
        )

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN environment variable is not set.")
        print("Please set BOT_TOKEN and optionally CHANNEL_ID.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Handle all documents
    document_handler = MessageHandler(filters.Document.ALL, handle_document)
    application.add_handler(document_handler)

    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
