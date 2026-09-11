import os
import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Настройка намерений бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

sound_task = None


def play_random_sound(vc: discord.VoiceClient):
    """Выборка и воспроизведение случайного звука из папки sounds"""
    sounds_dir = "sounds"

    if not vc.is_connected() or vc.is_playing():
        return

    if os.path.exists(sounds_dir):
        sound_files = [
            f for f in os.listdir(sounds_dir)
            if f.lower().endswith(('.mp3', '.wav'))
        ]
        if sound_files:
            chosen_sound = random.choice(sound_files)
            sound_path = os.path.join(sounds_dir, chosen_sound)
            audio_source = discord.FFmpegPCMAudio(sound_path)
            vc.play(audio_source)


async def random_sound_loop(vc: discord.VoiceClient):
    """Цикл воспроизведения: задержка 1 сек -> звук при входе -> случайные паузы (1-10 мин)"""
    # Даем 1 секунду на то, чтобы голосовое соединение Discord успело установиться
    await asyncio.sleep(1)
    play_random_sound(vc)

    # Цикл с интервалом от 1 до 10 минут (от 60 до 600 секунд)
    while vc.is_connected():
        delay = random.randint(60, 600)
        await asyncio.sleep(delay)

        if not vc.is_connected():
            break

        play_random_sound(vc)


@bot.tree.command(
    name="joinzvukobot",
    description="Призвать бота в голосовой канал по его ID"
)
@app_commands.describe(channel_id="ID голосового канала (число)")
async def join_zvukobot(interaction: discord.Interaction, channel_id: str):
    global sound_task

    # Сообщаем Discord, что команда принята в работу
    await interaction.response.defer()

    try:
        target_id = int(channel_id)
    except ValueError:
        await interaction.followup.send("❌ ID канала должен состоять только из цифр!")
        return

    channel = interaction.guild.get_channel(target_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(target_id)
        except (discord.NotFound, discord.Forbidden):
            await interaction.followup.send("❌ Канал с таким ID не найден или нет доступа!")
            return

    if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        await interaction.followup.send("❌ Указанный ID не принадлежит голосовому каналу!")
        return

    try:
        if interaction.guild.voice_client:
            vc = await interaction.guild.voice_client.move_to(channel)
        else:
            vc = await channel.connect()
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка при подключении к каналу: {e}")
        return

    # Перезапускаем задачу проигрывания звуков
    if sound_task and not sound_task.done():
        sound_task.cancel()

    sound_task = asyncio.create_task(random_sound_loop(vc))

    await interaction.followup.send(
        f"🔊 Бот успешно подключился к каналу **{channel.name}**!"
    )


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Бот {bot.user} успешно запущен и готов к работе!")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Ошибка: Токен не найден в файле .env!")
    else:
        bot.run(token)