# Telegram File-to-Media Bot

This is a Python Telegram bot that automatically converts image and video files sent as documents into media (photos/videos) and sends them back to the user. It also forwards the converted media to a specified Telegram channel.

## Features

-   **Media Detection**: Detects image and video files sent as documents (by MIME type or extension).
-   **Conversion**: Downloads the document and re-uploads it as a native media type (Photo or Video).
-   **Forwarding**: Forwards the media to a configured Telegram channel.
-   **Progress Updates**: Sends real-time progress updates to the user (Downloading, Uploading, Done).

## Supported Formats

-   **Images**: .jpg, .jpeg, .png, .gif, .bmp, .webp, .tiff
-   **Videos**: .mp4, .mov, .avi, .mkv, .webm, .flv, .wmv

## Prerequisites

-   Python 3.7+
-   A Telegram Bot Token (from @BotFather)
-   (Optional) A Telegram Channel ID where media should be forwarded. The bot must be an administrator in this channel to post messages.

## Installation

1.  Clone the repository or download the files.
2.  Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Set the following environment variables:

-   `BOT_TOKEN`: Your Telegram Bot API token.
-   `CHANNEL_ID`: (Optional) The ID of the channel to forward media to (e.g., `@mychannel` or `-100123456789`).

## Usage

Run the bot using:

```bash
export BOT_TOKEN="your_bot_token"
export CHANNEL_ID="@your_channel_id" # Optional
python bot.py
```

## How it works

1.  Send a file (Document) to the bot.
2.  The bot replies with "Status: Downloading file...".
3.  The bot identifies if it's an image or video.
4.  The bot converts the file to the appropriate media type and sends it back to you.
5.  If configured, the bot forwards the media to the specified channel.
6.  The status message is updated to "Status: Sent to you and forwarded to channel!".
