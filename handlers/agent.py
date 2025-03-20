from aiogram import Bot, Router, F
from aiogram.types import Message
import whisper
import ffmpeg
import uuid
from datetime import datetime
import os
from agent import Agent

model = whisper.load_model("base", device="cpu")

class AgentHandlers:
    def __init__(self, router: Router, agent: Agent):
        self.router = router
        self.agent = agent

        self.router.message.register(self.call_agent,~F.text.startswith("/"))
        
    async def call_agent(self, message: Message, bot: Bot):
        text = message.text
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

            ffmpeg.input(voice_ogg).output(voice_wav, ar=16000, ac=1).run()

            os.remove(voice_ogg)

            result = model.transcribe(voice_wav, fp16=False, language="ru")
            text = result["text"]

            os.remove(voice_wav)

        await message.answer("Думаю...")
        
        request = text + "\nIf there is a query linked with article then send the user a pdf_url. It's so important"
        result = self.agent.run_agent(request)

        await message.answer(result)

 