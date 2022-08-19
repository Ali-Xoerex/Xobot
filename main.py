#!/usr/bin/python

import datetime

from telegram import Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

months = {"January": 1, "February":2, "March": 3, "April":4, "May": 5, "June": 6, "July":7, "August":8, "September":9, "October":10, "November":11, "December": 12}
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
        context.user_data["task"] = {}
        context.bot.send_message(chat_id=update.effective_chat.id, text="Let's create new Task\n What would be the title?")    

def show_tasks(update,context):
    query = update.callback_query
    query.answer()
    if not context.user_data.get("state"):
        context.bot.send_message(chat_id=update.effective_chat.id, text="You pressed show button")

def text_handler(update,context):
    state = context.user_data.get("state")
    if state:
        if state == "define_title":
            context.user_data["task"]["title"] = update.message.text
            context.bot.send_message(chat_id=update.effective_chat.id, text="Got it!\nNow tell me when is it due?")
            context.user_data["state"] = "define_due"
        if state == "define_due":
            due_date = update.message.text.split(" ")
            due_time = due_date[0].split(":")
            due_hour = int(due_time[0])
            due_minute = int(due_time[1])
            due_day = int(due_date[1])
            due_month = months[due_date[2]]
            due_year = int(due_date[3])
            due = datetime.datetime(due_year,due_month,due_day,hour=due_hour,minute=due_minute)
            context.user_data["task"]["date"] = due
            context.user_data["task"]["id"] = hash(due)
            context.bot.send_message(chat_id=update.effective_chat.id, text="Task created with ID {}".format(context.user_data["task"]["id"]))

if __name__ == "__main__":

    start_handler = CommandHandler("start",start)
    msg_handler = MessageHandler(Filters.text & (~Filters.command),text_handler)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(CallbackQueryHandler(define_task,pattern="1"))
    dispatcher.add_handler(CallbackQueryHandler(show_tasks,pattern="2"))
    dispatcher.add_handler(msg_handler)

    updater.start_polling()

    updater.idle()