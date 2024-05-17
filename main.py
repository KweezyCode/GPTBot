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

_providers = [
    g4f.Provider.Bing
]


welcome_list = ["Привет! Как я могу помочь тебе сегодня?", 
                "Здравствуй! Чем я могу быть полезен?", 
                "Добро пожаловать! Что вас интересует?", 
                "Здравствуйте! Что вы хотели бы узнать?", 
                "Приветствую! Что вам было бы интересно обсудить?"
]

new_conversation_list = [
    "Начинаем новый диалог. Чем я могу помочь?",
    "Открываем новую беседу. Что вас интересует сегодня?",
    "Новый диалог начат. Готов ответить на ваши вопросы!",
    "Запускаем новую беседу. Что вы хотели бы обсудить?",
    "Начинаем свежий диалог. Чем я могу быть полезен?",
    "Новый диалог открыт. Я здесь, чтобы помочь вам!",
    "Стартуем новую беседу. Что вам было бы интересно узнать?"
]

class UserData:
    def __init__(self):
        self.convId = ""
        self.messagecount = 0
        self.conversation = None
        self.last_message_date = datetime.now()
        self.daily_message_count = 0
        

user_data: dict[str, UserData] = {}

async def run_provider(update: Update, message: str):
    global user_data

    try:
        user_id = str(update.message.chat_id)
        if user_id not in user_data:
            user_data[user_id] = UserData()

        user_data[user_id].messagecount += 1

        if user_data[user_id].conversation and user_data[user_id].messagecount <= 4:
            currentConv = user_data[user_id].conversation
        else:
            currentConv = None
            user_data[user_id].messagecount = 0


        stream = ChatCompletion.create(
            model=g4f.models.default,
            messages=[{"role": "user", "content": message}],
            provider=Provider.Bing,
            stream=True,
            ignore_stream=True,
            return_conversation=True,
            conversation=currentConv
        )
        print("got stream", flush=True)
        response_message = await update.message.reply_text("*Обрабатываю запрос...*", parse_mode=ParseMode.MARKDOWN)

        fullresponse = ""
        i = 0
        print("for loop()", flush=True)
        for chunk in stream:
            print("/", end="", flush=True)
            if isinstance(chunk, Conversation):
                convId = chunk.conversationId
                print("convId", convId, flush=True)
                user_data[user_id].conversation = chunk
                continue

            if chunk:
                fullresponse += chunk
                i += 1
            else:
                break

            if chunk.strip() and i > 20:
                i = 0
                
            try:
                await response_message.edit_text(eeeee(fullresponse + "\n[%s/4]") % (user_data[user_id].messagecount,), parse_mode=ParseMode.MARKDOWN_V2)
            except BadRequest:
                 pass

        if i != 0:
            try:
                await response_message.edit_text(eeeee(fullresponse + "\n[%s/4]") % (user_data[user_id].messagecount,), parse_mode=ParseMode.MARKDOWN_V2)
            except BadRequest:
                pass

        print("", flush=True)
        print("exit", flush=True)

    except Exception:
        print(traceback.print_exc())
        return str(Exception)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # if message == /start then send random welcome message
    if update.message.text == "/start":
        await update.message.reply_text(random.choice(welcome_list))
        return

    if update.message.text == "/convreset":
        await convreset_handler(update, context)
        return

    await run_provider(update, update.message.text)



async def convreset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.chat_id)
    if user_id in user_data:
        user_data[user_id].convId = ""
        user_data[user_id].conversation = None
    await update.message.reply_text(random.choice(new_conversation_list))


def main() -> None:
    application = Application.builder().token("6799409613:AAFvYjTHPkghMkTEbwdiF4LN9Lr_gCiYSZE").build()
    application.add_handler(MessageHandler(filters.TEXT, message_handler))

    print("Started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    print("Stopping...")

if __name__ == "__main__":
    main()
