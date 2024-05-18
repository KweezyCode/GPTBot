# Импортируем необходимые библиотеки и модули
import logging
from collections import deque
import g4f # type: ignore
from g4f.Provider.Bing import Conversation # type: ignore
from g4f import Provider, ChatCompletion # type: ignore
from md2tgmd import escape as eeeee # type: ignore
from telegram.constants import ParseMode # type: ignore
from telegram import ForceReply, Update # type: ignore
from telegram.ext import Application, MessageHandler, filters, ContextTypes # type: ignore
from telegram.error import BadRequest # type: ignore
from telegram.ext import CommandHandler # type: ignore
from datetime import datetime, timedelta
import traceback
import random

# Определяем константы
DAILY_MESSAGE_LIMIT = 50  # Максимальное количество сообщений в день
MAX_MESSAGE_COUNT = 4  # Максимальное количество сообщений в одном диалоге


# Определяем список провайдеров
_providers = [
    g4f.Provider.Bing
]

# Определяем список приветственных сообщений
welcome_list = [
    "Привет! Как я могу помочь тебе сегодня?", 
    "Здравствуй! Чем я могу быть полезен?", 
    "Добро пожаловать! Что вас интересует?", 
    "Здравствуйте! Что вы хотели бы узнать?", 
    "Приветствую! Что вам было бы интересно обсудить?"
]

# Определяем список сообщений для начала нового диалога
new_conversation_list = [
    "Начинаем новый диалог. Чем я могу помочь?",
    "Открываем новую беседу. Что вас интересует сегодня?",
    "Новый диалог начат. Готов ответить на ваши вопросы!",
    "Запускаем новую беседу. Что вы хотели бы обсудить?",
    "Начинаем свежий диалог. Чем я могу быть полезен?",
    "Новый диалог открыт. Я здесь, чтобы помочь вам!",
    "Стартуем новую беседу. Что вам было бы интересно узнать?"
]

# Определяем класс UserData для хранения информации о пользователе
class UserData:
    def __init__(self):
        self.convId = "" # ID диалога
        self.messagecount = 0 # Количество сообщений
        self.conversation = None # Текущий диалог
        self.last_message_date = datetime.now() # Дата последнего сообщения
        self.daily_message_count = 0 # Количество сообщений в день

# Создаем словарь для хранения данных пользователей
user_data: dict[str, UserData] = {}

def fibonacci():
    a, b = 0, 1
    while True:
        a, b = b, a + b
        yield a

# Определяем функцию для обработки сообщений от провайдера
async def run_provider(update: Update, message: str):
    print(message)
    global user_data
    try:
        user_id = str(update.message.chat_id)
        if user_id not in user_data:
            user_data[user_id] = UserData()

        # Проверяем, не достиг ли пользователь лимита сообщений в день
        if user_data[user_id].daily_message_count >= DAILY_MESSAGE_LIMIT and user_data[user_id].last_message_date.date() == datetime.now().date():
            # Вычисляем время до конца суток
            now = datetime.now()
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            wait_time = midnight - now

            # Форматируем время ожидания в часы и минуты
            wait_hours, remainder = divmod(wait_time.seconds, 3600)
            wait_minutes, _ = divmod(remainder, 60)

            await update.message.reply_text(f"Вы достигли лимита сообщений на сегодня. Пожалуйста, попробуйте через {wait_hours} часов {wait_minutes} минут.")
            return

        # Сбрасываем лимиты на следующий день 
        if user_data[user_id].last_message_date.date() < datetime.now().date():
            user_data[user_id].daily_message_count = 0

        # Проверяем, не достиг ли пользователь лимита сообщений в диалоге
        if user_data[user_id].conversation and user_data[user_id].messagecount <= MAX_MESSAGE_COUNT:
            currentConv = user_data[user_id].conversation
        else:
            currentConv = None
            user_data[user_id].messagecount = 0

        # Увеличиваем счетчик сообщений
        user_data[user_id].messagecount += 1
        user_data[user_id].daily_message_count += 1
        user_data[user_id].last_message_date = datetime.now()

        # Создаем поток сообщений
        stream = ChatCompletion.create(
            model=g4f.models.default,
            messages=[{"role": "user", "content": message}],
            provider=Provider.Bing,
            stream=True,
            ignore_stream=True,
            return_conversation=True,
            conversation=currentConv
        )

        # Отправляем сообщение о начале обработки запроса
        response_message = await update.message.reply_text("*Обрабатываю запрос...*", parse_mode=ParseMode.MARKDOWN)

        fullresponse = ""


        # использовано для ограничения количества обработанных сообщений за один раз, 
        # чтобы избежать перегрузки
        i = 0

        fib = fibonacci()
        cur = next(fib)

        # Обрабатываем поток сообщений
        for chunk in stream:
            if isinstance(chunk, Conversation):
                user_data[user_id].conversation = chunk
                continue

            if chunk:
                fullresponse += chunk
                i += 1
            else:
                break
            
            
            if chunk.strip() and i > (cur + 5):
                i = 0
                cur = next(fib)
                try:
                    await response_message.edit_text(eeeee(fullresponse + "\n[%s/%s | %s/%s]") % (user_data[user_id].messagecount,MAX_MESSAGE_COUNT,user_data[user_id].daily_message_count,DAILY_MESSAGE_LIMIT), parse_mode=ParseMode.MARKDOWN_V2)
                except BadRequest:
                    pass
                    print("BadRequest")

        if i != 0:
            try:
                await response_message.edit_text(eeeee(fullresponse + "\n[%s/%s | %s/%s]") % (user_data[user_id].messagecount,MAX_MESSAGE_COUNT,user_data[user_id].daily_message_count,DAILY_MESSAGE_LIMIT), parse_mode=ParseMode.MARKDOWN_V2)
            except BadRequest:
                pass
                print("BadRequest")
        print(fullresponse)

    except Exception:
        print(traceback.print_exc())
        return str(Exception)

# Определяем обработчик сообщений
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "/start":
        await update.message.reply_text(random.choice(welcome_list))
        return

    if update.message.text == "/convreset":
        await convreset_handler(update, context)
        return

    await run_provider(update, update.message.text)

# Определяем обработчик для сброса диалога
async def convreset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.chat_id)
    if user_id in user_data:
        user_data[user_id].convId = ""
        user_data[user_id].conversation = None
    await update.message.reply_text(random.choice(new_conversation_list))

# Определяем основную функцию
def main() -> None:
    application = Application.builder().token("6799409613:AAFvYjTHPkghMkTEbwdiF4LN9Lr_gCiYSZE").build()
    application.add_handler(MessageHandler(filters.TEXT, message_handler))

    print("Started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    print("Stopping...")

# Запускаем основную функцию
if __name__ == "__main__":
    main()