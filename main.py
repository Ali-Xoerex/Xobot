#!/usr/bin/python

from telegram import Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackContext, CommandHandler, CallbackQueryHandler

request_kargs = {"proxy_url":"http://127.0.0.1:62178"} # Hard-coded only for test

updater = Updater(token="5652106016:AAFUm4917Re2TmHpL1IZc1lPGgmPv49K3Cg", request_kwargs=request_kargs)

dispatcher = updater.dispatcher

def start(update,context):
    menu = [
        [InlineKeyboardButton("Define Task",callback_data="1"),
        InlineKeyboardButton("Show Tasks",callback_data="2")]
    ]
    reply_markup = InlineKeyboardMarkup(menu)
    context.bot.send_message(chat_id=update.effective_chat.id, text="How can I be of service?",reply_markup=reply_markup)

def define_task(update,context):
    query = update.callback_query
    query.answer()
    if not context.user_data.get("state"):
        context.user_data["state"] = "define_title"
        context.bot.send_message(chat_id=update.effective_chat.id, text="Let's create new Task\n What would be the title?")    

def show_tasks(update,context):
    query = update.callback_query
    query.answer()
    if not context.user_data.get("state"):
        context.bot.send_message(chat_id=update.effective_chat.id, text="You pressed show button")


start_handler = CommandHandler("start",start)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(CallbackQueryHandler(define_task,pattern="1"))
dispatcher.add_handler(CallbackQueryHandler(show_tasks,pattern="2"))

updater.start_polling()

updater.idle()