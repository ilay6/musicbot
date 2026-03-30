import os
import asyncio
import tempfile

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import BotCommand, BufferedInputFile
from aiogram.methods import DeleteWebhook
from dotenv import load_dotenv

load_dotenv()

MUSIC_BOT_TOKEN = os.getenv("MUSIC_BOT_TOKEN", "")

bot = Bot(MUSIC_BOT_TOKEN) if MUSIC_BOT_TOKEN else None
dp = Dispatcher()

YT_DLP = "yt-dlp"


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "🎵 <b>Музыкальный бот</b>\n\n"
        "Просто напиши название трека или артиста, например:\n"
        "<code>Eminem - Lose Yourself</code>\n"
        "<code>Нервы - Всё</code>\n\n"
        "Я найду и пришлю музыку 🎧",
        parse_mode="HTML"
    )


@dp.message(F.text)
async def download_music(message: types.Message):
    query = message.text.strip()
    if not query:
        return

    status = await message.answer("🔍 Ищу трек...")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(title)s.%(ext)s")

        # Search SoundCloud (no restrictions unlike YouTube)
        cmd = [
            YT_DLP,
            f"scsearch1:{query}",
            "--format", "bestaudio/best",
            "--output", output_template,
            "--no-playlist",
            "--max-filesize", "50m",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            err_text = stderr.decode(errors="ignore")

            if proc.returncode != 0:
                print(f"yt-dlp error: {err_text}")
                await status.edit_text("❌ Не удалось найти трек. Попробуй уточнить название.")
                return

            # Find downloaded file
            files = os.listdir(tmpdir)
            audio_files = [f for f in files if not f.endswith(".part")]
            if not audio_files:
                await status.edit_text("❌ Файл не найден после скачивания.")
                return

            audio_path = os.path.join(tmpdir, audio_files[0])
            file_size = os.path.getsize(audio_path)

            if file_size > 50 * 1024 * 1024:
                await status.edit_text("❌ Файл слишком большой (>50MB).")
                return

            await status.edit_text("📤 Отправляю...")

            filename = audio_files[0]
            title = os.path.splitext(filename)[0]

            with open(audio_path, "rb") as f:
                audio_data = f.read()

            await message.answer_audio(
                audio=BufferedInputFile(audio_data, filename=filename),
                title=title,
                caption="🎵 Готово!"
            )
            await status.delete()

        except asyncio.TimeoutError:
            await status.edit_text("⏱ Превышено время ожидания. Попробуй ещё раз.")
        except Exception as e:
            print(f"Download error: {e}")
            await status.edit_text("❌ Произошла ошибка при скачивании.")


async def run_polling():
    if not bot:
        print("No MUSIC_BOT_TOKEN set. Add it to .env")
        return
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу с ботом"),
    ])
    await bot(DeleteWebhook(drop_pending_updates=True))
    print("Music bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_polling())
