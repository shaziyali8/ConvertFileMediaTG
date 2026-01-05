import os
import logging
import io
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID")

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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command. Sends a welcome message and the current Chat ID.
    """
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Hello! Send me an image or video file (as Document) and I will convert it to media.\n\n"
        f"Current Chat ID: `{chat_id}`\n"
        f"Use this ID to configure CHANNEL_ID or GROUP_ID.",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles document uploads. Checks if the document is an image or video,
    downloads it, and sends it back as media (photo/video), and forwards to a channel and/or group.
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
        # In python-telegram-bot v20+, we use download_to_memory which accepts a writeable buffer
        file_buffer = io.BytesIO()
        await new_file.download_to_memory(out=file_buffer)
        file_buffer.seek(0)
        file_content = file_buffer.getvalue()

        await context.bot.edit_message_text(
            chat_id=update.message.chat_id,
            message_id=progress_msg.message_id,
            text="Status: Converting and Uploading..."
        )

        sent_message = None

        # Send back to user
        if media_type == 'image':
            sent_message = await context.bot.send_photo(
                chat_id=update.message.chat_id,
                photo=file_content,
                caption="Here is your image as media.",
                reply_to_message_id=update.message.message_id
            )
        elif media_type == 'video':
            sent_message = await context.bot.send_video(
                chat_id=update.message.chat_id,
                video=file_content,
                caption="Here is your video as media.",
                reply_to_message_id=update.message.message_id,
                supports_streaming=True
            )

        # Extract file_id to optimize forwarding
        file_id_to_send = file_content # Default back to bytes if extraction fails
        if sent_message:
            if sent_message.photo:
                # Photo is a list of sizes, take the last one (largest)
                file_id_to_send = sent_message.photo[-1].file_id
            elif sent_message.video:
                file_id_to_send = sent_message.video.file_id

        # Determine destinations
        destinations = []
        if CHANNEL_ID:
            destinations.append(("Channel", CHANNEL_ID))
        if GROUP_ID:
            destinations.append(("Group", GROUP_ID))

        forwarded_to = []
        errors = []

        for name, chat_id in destinations:
            try:
                if media_type == 'image':
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=file_id_to_send,
                        caption="New image received."
                    )
                elif media_type == 'video':
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=file_id_to_send,
                        caption="New video received.",
                        supports_streaming=True
                    )
                forwarded_to.append(name)
            except Exception as e:
                logging.error(f"Failed to forward to {name}: {e}")
                errors.append(f"{name} ({e})")

        # Construct final status message
        final_text = "Status: Sent to you"
        if forwarded_to:
            final_text += " and forwarded to " + " and ".join(forwarded_to) + "!"
        elif not destinations:
            final_text += " (No forwarding configured)."

        if errors:
            final_text += f"\nFailed to forward to: {', '.join(errors)}"

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
        print("Please set BOT_TOKEN and optionally CHANNEL_ID/GROUP_ID.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Handle /start command
    start_handler = CommandHandler('start', start_command)
    application.add_handler(start_handler)

    # Handle all documents
    document_handler = MessageHandler(filters.Document.ALL, handle_document)
    application.add_handler(document_handler)

    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
