import os
import random
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

SOUNDS_DIR = "sounds"

def get_random_sound():
    if not os.path.exists(SOUNDS_DIR):
        return None
    files = [f for f in os.listdir(SOUNDS_DIR) if f.endswith(('.mp3', '.wav', '.ogg'))]
    return os.path.join(SOUNDS_DIR, random.choice(files)) if files else None

async def play_sound(vc):
    if vc and vc.is_connected():
        sound_path = get_random_sound()
        if sound_path and not vc.is_playing():
            # На Linux/Railway запускаем ffmpeg без .exe
            vc.play(discord.FFmpegPCMAudio(sound_path))
            print(f"🔊 Воспроизводится: {sound_path}")
            while vc.is_playing():
                await asyncio.sleep(1)

@tasks.loop(seconds=10)
async def sound_loop():
    for guild in bot.guilds:
        vc = guild.voice_client
        if vc and vc.is_connected() and not vc.is_playing():
            # Задержка перед следующим случайным звуком (1-10 минут)
            wait_time = random.randint(60, 600)
            print(f"⏳ Следующий звук в {guild.name} через {wait_time // 60} мин.")
            await asyncio.sleep(wait_time)
            await play_sound(vc)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} успешно запущен и готов к работе!")
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} команд.")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

@bot.tree.command(name="joinzvukobot", description="Подключить бота к голосовому каналу")
async def join(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.move_to(channel)
            vc = interaction.guild.voice_client
        else:
            vc = await channel.connect()

        await interaction.followup.send(f"Присоединился к {channel.name}!")

        # 1. Запускаем первый звук фоном сразу при входе
        asyncio.create_task(play_sound(vc))

        # 2. Запускаем фоновый цикл для постоянных звуков
        if not sound_loop.is_running():
            sound_loop.start()
    else:
        await interaction.followup.send("Сначала зайдите в голосовой канал!")

bot.run(TOKEN)
