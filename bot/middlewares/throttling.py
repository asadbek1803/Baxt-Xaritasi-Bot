import time
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from bot.constants import Messages
from typing import Callable, Dict, Any, Awaitable, Union


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slow_mode_delay=0.5):
        super().__init__()
        self.user_timeouts = {}
        self.slow_mode_delay = slow_mode_delay

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()

        last_request_time = self.user_timeouts.get(user_id, 0)
        if current_time - last_request_time < self.slow_mode_delay:
            if isinstance(event, Message):
                await event.answer(text=Messages.too_requests.value)
            elif isinstance(event, CallbackQuery):
                await event.answer(text=Messages.too_requests.value, show_alert=True)
            return
        else:
            self.user_timeouts[user_id] = current_time
            return await handler(event, data)
