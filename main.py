import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from discord import app_commands
import logging
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os
from collections import deque

discord.opus.load_opus('/opt/homebrew/lib/libopus.dylib')
load_dotenv()
token = os.getenv("DISCORD_TOKEN")

SONG_QUEUES = {}

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
logging.basicConfig(filename='bot.log', level=logging.DEBUG)

bot = commands.Bot(command_prefix='$', intents=intents)

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"We are ready to go in, {bot.user.name}")

@bot.event
async def on_member_join(member):
    await member.channel.send(f"Welcome home {member.name}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if "luck" in message.content.lower():
        await message.channel.send(f"Good luck {message.author.mention}!")
    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name="")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        try:
            voice = await channel.connect()
            source = FFmpegPCMAudio('linkstart.mp3', executable='/opt/homebrew/bin/ffmpeg')
            voice.play(source)
        except Exception as e:
            await ctx.send(f"Error: {e}")
            raise e
    else:
        await ctx.send("You are not in a voice channel!")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        SONG_QUEUES[ctx.guild.id] = deque()
        ctx.voice_client.stop()
        source = FFmpegPCMAudio('saodeath.mp3', executable='/opt/homebrew/bin/ffmpeg')
        ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(ctx.voice_client.disconnect(), bot.loop))
    else:
        await ctx.send("I am not in a voice channel!")

async def play_next_song(ctx, voice_client, disconnect_if_empty=True):
    guild_id = ctx.guild.id
    if guild_id in SONG_QUEUES and SONG_QUEUES[guild_id]:
        audio_url, title = SONG_QUEUES[guild_id].popleft()

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }
        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable='/opt/homebrew/bin/ffmpeg')

        def after_play(error):
            if error:
                print(f"Error playing {title}: {error}")
            asyncio.run_coroutine_threadsafe(play_next_song(ctx, voice_client, disconnect_if_empty=True), bot.loop)

        voice_client.play(source, after=after_play)
        asyncio.run_coroutine_threadsafe(ctx.send(f"Now playing: **{title}**"), bot.loop)

@bot.command()
async def play(ctx, *, song_query: str):
    if not ctx.author.voice:
        await ctx.send("You are not in a voice channel!")
        return

    voice_channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client
    just_joined = False

    if voice_client is None:
        voice_client = await voice_channel.connect()
        just_joined = True
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    ydl_options = {
        'format': 'bestaudio[abr<=96]/bestaudio',
        'noplaylist': True,
    }
    if song_query.startswith("https"):
        query = song_query
    else:
        query = "ytsearch1:" + song_query
    try:
        results = await search_ytdlp_async(query, ydl_options)
        tracks = results.get("entries") or [results]
    except Exception as e:
        await ctx.send(f"Search error: {e}")
        return

    if not tracks:
        await ctx.send("No results found")
        return

    first_track = tracks[0]
    audio_url = first_track["url"]
    title = first_track.get("title", "Untitled")

    guild_id = ctx.guild.id
    if guild_id not in SONG_QUEUES:
        SONG_QUEUES[guild_id] = deque()

    SONG_QUEUES[guild_id].append((audio_url, title))
    if just_joined:
        # play join sound, then start the queue after it finishes
        source = FFmpegPCMAudio('linkstart.mp3', executable='/opt/homebrew/bin/ffmpeg')
        voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next_song(ctx, voice_client), bot.loop
        ))
    else:
        if voice_client.is_playing() or voice_client.is_paused():
            await ctx.send(f"Added to queue: **{title}**")
        else:
            await play_next_song(ctx, voice_client)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped!")
    else:
        await ctx.send("Nothing is playing!")

@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id not in SONG_QUEUES or not SONG_QUEUES[guild_id]:
        await ctx.send("The queue is empty!")
        return
    q = list(SONG_QUEUES[guild_id])
    msg = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(q)])
    await ctx.send(f"**Queue:**\n{msg}")

@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        SONG_QUEUES[ctx.guild.id] = deque()
        ctx.voice_client.stop()
        await ctx.send("Stopped and cleared the queue!")
    else:
        await ctx.send("Nothing is playing!")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
