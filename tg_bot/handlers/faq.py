from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.markdown import hbold
from aiogram.utils.keyboard import InlineKeyboardBuilder
import hashlib

from bot.models import TelegramUser, CartItem

router = Router()


# простой вывод инфы
faq_database = {
    "доставка": "🚚 Доставка осуществляется по всей России. Сроки доставки: 1-3 дня по Москве, 3-7 дней по России.",
    "оплата": "💳 Мы принимаем оплату картами Visa, MasterCard, МИР, а также наличными при получении.",
    "возврат": "↩️ Возврат товара возможен в течение 14 дней с момента получения при сохранении товарного вида.",
    "режим": "🕒 Мы работаем ежедневно с 9:00 до 21:00 по московскому времени.",
    "контакты": "📞 Телефон: +7 (999) 123-45-67\n📧 Email: support@shop.ru",
    "скидки": "🏷️ У нас действует система скидок: \n- от 5000₽ - скидка 5%\n- от 10000₽ - скидка 10%",
}

topic_emoji = {
    "доставка": "🚚",
    "оплата": "💳",
    "возврат": "↩️",
    "режим": "🕒",
    "контакты": "📞",
    "скидки": "🏷️",
}

@router.inline_query()
async def faq_inline_handler(inline_query: InlineQuery):
    query = inline_query.query.lower()
    results = []
    
    for keyword, answer in faq_database.items():
        if query and not keyword.startswith(query):
            continue
            
        result_id = hashlib.md5(keyword.encode()).hexdigest()
        message_text = f"{hbold(keyword.capitalize())}\n\n{answer}"
        
        item = InlineQueryResultArticle(
            id=result_id,
            title=keyword.capitalize(),
            description=answer[:100] + "..." if len(answer) > 100 else answer,
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode="HTML"
            )
        )
        results.append(item)
    
    if not results:
        help_text = "❓ Доступные команды справки:\n"
        help_text += "\n".join(f"• {key}" for key in faq_database.keys())
        
        results.append(
            InlineQueryResultArticle(
                id="help",
                title="Справка по командам",
                description="Список всех доступных вопросов",
                input_message_content=InputTextMessageContent(
                    message_text=help_text,
                    parse_mode="HTML"
                )
            )
        )
    
    await inline_query.answer(results, cache_time=300)

@router.callback_query(F.data == "show_faq")
async def show_faq_menu(callback: CallbackQuery):
    text = "❓ Выберите интересующую вас тему:"
    
    builder = InlineKeyboardBuilder()
    
    for topic in faq_database.keys():
        builder.button(
            text=f"{topic_emoji.get(topic, '❓')} {topic.capitalize()}", 
            callback_data=f"faq:{topic}"
        )
    
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_start"))
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("faq:"))
async def show_faq_answer(callback: CallbackQuery):
    topic = callback.data.replace("faq:", "")
    
    answer_text = f"{topic_emoji.get(topic, '❓')} {topic.capitalize()}\n\n"
    answer_text += faq_database[topic]
    
    builder = InlineKeyboardBuilder()
    
    for other_topic in faq_database.keys():
        if other_topic != topic:
            builder.button(
                text=f"{topic_emoji.get(other_topic, '❓')} {other_topic.capitalize()}", 
                callback_data=f"faq:{other_topic}"
            )
    
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_start"))
    builder.adjust(1)
    
    await callback.message.edit_text(
        answer_text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    user = callback.from_user
    text = f"🔄 С возвращением, {user.first_name}!"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Каталог", callback_data="show_catalog")
    builder.button(text="FAQ", callback_data="show_faq")
    builder.adjust(2)
    
    user_obj, _ = await TelegramUser.objects.aget_or_create(telegram_id=user.id)
    has_cart_items = await CartItem.objects.filter(user=user_obj).aexists()
    if has_cart_items:
        builder.row(InlineKeyboardButton(text="Корзина", callback_data="view_cart"))
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()