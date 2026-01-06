# Telegram File-to-Media Bot (MTProto)

This is a Python Telegram bot that converts image and video files sent as documents into native media (photos/videos) and forwards them to a configured channel and/or group.

It uses **Pyrogram** (MTProto) to support large files (up to 2GB) and efficient processing.

## Features

-   **MTProto Powered**: Uses the Telegram MTProto API via Pyrogram for better performance and large file support.
-   **Media Detection**: Detects image and video files sent as documents.
-   **Conversion**: Converts the document to a native media type (Photo or Video).
-   **Thumbnail Support**: Automatically extracts or generates thumbnails for videos.
-   **Forwarding**: Forwards the media to a configured Telegram channel and/or group.
-   **Progress Updates**: Sends real-time progress updates.

## Prerequisites

-   Python 3.7+
-   A Telegram Bot Token (from @BotFather)
-   **API ID and API Hash**: Required for MTProto clients. You can get these from [my.telegram.org](https://my.telegram.org).
-   **ffmpeg**: Required for video thumbnail generation.

## Installation

1.  Clone the repository or download the files.
2.  Install the required system dependencies:
    *   **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
    *   **MacOS**: `brew install ffmpeg`
    *   **Windows**: Download and install from ffmpeg.org
3.  Install the required Python dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Set the following environment variables:

-   `BOT_TOKEN`: Your Telegram Bot API token.
-   `API_ID`: Your Telegram API ID.
-   `API_HASH`: Your Telegram API Hash.
-   `CHANNEL_ID`: (Optional) The ID of the channel to forward media to (e.g., `-100123456789`).
-   `GROUP_ID`: (Optional) The ID of the group to forward media to (e.g., `-100987654321`).

## Usage

Run the bot using:

```bash
export BOT_TOKEN="your_bot_token"
export API_ID="your_api_id"
export API_HASH="your_api_hash"
export CHANNEL_ID="-100xxxx"
export GROUP_ID="-100xxxx"
python bot.py
```

## How to get API ID and Hash

1.  Log in to your Telegram account at [my.telegram.org](https://my.telegram.org).
2.  Go to "API development tools".
3.  Create a new application (if you haven't already).
4.  Copy the `App api_id` and `App api_hash`.

## Troubleshooting

-   **"Chat not found"**: Ensure the bot is added to the channel/group and is an admin. Use `/start` to verify the ID.
-   **File conversion failed**: Some files cannot be converted if their format is invalid. The bot will report an error.
