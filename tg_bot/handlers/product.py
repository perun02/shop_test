from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os
from typing import Union

from bot.models import Category, Subcategory, Product, CartItem, TelegramUser
from aiogram.exceptions import TelegramBadRequest

router = Router()

class ProductStates(StatesGroup):
    waiting_for_quantity = State() 
    waiting_for_confirmation = State()

# подготовка фотографии товара для отправки
def prepare_product_photo(product):
    if product.image:
        image_path = os.path.join('media', product.image.name)
        if os.path.exists(image_path):
            return FSInputFile(image_path)
    return None

# удаление сообщения с обработкой ошибок
async def _try_delete_message(message):
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

# редактирование сообщения с обработкой ошибок
async def _try_edit_message(message, text=None, reply_markup=None, media=None):
    try:
        if media:
            await message.edit_media(media=media, reply_markup=reply_markup)
        elif text:
            await message.edit_text(text=text, reply_markup=reply_markup)
        return True
    except TelegramBadRequest:
        return False

# отправка или обновление сообщения с информацией о товаре
async def _send_product_message(message_or_query, product, keyboard, is_edit=False):
    caption = f"<b>{product.subcategory.name}</b>\n\n{product.description}"
    photo = prepare_product_photo(product)

    if isinstance(message_or_query, Message):
        if photo:
            await message_or_query.answer_photo(photo=photo, caption=caption, reply_markup=keyboard)
        else:
            await message_or_query.answer(text=f"🖼 [Фото отсутствует]\n\n{caption}", reply_markup=keyboard)
        return

    if photo:
        if message_or_query.message.photo:
            success = await _try_edit_message(
                message_or_query.message,
                media=InputMediaPhoto(media=photo, caption=caption),
                reply_markup=keyboard
            )
            if success:
                return

        await _try_delete_message(message_or_query.message)
        await message_or_query.bot.send_photo(
            chat_id=message_or_query.message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=keyboard
        )
    else:
        success = await _try_edit_message(
            message_or_query.message,
            text=f"🖼 [Фото отсутствует]\n\n{caption}",
            reply_markup=keyboard
        )
        if not success:
            await _try_delete_message(message_or_query.message)
            await message_or_query.bot.send_message(
                chat_id=message_or_query.message.chat.id,
                text=f"🖼 [Фото отсутствует]\n\n{caption}",
                reply_markup=keyboard
            )

# создание клавиатуры для карточки товара
def build_product_keyboard(product, product_count=1):
    builder = InlineKeyboardBuilder()
    if product_count > 1:
        builder.button(text="❮", callback_data="prev_product")
        builder.button(text="❯", callback_data="next_product")
        builder.adjust(2)
    
    builder.row(
        InlineKeyboardButton(text="Добавить в корзину", callback_data="add_to_cart_product"),
        InlineKeyboardButton(text="Назад", callback_data=f"back_to_subcategory:{product.subcategory.id}")
    )
    return builder.as_markup()

# создание клавиатуры для списка подкатегорий
def build_subcategory_keyboard(subcats, add_back_button=True):
    builder = InlineKeyboardBuilder()
    builder.row_width = 2
    for sub in subcats:
        builder.button(text=sub.name, callback_data=f"subcategory:{sub.id}")
    if add_back_button:
        builder.button(text="Назад", callback_data="back_to_categories")
    return builder.as_markup()

# отображение товара по индексу в списке
async def _display_product_at_index(message_or_query: Union[Message, CallbackQuery], state: FSMContext, product_index: int):
    data = await state.get_data()
    product_ids = data.get("products", [])

    if not product_ids or not (0 <= product_index < len(product_ids)):
        if isinstance(message_or_query, CallbackQuery):
            await message_or_query.answer("Товары не найдены или произошла ошибка.", show_alert=True)
        else:
            await message_or_query.answer("Товары не найдены или произошла ошибка.")
        return

    current_product_id = product_ids[product_index]
    product = await Product.objects.select_related('subcategory__category').aget(id=current_product_id)
    await state.update_data(
        index=product_index, 
        current_product_id=current_product_id,
        category_id=product.subcategory.category_id
    )

    keyboard = build_product_keyboard(product, len(product_ids))
    await _send_product_message(message_or_query, product, keyboard, is_edit=True)

# начало навигации по каталогу
@router.message(F.text == "Каталог")
async def show_categories(message: Message):
    categories = [cat async for cat in Category.objects.all()]
    if not categories:
        await message.answer("Категорий пока нет.")
        return

    builder = InlineKeyboardBuilder()
    builder.row_width = 2
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"category:{cat.id}")

    keyboard = builder.as_markup(resize_keyboard=True)
    await message.answer("Выберите категорию:", reply_markup=keyboard)

# выбор подкатегории в каталоге
@router.callback_query(F.data.startswith("category:"))
async def choose_subcategory(query: CallbackQuery):
    category_id = int(query.data.split(":", 1)[1])
    subcats = [sub async for sub in Subcategory.objects.filter(category_id=category_id)]
    if not subcats:
        await query.answer("Подкатегорий пока нет.", show_alert=True)
        return

    keyboard = build_subcategory_keyboard(subcats)
    await query.message.edit_text("Выберите подкатегорию:", reply_markup=keyboard)
    await query.answer()

