import time
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slow_mode_delay=0.5):
        super().__init__()
        self.user_timeouts = {}
        self.slow_mode_delay = slow_mode_delay

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()

        last_request_time = self.user_timeouts.get(user_id, 0)
        if current_time - last_request_time < self.slow_mode_delay:
            await event.answer("Juda ko'p so'rov! Biroz kuting.")
            return
        else:
            self.user_timeouts[user_id] = current_time
            return await handler(event, data)
