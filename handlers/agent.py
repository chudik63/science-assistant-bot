from aiogram import Bot, Router, F
from aiogram.types import Message
import asyncio
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
        self.is_thinking = False

        self.router.message.register(self.call_agent, ~F.text.startswith("/"))
        
    async def call_agent(self, message: Message, bot: Bot):
        text = message.text

        # Если сообщение голосовое, производим распознавание
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

        result_queue = asyncio.Queue()

        # Запускаем анимацию "думаю" как отдельную задачу
        self.is_thinking = True
        thinking_task = asyncio.create_task(self.simulate_thinking(message))

        # Запускаем обработку запроса в отдельном потоке, чтобы не блокировать event loop
        await self.process_request(text, result_queue)

        result = await result_queue.get()

        # Останавливаем анимацию и ждем её завершения
        self.is_thinking = False  
        await thinking_task

        await message.answer(result)
    
    async def process_request(self, text: str, result_queue: asyncio.Queue):
        request = text + "\nIf there is a query linked with article then send the user a pdf_url. It's so important"
        loop = asyncio.get_running_loop()
        # Запускаем синхронную функцию в executor
        res = await loop.run_in_executor(None, self.agent.run_agent, request)
        await result_queue.put(res)
    
    async def simulate_thinking(self, message: Message):
        thinking = "Думаю"
        dot = "."
        think = await message.answer(thinking)
        c = 1
        while self.is_thinking:
            if c == 4:
                c = 0
            await asyncio.sleep(1)
            await think.edit_text(thinking + dot * c)
            c += 1
        # По завершении анимации можно удалить сообщение
        await think.delete()