# возврат к списку категорий
@router.callback_query(F.data == "back_to_categories")
async def back_to_categories_from_subcat_list(query: CallbackQuery, state: FSMContext):
    await state.set_data({}) 
    categories = [cat async for cat in Category.objects.all()]
    if not categories:
        await query.answer("Категорий пока нет.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row_width = 2
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"category:{cat.id}")

    keyboard = builder.as_markup()
    await query.message.edit_text("Выберите категорию:", reply_markup=keyboard)
    await query.answer()

# показ первого товара в выбранной подкатегории
@router.callback_query(F.data.startswith("subcategory:"))
async def show_first_product_in_subcategory(query: CallbackQuery, state: FSMContext):
    sub_id = int(query.data.split(":", 1)[1])
    subcategory = await Subcategory.objects.select_related('category').aget(id=sub_id)
    products_queryset = Product.objects.filter(subcategory_id=sub_id).select_related('subcategory__category')
    product_list = [p async for p in products_queryset]

    if not product_list:
        await query.answer("В этой подкатегории пока нет товаров.", show_alert=True)
        return

    product_ids = [p.id for p in product_list]
    await state.update_data(
        products=product_ids, 
        index=0, 
        current_subcategory_id=sub_id,
        category_id=subcategory.category_id
    )
    
    await _display_product_at_index(query, state, 0)

# переход к следующему товару
@router.callback_query(F.data == "next_product")
async def handle_next_product(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_ids = data.get("products", [])
    if not product_ids:
        await query.answer("Ошибка: список товаров не найден.", show_alert=True)
        return 
    current_index = data.get("index", 0)
    new_index = (current_index + 1) % len(product_ids)
    await _display_product_at_index(query, state, new_index)

# переход к предыдущему товару
@router.callback_query(F.data == "prev_product")
async def handle_prev_product(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_ids = data.get("products", [])
    if not product_ids:
        await query.answer("Ошибка: список товаров не найден.", show_alert=True)
        return
    current_index = data.get("index", 0)
    new_index = (current_index - 1 + len(product_ids)) % len(product_ids)
    await _display_product_at_index(query, state, new_index)

# начало процесса добавления товара в корзину
@router.callback_query(F.data == "add_to_cart_product")
async def add_to_cart_callback(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_product_id = data.get("current_product_id")
    if not current_product_id:
        await query.answer("Ошибка: товар не выбран. Пожалуйста, попробуйте снова.", show_alert=True)
        return
    
    await query.message.answer(
        "Введите количество товара:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(ProductStates.waiting_for_quantity)
    await query.answer()

# обработка введенного количества товара
@router.message(ProductStates.waiting_for_quantity)
async def process_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Пожалуйста, введите корректное положительное число.")
        return

    quantity = int(message.text)
    await state.update_data(quantity=quantity)

    builder = InlineKeyboardBuilder()
    builder.button(text="✔️", callback_data="confirm_add")
    builder.button(text="❌", callback_data="cancel_add")
    keyboard = builder.as_markup()

    await message.answer(f"Добавить {quantity} шт. в корзину?", reply_markup=keyboard)
    await state.set_state(ProductStates.waiting_for_confirmation)

# подтверждение добавления товара в корзину
@router.callback_query(F.data == "confirm_add")
async def confirm_add(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prod_id = data.get("current_product_id") 
    quantity = data.get("quantity", 0)

    if not prod_id or quantity <= 0:
        await query.message.edit_text("Ошибка: Товар или количество не указаны. Попробуйте снова.")
        await state.set_state(None)
        return

    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=query.from_user.id)
    product = await Product.objects.aget(id=prod_id)

    await CartItem.objects.aupdate_or_create(
        user=user_obj,
        product=product,
        defaults={"quantity": quantity}
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="Перейти в корзину", callback_data="view_cart")
    builder.button(text="В каталог", callback_data="back_to_categories")
    keyboard = builder.as_markup()

    await query.message.answer("Товар добавлен в корзину.", reply_markup=keyboard)
    await state.clear()
    await query.answer()

# отмена добавления товара в корзину
@router.callback_query(F.data == "cancel_add")
async def cancel_add(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.answer(
        "Добавление в корзину отменено. Если хотите выбрать другой товар, нажмите 'Каталог'."
    )
    await query.answer()

# возврат к списку подкатегорий
@router.callback_query(F.data.startswith("back_to_subcategory:"))
async def back_to_subcategory(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category_id = data.get("category_id")
    if not category_id:
        await back_to_categories_from_subcat_list(query, state)
        return

    subcats = [sub async for sub in Subcategory.objects.filter(category_id=category_id)]
    if not subcats:
        await query.answer("Подкатегорий пока нет.", show_alert=True)
        return

    keyboard = build_subcategory_keyboard(subcats)
    if not await _try_edit_message(query.message, text="Выберите подкатегорию:", reply_markup=keyboard):
        await _try_delete_message(query.message)
        await query.message.answer("Выберите подкатегорию:", reply_markup=keyboard)
    await query.answer()
