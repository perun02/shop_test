from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from decimal import Decimal

from bot.models import CartItem, TelegramUser, Product

router = Router()

# показывает содержимое корзины пользователя
@router.callback_query(F.data == "view_cart")
async def show_cart(query: CallbackQuery):
    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=query.from_user.id)
    cart_items = [
        item async for item in CartItem.objects.filter(user=user_obj).select_related('product')
    ]
    
    if not cart_items:
        builder = InlineKeyboardBuilder()
        builder.button(text="В каталог", callback_data="show_catalog")
        await query.message.edit_text(
            "Ваша корзина пуста. Выберите товары в каталоге.",
            reply_markup=builder.as_markup()
        )
        await query.answer()
        return

    message_text = "🛒 Ваша корзина:\n\n"
    builder = InlineKeyboardBuilder()
    
    for idx, item in enumerate(cart_items, 1):
        product = item.product
        message_text += f"{idx}. {product.description}\n"
        message_text += f"   Количество: {item.quantity} шт.\n\n"
        builder.button(
            text=f"❌ Удалить {idx}",
            callback_data=f"remove_from_cart:{product.id}"
        )
    
    builder.adjust(2)
    builder.row()
    
    builder.button(text="Очистить корзину", callback_data="clear_cart")
    builder.button(text="Оформить заказ", callback_data="checkout")
    builder.adjust(1)
    builder.row()
    builder.button(text="В каталог", callback_data="show_catalog")
    
    await query.message.edit_text(message_text, reply_markup=builder.as_markup())
    await query.answer()


# очищаем всю корзину пользователя
@router.callback_query(F.data == "clear_cart")
async def clear_cart(query: CallbackQuery):
    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=query.from_user.id)
    await CartItem.objects.filter(user=user_obj).adelete()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="В каталог", callback_data="show_catalog")
    
    await query.message.edit_text(
        "Корзина очищена!",
        reply_markup=builder.as_markup()
    )
    await query.answer()


# удаление конкретного товара из корзины
@router.callback_query(F.data.startswith("remove_from_cart:"))
async def remove_from_cart(query: CallbackQuery):
    product_id = int(query.data.split(":")[1])
    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=query.from_user.id)
    await CartItem.objects.filter(user=user_obj, product_id=product_id).adelete()
    await show_cart(query)


# процесс оформления заказа
@router.callback_query(F.data == "checkout")
async def start_checkout(query: CallbackQuery, state: FSMContext):
    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=query.from_user.id)
    cart_items = [
        item async for item in CartItem.objects.filter(user=user_obj).select_related('product')
    ]
    
    if not cart_items:
        await query.answer("Корзина пуста!", show_alert=True)
        return

    message_text = "📋 Подтверждение заказа\n\n"
    message_text += "Товары в заказе:\n"
    
    for item in cart_items:
        message_text += f"• {item.product.description} - {item.quantity} шт.\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data="confirm_order")
    builder.button(text="Отмена", callback_data="view_cart")
    
    await query.message.edit_text(
        message_text,
        reply_markup=builder.as_markup()
    )
    await query.answer()