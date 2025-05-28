from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.models import TelegramUser, CartItem

router = Router()

@router.message(Command(commands=["start"]))
async def start_handler(message: Message):
    user = message.from_user
    obj, created = await TelegramUser.objects.aget_or_create(
        telegram_id=user.id,
        defaults={
            'username': user.username or "",
            'first_name': user.first_name or "",
        }
    )

    if created:
        text = f"👋 Привет, {user.first_name}! Вы успешно зарегистрированы."
    else:
        text = f"🔄 С возвращением, {user.first_name}! Вы уже зарегистрированы."

    builder = InlineKeyboardBuilder()
    builder.button(text="Каталог", callback_data="show_catalog")
    builder.button(text="FAQ", callback_data="show_faq")
    builder.adjust(2)

    has_cart_items = await CartItem.objects.filter(user=obj).aexists()
    if has_cart_items:
        builder.row(InlineKeyboardButton(text="Корзина", callback_data="view_cart"))

    keyboard = builder.as_markup()
    await message.answer(text, reply_markup=keyboard)
