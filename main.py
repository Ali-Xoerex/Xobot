#!/usr/bin/python

import time
import os
import configparser
import concurrent.futures
import pickle
import sqlite3
import datetime
import calendar

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

def inactive_buttons(update,context):
    query = update.callback_query
    print(query.data)
    query.answer()

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

def calendar_markup(y,m):
    monthstr = calendar.TextCalendar()
    monthstr = monthstr.formatmonth(y,m)
    monthstr = monthstr.split("\n")
    monthstr = [i.strip() for i in monthstr]
    first = [InlineKeyboardButton("<",callback_data="previous"),InlineKeyboardButton(monthstr[0],callback_data="None"),InlineKeyboardButton(">",callback_data="next")]
    second = [InlineKeyboardButton(mnth,callback_data="None") for mnth in monthstr[1].split()]
    m2 = monthstr[2].split()
    zeros = ["0" for i in range(7-len(m2))]
    m2 = zeros + m2
    m3 = monthstr[3].split()
    m4 = monthstr[4].split()
    m5 = monthstr[5].split()
    monthstr[6] = monthstr[6].split()
    zeros = ["0" for i in range(7-len(monthstr[6]))]
    m6 = monthstr[6] + zeros
    m2 = [InlineKeyboardButton(i,callback_data="d{}".format(i)) if i != "0" else InlineKeyboardButton("-",callback_data="None") for i in m2]
    m3 = [InlineKeyboardButton(i,callback_data="d{}".format(i)) if i != "0" else InlineKeyboardButton("-",callback_data="None") for i in m3]
    m4 = [InlineKeyboardButton(i,callback_data="d{}".format(i)) if i != "0" else InlineKeyboardButton("-",callback_data="None") for i in m4]
    m5 = [InlineKeyboardButton(i,callback_data="d{}".format(i)) if i != "0" else InlineKeyboardButton("-",callback_data="None") for i in m5]
    m6 = [InlineKeyboardButton(i,callback_data="d{}".format(i)) if i != "0" else InlineKeyboardButton("-",callback_data="None") for i in m6]
    keyboard = [first,second,m2,m3,m4,m5,m6]
    return keyboard

def pick_date(update,context):
    query = update.callback_query
    context.user_data["date"]["day"] = query.data.replace("d","")
    context.bot.send_message(chat_id=update.effective_chat.id,text="Great!\n What time will it end? (24-hour format e.g 13:14)")
    context.user_data["state"] = "define_time"
    query.answer()   

def back_calendar(update,context):
    query = update.callback_query
    query.answer()
    month = context.user_data["date"]["month"]
    if month - 1 < 1:
        context.user_data["date"]["month"] = 12
        context.user_data["date"]["year"] -= 1
    else:
        context.user_data["date"]["month"] -= 1
    k = calendar_markup(context.user_data["date"]["year"],context.user_data["date"]["month"])    
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,reply_markup=InlineKeyboardMarkup(k),message_id=context.user_data["last_markup_id"])

def forward_calendar(update,context):
    query = update.callback_query
    query.answer()
    month = context.user_data["date"]["month"]
    if month + 1 > 12:
        context.user_data["date"]["month"] = 1
        context.user_data["date"]["year"] += 1
    else:
        context.user_data["date"]["month"] += 1
    k = calendar_markup(context.user_data["date"]["year"],context.user_data["date"]["month"])    
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,reply_markup=InlineKeyboardMarkup(k),message_id=context.user_data["last_markup_id"])

def text_handler(update,context):
    db = sqlite3.connect("xobot.db")
    cur = db.cursor()
    state = context.user_data.get("state")
    if state:
        if state == "define_title":
            now = datetime.datetime.now()
            k = calendar_markup(now.year,now.month)
            context.user_data["task"]["title"] = update.message.text
            context.user_data["date"] = {"year":now.year,"month":now.month}
            context.user_data["last_markup_id"] = context.bot.send_message(chat_id=update.effective_chat.id, text="Got it!\nNow tell me when is it due?",reply_markup=InlineKeyboardMarkup(k)).message_id
        if state == "define_time":
            due_time = update.message.text.split(":")
            due = datetime.datetime(int(context.user_data["date"]["year"]),int(context.user_data["date"]["month"]),int(context.user_data["date"]["day"]),hour=int(due_time[0]),minute=int(due_time[1]))
            cur.execute("INSERT INTO Tasks VALUES (?,?,?,?,?)",(update.effective_user.id,update.effective_chat.id,id(due),context.user_data["task"]["title"],pickle.dumps(due)))
            db.commit()
            db.close()
            task_thread = executor.submit(tick_until_finish,due,id(due),context.user_data["task"]["title"],update.effective_chat.id)
            executor_dict[id(due)] = task_thread
            context.user_data.pop("state")
            context.user_data.pop("task")
            context.user_data.pop("date")
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
    dispatcher.add_handler(CallbackQueryHandler(inactive_buttons,pattern="None"))
    dispatcher.add_handler(CallbackQueryHandler(back_calendar,pattern="previous"))
    dispatcher.add_handler(CallbackQueryHandler(forward_calendar,pattern="next"))
    dispatcher.add_handler(CallbackQueryHandler(pick_date,pattern="d*"))
    dispatcher.add_handler(msg_handler)

    updater.start_polling()

    updater.idle()