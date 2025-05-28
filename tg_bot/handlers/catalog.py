from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from bot.models import Category, Subcategory

router = Router()

# показ категорий
@router.callback_query(F.data == "show_catalog")
async def show_categories(query: CallbackQuery):
    categories = [cat async for cat in Category.objects.all()]
    if not categories:
        await query.answer("Категорий пока нет.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row_width = 2
    for cat in categories:
        builder.button(
            text=cat.name,
            callback_data=f"category:{cat.id}"
        )

    keyboard = builder.as_markup()
    await query.message.edit_text("Выберите категорию:", reply_markup=keyboard)
    await query.answer()

# показ подкатегорий
@router.callback_query(F.data.startswith("category:"))
async def choose_subcategory(query: CallbackQuery):
    category_id = int(query.data.split(":", 1)[1])
    subcats = [sub async for sub in Subcategory.objects.filter(category_id=category_id)]
    if not subcats:
        await query.answer("Подкатегорий пока нет.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row_width = 2
    for sub in subcats:
        builder.button(
            text=sub.name,
            callback_data=f"subcategory:{sub.id}"
        )
    builder.button(
        text="Назад",
        callback_data="back_to_categories"
    )

    keyboard = builder.as_markup()
    await query.message.edit_text("Выберите подкатегорию:", reply_markup=keyboard)
    await query.answer()

# возврат к категориям
@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(query: CallbackQuery):
    categories = [cat async for cat in Category.objects.all()]
    if not categories:
        await query.answer("Категорий пока нет.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row_width = 2
    for cat in categories:
        builder.button(
            text=cat.name,
            callback_data=f"category:{cat.id}"
        )

    keyboard = builder.as_markup()
    await query.message.edit_text("Выберите категорию:", reply_markup=keyboard)
    await query.answer()
