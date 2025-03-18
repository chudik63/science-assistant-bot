from repository import Repository
from handlers import Registration
from aiogram.types import Update
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

class UserAuthorizationMiddleware(BaseMiddleware):
    def __init__(self, repository: Repository):
        self.repo = repository

    async def __call__(
        self, handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        
        state = data.get('raw_state')
        user_id = 0

        if event.message:  
            user_id = event.message.from_user.id
            if not event.message.text:
                await data['bot'].send_message(user_id, "Я могу отвечать только на текст!")
                return
            if state and event.message.text.startswith('/'):
                await event.message.answer("В данный момент выполнение команд невозможно.")
                return
        elif event.callback_query:  
            user_id = event.callback_query.from_user.id

        if state in [Registration.name.state, Registration.email.state, Registration.timezone.state]:
            return await handler(event, data)

        
        user = await self.repo.get_user_by_id(user_id)

        if not user and not event.message.text.startswith('/registration') and not event.message.text.startswith('/start'):
            await event.message.answer("Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь, чтобы использовать бота.")
            return
    
        return await handler(event, data)