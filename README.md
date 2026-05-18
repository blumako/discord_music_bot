## Joseph Tran - Discord Bot
This is a music bot application for discord.
It uses ytdlp to extract audio stream URLs from Youtube.
FFmpeg takes said URL, then decodes and converts the audio into
a playable format for discord.


## How to setup:
Intended for mac:

Create a .env file:
DISCORD_TOKEN='your token here'

Download homebrew and install FFmpeg through homebrew (terminal)
Download all required libraries in main.py and requirements.txt

Invite to server

Use commands with prefix: '$'

## Commands:

$join - join current voice channel sender is currently in
$play "query" - join/play song either from text or url
$skip - skip song and play next song in the queue
$queue - lists all songs in the queue
$leave - leaves the voice channel

