from django.db import models

# модель пользователя Telegram
class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=150, blank=True, null=True, verbose_name="Username")
    first_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Имя")
    register_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    class Meta:
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"
        ordering = ['-register_date']

    def __str__(self):
        return f"{self.username or self.first_name or self.telegram_id}"


# модель категорий товаров
class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название категории"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name


# модель подкатегорий товаров
class Subcategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name="Родительская категория"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Название подкатегории"
    )

    class Meta:
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"
        unique_together = ('category', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} → {self.name}"


# модель товаров
class Product(models.Model):
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Подкатегория"
    )
    image = models.ImageField(
        upload_to='products/%Y/%m/%d/',
        verbose_name="Фото товара",
        null=True,
        blank=True
    )
    description = models.TextField(
        verbose_name="Описание товара"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата добавления"
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subcategory} - {self.description[:50]}..."


# модель корзины пользователя
class CartItem(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name="Пользователь"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Товар"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Количество"
    )

    class Meta:
        verbose_name = "Позиция в корзине"
        verbose_name_plural = "Позиции в корзине"
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.product} x {self.quantity} для {self.user}"


# модель заказов
class Order(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Пользователь"
    )
    full_name = models.CharField(
        max_length=200,
        verbose_name="ФИО получателя"
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="Номер телефона"
    )
    address = models.CharField(
        max_length=300,
        verbose_name="Адрес доставки"
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name="Оплачен"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания заказа"
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} от {self.user}"


# модель позиций в заказе
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Заказ"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name="Товар"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Количество"
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.product} x {self.quantity}"


# модель рассылок сообщений
class Broadcast(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Заголовок рассылки"
    )
    message = models.TextField(
        verbose_name="Текст сообщения"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    sent = models.BooleanField(
        default=False,
        verbose_name="Отправлено"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата отправки"
    )

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"
