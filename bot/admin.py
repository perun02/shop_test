import asyncio
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    TelegramUser,
    Category,
    Subcategory,
    Product,
    CartItem,
    Order,
    OrderItem,
    Broadcast,
)
from .utils import send_broadcast as send_broadcast_util

# раздел с клиентами Telegram
@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'register_date')
    search_fields = ('telegram_id', 'username', 'first_name')
    ordering = ('-register_date',)


# раздел с категориями товаров
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


# раздел с подкатегориями товаров
@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)
    ordering = ('category', 'name')


# раздел с товарами
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'subcategory', 'created_at', 'image_preview')
    list_filter = ('subcategory__category', 'subcategory')
    search_fields = ('id', 'description')
    readonly_fields = ('created_at', 'image_thumbnail')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = 'Превью'

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" />', obj.image.url)
        return "Нет изображения"
    image_thumbnail.short_description = 'Изображение'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


# раздел с заказами
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'phone_number', 'address', 'is_paid', 'created_at')
    list_filter = ('is_paid',)
    search_fields = ('user__telegram_id', 'full_name', 'phone_number', 'address')
    readonly_fields = ('created_at',)
    inlines = [OrderItemInline]


# раздел с рассылками
@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'sent', 'sent_at')
    list_filter = ('sent',)
    search_fields = ('title', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'sent_at')
    actions = ['send_broadcast_action']

    def send_broadcast_action(self, request, queryset):
        user_ids = list(TelegramUser.objects.values_list('telegram_id', flat=True))
        if not user_ids:
            self.message_user(request, "Нет пользователей для отправки рассылки.", messages.WARNING)
            return

        num_sent = 0
        for broadcast_obj in queryset.filter(sent=False):
            try:
                success_count, failed_ids = asyncio.run(
                    send_broadcast_util(user_ids, broadcast_obj.title, broadcast_obj.message)
                )

                broadcast_obj.sent = True
                broadcast_obj.sent_at = timezone.now()
                broadcast_obj.save()

                num_sent += 1

                message = f"Рассылка '{broadcast_obj.title}' отправлена {success_count} пользователям."
                if failed_ids:
                    message += f" Не удалось отправить {len(failed_ids)} пользователям."

                level = messages.SUCCESS if not failed_ids else messages.WARNING
                self.message_user(request, message, level)

            except Exception as e:
                self.message_user(
                    request,
                    f"Ошибка при отправке рассылки '{broadcast_obj.title}': {str(e)}",
                    messages.ERROR
                )

        if num_sent == 0:
            self.message_user(
                request,
                "Не выбрано новых рассылок для отправки или все уже были отправлены.",
                messages.WARNING
            )

    send_broadcast_action.short_description = "Отправить выбранные рассылки"
