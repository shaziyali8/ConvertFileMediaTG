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

def is_image_file(document) -> bool:
    """
    Determines if a document is an image based on mime_type or file extension.
    Args:
        document: A telegram.Document object or similar object with mime_type and file_name attributes.
    Returns:
        bool: True if it appears to be an image, False otherwise.
    """
    if document.mime_type and document.mime_type.startswith('image/'):
        return True

    if document.file_name:
        ext = os.path.splitext(document.file_name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']:
            return True

    return False

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles document uploads. Checks if the document is an image,
    downloads it, and sends it back as a photo (media), and forwards to a channel.
    """
    document = update.message.document

    if not is_image_file(document):
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

        # Send back to user as Photo
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=bytes(file_content),
            caption="Here is your image as media.",
            reply_to_message_id=update.message.message_id
        )

        # Forward to channel if configured
        if CHANNEL_ID:
            try:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=bytes(file_content),
                    caption="New image received."
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
