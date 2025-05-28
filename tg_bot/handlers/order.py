from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import uuid
from yookassa import Configuration, Payment

from bot.models import CartItem, Order, OrderItem, TelegramUser

# Инициализация ЮKassa
Configuration.account_id = os.getenv('YOOKASSA_SHOP_ID')
Configuration.secret_key = os.getenv('YOOKASSA_SECRET_KEY')

router = Router()


class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_confirmation = State()

# процесс сбора инфы для заказа
@router.callback_query(F.data == "confirm_order")
async def start_order(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.answer(
        "Пожалуйста, введите ваше ФИО:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderStates.waiting_for_name)
    await query.answer()


@router.message(OrderStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if len(message.text) < 3:
        await message.answer("ФИО должно содержать не менее 3 символов. Попробуйте еще раз:")
        return

    await state.update_data(full_name=message.text)
    await message.answer("Введите ваш номер телефона:")
    await state.set_state(OrderStates.waiting_for_phone)


@router.message(OrderStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.replace('+', '').isdigit() or len(phone) < 10:
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return

    await state.update_data(phone_number=phone)
    await message.answer("Введите адрес доставки:")
    await state.set_state(OrderStates.waiting_for_address)


# подтверждение и тд 
@router.message(OrderStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    if len(message.text) < 10:
        await message.answer("Адрес слишком короткий. Пожалуйста, укажите полный адрес доставки:")
        return

    await state.update_data(address=message.text)
    data = await state.get_data()

    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=message.from_user.id)
    cart_items = [
        item async for item in CartItem.objects.filter(user=user_obj).select_related('product')
    ]

    message_text = "📋 Подтвердите данные заказа:\n\n"
    message_text += f"👤 ФИО: {data['full_name']}\n"
    message_text += f"📞 Телефон: {data['phone_number']}\n"
    message_text += f"📍 Адрес: {data['address']}\n\n"
    message_text += "Товары:\n"

    for item in cart_items:
        message_text += f"• {item.product.description} - {item.quantity} шт.\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить заказ", callback_data="complete_order")
    builder.button(text="❌ Отменить", callback_data="cancel_order")
    builder.adjust(1)

    await message.answer(message_text, reply_markup=builder.as_markup())
    await state.set_state(OrderStates.waiting_for_confirmation)


@router.callback_query(F.data == "complete_order")
async def complete_order(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=query.from_user.id)
    cart_items = [item async for item in CartItem.objects.filter(user=user_obj).select_related('product')]

    order = await Order.objects.acreate(
        user=user_obj,
        full_name=data['full_name'],
        phone_number=data['phone_number'],
        address=data['address']
    )

    for cart_item in cart_items:
        await OrderItem.objects.acreate(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity
        )

    payment = Payment.create({
        "amount": {
            "value": "199.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://t.me/shoooptest_bot"
        },
        "capture": True,
        "description": f"Тестовый заказ #{order.id}"
    })

    await Order.objects.filter(id=order.id).aupdate(is_paid=True)

    await CartItem.objects.filter(user=user_obj).adelete()
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💳 Перейти к оплате",
        url=payment.confirmation.confirmation_url
    )

    await query.message.edit_text(
        f"🛍 Заказ #{order.id} успешно создан!\n\n"
        "Нажмите кнопку ниже для оплаты заказа.",
        reply_markup=builder.as_markup()
    )
    await query.answer()

    builder = InlineKeyboardBuilder()
    builder.button(text="В каталог", callback_data="show_catalog")

    await query.message.answer(
        f"✅ Заказ #{order.id} успешно оплачен!\n\n"
        f"📦 Статус: Заказ оформлен и оплачен\n"
        f"👤 Получатель: {data['full_name']}\n"
        f"📞 Телефон: {data['phone_number']}\n"
        f"📍 Адрес доставки: {data['address']}\n\n"
        "Спасибо за покупку! Мы свяжемся с вами для уточнения деталей доставки.",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "cancel_order")
async def cancel_order(query: CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="Вернуться в корзину", callback_data="view_cart")

    await query.message.edit_text(
        "❌ Оформление заказа отменено",
        reply_markup=builder.as_markup()
    )
    await query.answer()
