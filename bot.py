import os
import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration
# MTProto requires API_ID and API_HASH in addition to BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

CHANNEL_ID = os.getenv("CHANNEL_ID")
# Defaulting GROUP_ID as requested
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

def main():
    if not TOKEN or not API_ID or not API_HASH:
        print("Error: BOT_TOKEN, API_ID, and API_HASH environment variables are required for MTProto.")
        return

    # Initialize Pyrogram Client
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
            f"Hello! Send me an image or video file (as Document) and I will convert it to media.\n\n"
            f"Current Chat ID: `{chat_id}`\n"
            f"Use this ID to configure CHANNEL_ID or GROUP_ID.",
            parse_mode=enums.ParseMode.MARKDOWN
        )

    @app.on_message(filters.document)
    async def handle_document(client: Client, message: Message):
        document = message.document
        logging.info(f"Received document: {document.file_name} ({document.mime_type}, Size: {document.file_size})")

        media_type = get_media_type(document)

        if not media_type:
            logging.info("File type not supported/detected.")
            return

        status_msg = await message.reply_text("Status: Processing via MTProto...")

        try:
            sent_message = None
            file_id = document.file_id

            # Pyrogram using MTProto handles large files better.
            # We can pass the file_id directly. If the server refuses simple conversion (wrong file ref),
            # Pyrogram might handle it, or we might need to stream.
            # For now, we try direct ID pass-through which is standard for "converting" provided the DC allows it.

            if media_type == 'image':
                sent_message = await client.send_photo(
                    chat_id=message.chat.id,
                    photo=file_id,
                    caption="Here is your image as media.",
                    reply_to_message_id=message.id
                )
            elif media_type == 'video':
                sent_message = await client.send_video(
                    chat_id=message.chat.id,
                    video=file_id,
                    caption="Here is your video as media.",
                    reply_to_message_id=message.id,
                    supports_streaming=True
                )

            # Forwarding Logic
            destinations = []
            if CHANNEL_ID: destinations.append(("Channel", int(CHANNEL_ID) if CHANNEL_ID.lstrip('-').isdigit() else CHANNEL_ID))
            if GROUP_ID: destinations.append(("Group", int(GROUP_ID) if GROUP_ID.lstrip('-').isdigit() else GROUP_ID))

            forwarded_to = []
            errors = []

            # Determine file_id to forward (use the one we just sent if possible, else original)
            forward_target = None
            if sent_message:
                forward_target = sent_message
            else:
                # If conversion failed but no exception raised (unlikely), use original
                forward_target = message

            for name, chat_id in destinations:
                try:
                    # In Pyrogram, we can just copy the message (simplest) or resend the file_id
                    # copying keeps the type. If we want to ensure it's media, we send using the file_id from 'sent_message'
                    if sent_message:
                        await sent_message.copy(chat_id=chat_id, caption=f"New {media_type} received.")
                    else:
                        # Fallback to forwarding original document if conversion failed silently?
                        await message.copy(chat_id=chat_id, caption="New file received.")

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

    print("Bot is starting...")
    app.run()

if __name__ == '__main__':
    main()
