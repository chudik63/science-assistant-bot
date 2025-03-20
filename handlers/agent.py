from aiogram import Bot, Router, F
from aiogram.types import Message
import whisper
from moviepy import AudioFileClip
import uuid
from datetime import datetime
import os

model = whisper.load_model("base", device="cpu")

class AgentHandlers:
    def __init__(self, router: Router):
        self.router = router

        self.router.message.register(self.call_agent,~F.text.startswith("/"))
        
    async def call_agent(self, message: Message, bot: Bot):
        if message.voice:
            file_id = message.voice.file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:6]
            voice_name = f"voice_{timestamp}_{unique_id}"

            voice_ogg = f"{voice_name}.ogg"
            voice_wav = f"{voice_name}.wav"

            await bot.download_file(file_path, voice_ogg)

            clip = AudioFileClip(voice_ogg)
            clip.write_audiofile(voice_wav)

            os.remove(voice_ogg)

            result = model.transcribe(voice_wav, fp16=False, language="ru")
            text = result["text"]

            await message.answer(f"Распознанный текст: {text}")

            os.remove(voice_wav)

            return
        await message.answer("calling agent")

 