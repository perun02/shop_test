import os
from typing import Optional
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties

# функция для инициализации бота Telegram
async def get_bot() -> Optional[Bot]:
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        return None
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# функция для отправки массовой рассылки пользователям
async def send_broadcast(user_ids: list[int], title: str, message: str) -> tuple[int, list[int]]:
    bot = await get_bot()
    if not bot:
        return 0, user_ids

    success_count = 0
    failed_ids = []
    
    formatted_message = f"<b>{title}</b>\n\n{message}"

    try:
        for user_id in user_ids:
            try:
                await bot.send_message(chat_id=user_id, text=formatted_message)
                success_count += 1
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
                failed_ids.append(user_id)
    finally:
        await bot.session.close()

    return success_count, failed_ids
