"""
Модуль интеграции с Telegram для AI-ассистента Лиза.
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime
from pathlib import Path

from telegram import (
    Update,
    Bot,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from telegram.error import TelegramError


class TelegramBot:
    """Класс для работы с Telegram ботом."""

    # Состояния для ConversationHandler
    AWAITING_INPUT, AWAITING_CONFIRMATION = range(2)

    def __init__(self, token: str, allowed_chat_ids: List[int] = None,
                 admin_ids: List[int] = None, data_dir: str = "data/telegram"):
        self.logger = logging.getLogger(__name__)
        self.token = token
        self.allowed_chat_ids = allowed_chat_ids or []
        self.admin_ids = admin_ids or []
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.application = None
        self.bot = None

        # Обработчики команд
        self.command_handlers = {}
        self.message_handlers = []
        self.callback_handlers = {}

        # Система состояний пользователей
        self.user_states = {}

        # Кэш для хранения временных данных
        self.user_data_cache = {}

        # Загрузка сохраненных данных
        self.load_data()

    def load_data(self):
        """Загрузка сохраненных данных."""
        states_file = self.data_dir / "user_states.json"
        cache_file = self.data_dir / "user_data_cache.json"

        try:
            if states_file.exists():
                with open(states_file, 'r', encoding='utf-8') as f:
                    self.user_states = json.load(f)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки состояний пользователей: {e}")

        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.user_data_cache = json.load(f)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кэша данных: {e}")

    def save_data(self):
        """Сохранение данных."""
        states_file = self.data_dir / "user_states.json"
        cache_file = self.data_dir / "user_data_cache.json"

        try:
            with open(states_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения состояний пользователей: {e}")

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения кэша данных: {e}")

    async def initialize(self):
        """Инициализация бота."""
        try:
            self.application = (
                ApplicationBuilder()
                .token(self.token)
                .concurrent_updates(True)
                .build()
            )
            self.bot = self.application.bot

            # Регистрация обработчиков
            self._register_handlers()

            self.logger.info("Telegram бот инициализирован")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации Telegram бота: {e}")
            return False

    def _register_handlers(self):
        """Регистрация обработчиков команд и сообщений."""
        # Базовые обработчики команд
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("cancel", self._handle_cancel))

        # Административные команды
        self.application.add_handler(CommandHandler("admin", self._handle_admin))
        self.application.add_handler(CommandHandler("broadcast", self._handle_broadcast))

        # Обработчик инлайн-кнопок
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))

        # Обработчики различных типов сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))
        self.application.add_handler(MessageHandler(filters.DOCUMENT, self._handle_document))
        self.application.add_handler(MessageHandler(filters.VOICE, self._handle_voice))

        # Conversation handler для многошаговых взаимодействий
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("setup", self._handle_setup)],
            states={
                self.AWAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_setup_input)],
                self.AWAITING_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_setup_confirmation)]
            },
            fallbacks=[CommandHandler("cancel", self._handle_cancel)]
        )
        self.application.add_handler(conv_handler)

        # Регистрация пользовательских обработчиков команд
        for command, handler in self.command_handlers.items():
            self.application.add_handler(CommandHandler(command, handler))

        # Обработчик ошибок
        self.application.add_error_handler(self._handle_error)

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start."""
        chat_id = update.effective_chat.id
        user = update.effective_user

        # Проверка доступа
        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен. Обратитесь к администратору.")
            return

        # Сохранение информации о пользователе
        self._save_user_info(user)

        welcome_text = """
        👋 Привет! Я AI-ассистент Лиза.

        Я могу помочь с:
        • Автоматизацией задач
        • Генерацией и анализом кода
        • Мониторингом системы
        • Управлением ресурсами

        Используйте /help для списка команд.
        """

        # Клавиатура с основными командами
        keyboard = [
            [KeyboardButton("/help"), KeyboardButton("/status")],
            [KeyboardButton("/tasks"), KeyboardButton("/monitor")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

        # Логирование начала работы
        self._log_interaction(chat_id, user.username, "start", "success")

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help."""
        chat_id = update.effective_chat.id

        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен")
            return

        help_text = """
        📋 Доступные команды:

        /start - Начать работу
        /help - Показать справку
        /status - Статус системы
        /setup - Настройка параметров
        /cancel - Отмена текущей операции

        🔧 Системные команды:
        /tasks - Управление задачами
        /monitor - Мониторинг ресурсов
        /analyze - Анализ кода

        💬 Просто отправьте текстовое сообщение для выполнения действий.
        """

        # Инлайн-кнопки для быстрого доступа
        inline_keyboard = [
            [InlineKeyboardButton("Статус системы", callback_data="status")],
            [InlineKeyboardButton("Список задач", callback_data="tasks")],
            [InlineKeyboardButton("Мониторинг", callback_data="monitor")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        await update.message.reply_text(help_text, reply_markup=reply_markup)

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /status."""
        chat_id = update.effective_chat.id

        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен")
            return

        # TODO: Получение реального статуса системы
        status_text = """
        📊 Статус системы:

        • CPU: 45% ✅
        • Память: 60% ⚠️
        • Диск: 75% ⚠️
        • Сеть: 100Mbps ✅

        🟢 Все системы работают нормально.
        """

        await update.message.reply_text(status_text)

    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /cancel."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Сброс состояния пользователя
        if str(user_id) in self.user_states:
            del self.user_states[str(user_id)]
            self.save_data()

        await update.message.reply_text(
            "❌ Текущая операция отменена.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def _handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка административных команд."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if not self._check_admin_access(user_id):
            await update.message.reply_text("🚫 Недостаточно прав для выполнения этой команды.")
            return

        admin_text = """
        ⚙️ Административная панель:

        /broadcast - Рассылка сообщения
        /stats - Статистика использования
        /logs - Просмотр логов
        /users - Управление пользователями
        """

        await update.message.reply_text(admin_text)

    async def _handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды рассылки."""
        user_id = update.effective_user.id

        if not self._check_admin_access(user_id):
            await update.message.reply_text("🚫 Недостаточно прав для выполнения этой команды.")
            return

        # Установка состояния ожидания сообщения для рассылки
        self.user_states[str(user_id)] = {
            'state': 'awaiting_broadcast',
            'timestamp': datetime.now().isoformat()
        }
        self.save_data()

        await update.message.reply_text(
            "📢 Введите сообщение для рассылки:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/cancel")]], resize_keyboard=True)
        )

    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message_text = update.message.text

        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен")
            return

        # Проверка состояния пользователя
        user_state = self.user_states.get(str(user_id), {})

        if user_state.get('state') == 'awaiting_broadcast':
            # Обработка сообщения для рассылки
            await self._process_broadcast(update, message_text)
            return

        # Вызов пользовательских обработчиков
        handled = False
        for handler in self.message_handlers:
            try:
                result = await handler(update, context, message_text)
                if result:
                    handled = True
                    break
            except Exception as e:
                self.logger.error(f"Ошибка в обработчике сообщений: {e}")

        # Ответ по умолчанию, если ни один обработчик не сработал
        if not handled:
            default_response = f"🔍 Получена команда: {message_text}\n\nИспользуйте /help для списка доступных команд."
            await update.message.reply_text(default_response)

        # Логирование взаимодействия
        self._log_interaction(chat_id, update.effective_user.username, "message", message_text)

    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на инлайн-кнопки."""
        query = update.callback_query
        await query.answer()  # Ответим на callback, чтобы убрать "часики"

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        callback_data = query.data

        if not self._check_access(chat_id):
            await query.edit_message_text("🚫 Доступ запрещен")
            return

        # Вызов зарегистрированных обработчиков callback
        if callback_data in self.callback_handlers:
            try:
                await self.callback_handlers[callback_data](update, context)
            except Exception as e:
                self.logger.error(f"Ошибка в обработчике callback: {e}")
                await query.edit_message_text("❌ Произошла ошибка при обработке запроса.")
        else:
            # Обработка стандартных callback
            if callback_data == "status":
                await self._handle_status(update, context)
            elif callback_data == "tasks":
                await query.edit_message_text("📋 Функционал управления задачами в разработке...")
            elif callback_data == "monitor":
                await query.edit_message_text("📊 Функционал мониторинга в разработке...")

        # Логирование взаимодействия
        self._log_interaction(chat_id, update.effective_user.username, "callback", callback_data)

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий."""
        chat_id = update.effective_chat.id

        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен")
            return

        # TODO: Реализовать обработку фотографий
        await update.message.reply_text("📸 Получено изображение. Обработка изображений в разработке...")

    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка документов."""
        chat_id = update.effective_chat.id

        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен")
            return

        # TODO: Реализовать обработку документов
        document = update.message.document
        await update.message.reply_text(f"📄 Получен документ: {document.file_name}")

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений."""
        chat_id = update.effective_chat.id

        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен")
            return

        # TODO: Реализовать обработку голосовых сообщений
        await update.message.reply_text("🎤 Получено голосовое сообщение. Обработка аудио в разработке...")

    async def _handle_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса настройки."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if not self._check_access(chat_id):
            await update.message.reply_text("🚫 Доступ запрещен")
            return ConversationHandler.END

        # Установка состояния пользователя
        self.user_states[str(user_id)] = {
            'state': 'setup',
            'step': 'awaiting_language',
            'timestamp': datetime.now().isoformat()
        }
        self.save_data()

        await update.message.reply_text(
            "🌍 Выберите язык / Select language:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("Русский"), KeyboardButton("English")],
                [KeyboardButton("/cancel")]
            ], resize_keyboard=True)
        )

        return self.AWAITING_INPUT

    async def _handle_setup_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода во время настройки."""
        user_id = update.effective_user.id
        message_text = update.message.text
        user_state = self.user_states.get(str(user_id), {})

        if user_state.get('step') == 'awaiting_language':
            # Сохранение выбора языка
            if message_text in ["Русский", "Russian"]:
                language = "ru"
            else:
                language = "en"

            self.user_data_cache[str(user_id)] = {
                'language': language,
                'setup_step': 'language_selected'
            }
            self.save_data()

            # Переход к следующему шагу
            self.user_states[str(user_id)]['step'] = 'awaiting_confirmation'
            self.save_data()

            await update.message.reply_text(
                f"✅ Язык установлен: {message_text}\n\n"
                "Подтвердите настройку или введите /cancel для отмены:",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("Подтвердить"), KeyboardButton("Отменить")],
                    [KeyboardButton("/cancel")]
                ], resize_keyboard=True)
            )

            return self.AWAITING_CONFIRMATION

        return self.AWAITING_INPUT

    async def _handle_setup_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения настройки."""
        user_id = update.effective_user.id
        message_text = update.message.text

        if message_text.lower() in ["подтвердить", "confirm"]:
            # Завершение настройки
            user_data = self.user_data_cache.get(str(user_id), {})
            # TODO: Сохранение настроек пользователя

            await update.message.reply_text(
                "✅ Настройка завершена!",
                reply_markup=ReplyKeyboardRemove()
            )

            # Очистка временных данных
            if str(user_id) in self.user_data_cache:
                del self.user_data_cache[str(user_id)]
            if str(user_id) in self.user_states:
                del self.user_states[str(user_id)]
            self.save_data()

            return ConversationHandler.END
        else:
            # Отмена настройки
            await update.message.reply_text(
                "❌ Настройка отменена.",
                reply_markup=ReplyKeyboardRemove()
            )

            # Очистка временных данных
            if str(user_id) in self.user_data_cache:
                del self.user_data_cache[str(user_id)]
            if str(user_id) in self.user_states:
                del self.user_states[str(user_id)]
            self.save_data()

            return ConversationHandler.END

    async def _process_broadcast(self, update: Update, message_text: str):
        """Обработка рассылки сообщения."""
        user_id = update.effective_user.id

        # Отправка сообщения всем пользователям
        success_count = 0
        fail_count = 0

        for chat_id in self.allowed_chat_ids:
            try:
                await self.send_message(chat_id, f"📢 Рассылка:\n\n{message_text}")
                success_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка отправки рассылки в чат {chat_id}: {e}")
                fail_count += 1

        # Сброс состояния пользователя
        if str(user_id) in self.user_states:
            del self.user_states[str(user_id)]
        self.save_data()

        await update.message.reply_text(
            f"📊 Рассылка завершена:\n\n• Успешно: {success_count}\n• Не удалось: {fail_count}",
            reply_markup=ReplyKeyboardRemove()
        )

    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ошибок."""
        self.logger.error(f"Ошибка в обработчике Telegram: {context.error}")

        if update and update.effective_chat:
            try:
                await update.effective_chat.send_message(
                    "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
                )
            except Exception as e:
                self.logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

    def _check_access(self, chat_id: int) -> bool:
        """Проверка доступа к боту."""
        if not self.allowed_chat_ids:  # Если список пустой, доступ для всех
            return True
        return chat_id in self.allowed_chat_ids

    def _check_admin_access(self, user_id: int) -> bool:
        """Проверка административного доступа."""
        if not self.admin_ids:  # Если список пустой, доступ для всех
            return True
        return user_id in self.admin_ids

    def _save_user_info(self, user):
        """Сохранение информации о пользователе."""
        user_file = self.data_dir / "users.json"
        users = {}

        try:
            if user_file.exists():
                with open(user_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
        except Exception as e:
            self.logger.error(f"Ошибка загрузки информации о пользователях: {e}")

        # Обновление информации о пользователе
        users[str(user.id)] = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'last_seen': datetime.now().isoformat()
        }

        try:
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения информации о пользователях: {e}")

    def _log_interaction(self, chat_id: int, username: str, action: str, details: str):
        """Логирование взаимодействия с пользователем."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'chat_id': chat_id,
            'username': username,
            'action': action,
            'details': details
        }

        log_file = self.data_dir / "interactions.log"

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"Ошибка записи в лог взаимодействий: {e}")

    def add_command_handler(self, command: str, handler: Callable):
        """Добавление обработчика команды."""
        self.command_handlers[command] = handler

        # Если приложение уже инициализировано, перерегистрируем обработчики
        if self.application:
            self.application.add_handler(CommandHandler(command, handler))

    def add_message_handler(self, handler: Callable):
        """Добавление обработчика сообщений."""
        self.message_handlers.append(handler)

    def add_callback_handler(self, callback_data: str, handler: Callable):
        """Добавление обработчика callback."""
        self.callback_handlers[callback_data] = handler

    async def send_message(self, chat_id: int, text: str,
                           keyboard: Optional[List[List[KeyboardButton]]] = None,
                           inline_keyboard: Optional[List[List[InlineKeyboardButton]]] = None,
                           parse_mode: Optional[str] = None) -> bool:
        """
        Отправка сообщения в Telegram.

        Args:
            chat_id: ID чата
            text: Текст сообщения
            keyboard: Обычная клавиатура (опционально)
            inline_keyboard: Инлайн-клавиатура (опционально)
            parse_mode: Режим парсинга (Markdown, HTML)

        Returns:
            True если сообщение отправлено успешно
        """
        try:
            reply_markup = None

            if keyboard:
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            elif inline_keyboard:
                reply_markup = InlineKeyboardMarkup(inline_keyboard)

            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )

            self.logger.info(f"Сообщение отправлено в чат {chat_id}")
            return True

        except TelegramError as e:
            self.logger.error(f"Ошибка отправки сообщения в Telegram: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка при отправке сообщения: {e}")
            return False

    async def send_document(self, chat_id: int, document_path: str,
                           caption: Optional[str] = None) -> bool:
        """
        Отправка документа в Telegram.

        Args:
            chat_id: ID чата
            document_path: Путь к документу
            caption: Подпись к документу (опционально)

        Returns:
            True если документ отправлен успешно
        """
        try:
            with open(document_path, 'rb') as doc:
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=doc,
                    caption=caption
                )

            self.logger.info(f"Документ отправлен в чат {chat_id}")
            return True

        except TelegramError as e:
            self.logger.error(f"Ошибка отправки документа в Telegram: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка при отправке документа: {e}")
            return False

    async def start_polling(self):
        """Запуск polling для получения сообщений."""
        if not self.application:
            await self.initialize()

        try:
            self.logger.info("Запуск polling Telegram бота")
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            self.logger.error(f"Ошибка polling Telegram бота: {e}")

    async def stop(self):
        """Остановка бота."""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
            self.logger.info("Telegram бот остановлен")

    def run(self):
        """Запуск бота в синхронном режиме."""
        try:
            asyncio.run(self.start_polling())
        except KeyboardInterrupt:
            self.logger.info("Остановка Telegram бота")
            asyncio.run(self.stop())