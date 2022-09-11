#!/usr/bin/python

import time
import os
import configparser
import concurrent.futures
import pickle
import sqlite3
import datetime

from telegram import Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

months = {"January": 1, "February":2, "March": 3, "April":4, "May": 5, "June": 6, "July":7, "August":8, "September":9, "October":10, "November":11, "December": 12}
request_kargs = {"proxy_url":"http://127.0.0.1:5000"} # Hard-coded only for test

if os.path.isfile("config.cfg"):
    config = configparser.ConfigParser()
    config.read_file(open("config.cfg"))
    t = config["Options"]["token"]
    updater = Updater(token=t, request_kwargs=request_kargs)
else:
    t = input("Enter bot token: ")
    updater = Updater(token=t, request_kwargs=request_kargs)
    config = configparser.ConfigParser()
    config["Options"] = {}
    config["Options"]["token"] = t
    with open("config.cfg","w") as cfile:
        config.write(cfile)


dispatcher = updater.dispatcher
executor = concurrent.futures.ThreadPoolExecutor()
executor_dict = {}

def tick_until_finish(dateobj,objid,title,chatid):
    secs = (dateobj - datetime.datetime.now()).seconds
    time.sleep(secs)
    db = sqlite3.connect("xobot.db")
    cur = db.cursor()
    cur.execute("DELETE FROM Tasks WHERE id={}".format(objid))
    db.commit()
    db.close()
    executor_dict.pop(objid)
    updater.bot.send_message(chat_id=chatid,text="The due date of following task has been reached\nTitle: {}\nDue:{}".format(title,dateobj))

def setup():
    db = sqlite3.connect("xobot.db")
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS Tasks (User INTEGER, chatid INTEGER ,id INTEGER, Title TEXT, dateobj BLOB)")
    db.commit()
    cur.execute("SELECT * FROM TASKS")
    results = cur.fetchall()

    for result in results:
        dateobject = pickle.loads(result[4])
        if datetime.datetime.now() < dateobject:
            a = executor.submit(tick_until_finish,dateobject,result[2],result[3],result[1])
            executor_dict[result[2]] = a
        else:
            cur.execute("DELETE FROM Tasks WHERE id={}".format(result[2]))
            db.commit()     
    db.close()

def start(update,context):
    menu = [
        [InlineKeyboardButton("Define Task",callback_data="1"),
        InlineKeyboardButton("Show Tasks",callback_data="2"),
        InlineKeyboardButton("Delete Task",callback_data="3")]
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
    db = sqlite3.connect("xobot.db")
    cur = db.cursor()
    query = update.callback_query
    query.answer()
    cur.execute("SELECT * FROM Tasks WHERE User={}".format(update.effective_user.id))
    results = cur.fetchall()
    for result in results:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Title: {}\n Due Date: {}".format(result[3],pickle.loads(result[4])))
    if not context.user_data.get("state"):
        context.bot.send_message(chat_id=update.effective_chat.id, text="You pressed show button")

def text_handler(update,context):
    db = sqlite3.connect("xobot.db")
    cur = db.cursor()
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
            cur.execute("INSERT INTO Tasks VALUES (?,?,?,?,?)",(update.effective_user.id,update.effective_chat.id,id(due),context.user_data["task"]["title"],pickle.dumps(due)))
            db.commit()
            db.close()
            task_thread = executor.submit(tick_until_finish,due,id(due),context.user_data["task"]["title"],update.effective_chat.id)
            executor_dict[id(due)] = task_thread
            context.user_data.pop("state")
            context.user_data.pop("task")
            context.bot.send_message(chat_id=update.effective_chat.id, text="Task created with ID {}".format(id(due)))
        if state == "choose_del":
            cur.execute("SELECT * FROM Tasks WHERE User={}".format(update.effective_user.id))
            results = cur.fetchall()
            for ind,task in enumerate(results):
                if str(ind) == update.message.text:
                    identification = task[2]
                    executor_dict[identification].cancel()
                    context.user_data.pop("state")
                    executor_dict.pop(identification)
                    context.bot.send_message(chat_id=update.effective_chat.id, text="Task deleted with ID {}".format(identification))
                    break


def delete_task(update,context):
    db = sqlite3.connect("xobot.db")
    cur = db.cursor()
    query = update.callback_query
    query.answer()
    cur.execute("SELECT * FROM Tasks WHERE User={}".format(update.effective_user.id))
    results = cur.fetchall()
    if results:
        context.user_data["state"] = "choose_del"
    for ind,task in enumerate(results):
        context.bot.send_message(chat_id=update.effective_chat.id, text="No.{}\nTitle: {}\n Due Date: {}".format(ind,task[3],pickle.loads(task[4])))

if __name__ == "__main__":

    setup()

    start_handler = CommandHandler("start",start)
    msg_handler = MessageHandler(Filters.text & (~Filters.command),text_handler)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(CallbackQueryHandler(define_task,pattern="1"))
    dispatcher.add_handler(CallbackQueryHandler(show_tasks,pattern="2"))
    dispatcher.add_handler(CallbackQueryHandler(delete_task,pattern="3"))
    dispatcher.add_handler(msg_handler)

    updater.start_polling()

    updater.idle()