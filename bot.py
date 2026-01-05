import os
import logging
import io
from telegram import Update, error
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# SECURITY WARNING: Never hardcode tokens in production files.
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID", "-1003086504750")

# Telegram Bot API Download Limit is 20MB
DOWNLOAD_LIMIT = 20 * 1024 * 1024

def get_media_type(document):
    """
    Determines if a document is an image or video based on mime_type or file extension.
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
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Hello! Send me an image or video file (as Document) and I will convert it to media.\n\n"
        f"Current Chat ID: `{chat_id}`\n"
        f"Use this ID to configure CHANNEL_ID or GROUP_ID.",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    logging.info(f"Received document: {document.file_name} ({document.mime_type}, Size: {document.file_size})")

    media_type = get_media_type(document)

    if not media_type:
        logging.info("File type not supported/detected.")
        return

    progress_msg = await update.message.reply_text("Status: Processing...")

    try:
        sent_message = None
        file_source = None
        is_large_file = document.file_size > DOWNLOAD_LIMIT

        if not is_large_file:
            # Case 1: Small file (<20MB). Download and convert proper.
            await context.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=progress_msg.message_id,
                text="Status: Downloading & Converting..."
            )

            new_file = await context.bot.get_file(document.file_id)
            file_buffer = io.BytesIO()
            await new_file.download_to_memory(out=file_buffer)
            file_buffer.seek(0)
            file_source = file_buffer.getvalue()

        else:
            # Case 2: Large file (>20MB). Attempt file_id pass-through.
            await context.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=progress_msg.message_id,
                text="Status: Large file detected. Attempting direct conversion..."
            )
            file_source = document.file_id

        # Attempt to send as media
        try:
            if media_type == 'image':
                sent_message = await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=file_source,
                    caption="Here is your image as media.",
                    reply_to_message_id=update.message.message_id
                )
            elif media_type == 'video':
                sent_message = await context.bot.send_video(
                    chat_id=update.message.chat_id,
                    video=file_source,
                    caption="Here is your video as media.",
                    reply_to_message_id=update.message.message_id,
                    supports_streaming=True
                )
        except error.TelegramError as e:
            # If direct conversion fails (likely for large files or strict API checks),
            # fall back to forwarding the document if it was a large file.
            if is_large_file:
                logging.warning(f"Direct conversion failed for large file: {e}. Forwarding original.")
                await context.bot.edit_message_text(
                    chat_id=update.message.chat_id,
                    message_id=progress_msg.message_id,
                    text="Status: Cannot convert large file to media. Forwarding as document..."
                )
                # Forward original message to destinations instead of converted one
                sent_message = update.message # Treat original as "sent" for forwarding logic
            else:
                raise e

        # Logic for forwarding
        destinations = []
        if CHANNEL_ID: destinations.append(("Channel", CHANNEL_ID))
        if GROUP_ID: destinations.append(("Group", GROUP_ID))

        forwarded_to = []
        errors = []

        # Determine what to forward
        # If we successfully created a new media message, use its ID.
        # If we failed conversion (large file) and fell back, use the original document ID.

        forward_method = 'media' # 'media' or 'document'
        file_id_to_send = None

        if sent_message and sent_message != update.message:
            # We created a new media message
            if sent_message.photo:
                file_id_to_send = sent_message.photo[-1].file_id
                forward_method = 'photo'
            elif sent_message.video:
                file_id_to_send = sent_message.video.file_id
                forward_method = 'video'
        elif sent_message == update.message:
            # Fallback: Forwarding the original document
            file_id_to_send = document.file_id
            forward_method = 'document'

        if file_id_to_send:
            for name, chat_id in destinations:
                try:
                    if forward_method == 'photo':
                        await context.bot.send_photo(chat_id=chat_id, photo=file_id_to_send, caption="New image received.")
                    elif forward_method == 'video':
                        await context.bot.send_video(chat_id=chat_id, video=file_id_to_send, caption="New video received.", supports_streaming=True)
                    elif forward_method == 'document':
                         await context.bot.send_document(chat_id=chat_id, document=file_id_to_send, caption="New file received (Large).")

                    forwarded_to.append(name)
                except Exception as e:
                    logging.error(f"Failed to forward to {name}: {e}")
                    errors.append(f"{name} ({e})")

        # Final Status
        final_text = "Status: Done!"
        if sent_message == update.message:
            final_text = "Status: Forwarded as Document (File too large to convert)."
        elif forwarded_to:
            final_text = "Status: Sent to you and forwarded to " + " and ".join(forwarded_to) + "!"

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
            text=f"Error: {str(e)}"
        )

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN environment variable is not set.")
        return

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
