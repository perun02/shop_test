from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# мидлварь для логирования событий бота
class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        logger.info(f"Получено событие: {event.__class__.__name__}")
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка при обработке события: {e}")
            raise
