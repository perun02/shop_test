import os
import sys
import asyncio

from dotenv import load_dotenv
from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import Bot, DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не найден в .env")

sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_test.settings')
import django
django.setup()

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

from tg_bot.middleware import LoggingMiddleware
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())

from tg_bot.handlers import (
    start_router, catalog_router, product_router, 
    cart_router, order_router, faq_router, admin_router
)

dp.include_router(start_router)
dp.include_router(catalog_router)
dp.include_router(product_router)
dp.include_router(cart_router)
dp.include_router(order_router)
dp.include_router(faq_router)
dp.include_router(admin_router)

async def main():
    try:
        print("Запускаю бота...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка бота: {e}")
        raise
    finally:
        print("Завершаю работу бота...")
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
