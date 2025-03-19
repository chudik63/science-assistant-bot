from aiogram import Router, F
from aiogram.types import Message

class AgentHandlers:
    def __init__(self, router: Router):
        self.router = router

        self.router.message.register(self.call_agent,~F.text.startswith("/"))
        
    async def call_agent(self, message: Message):
        if message.voice:
            await message.answer("this message will be transcribed first and then passed to the agent")

            return
        await message.answer("calling agent")

 