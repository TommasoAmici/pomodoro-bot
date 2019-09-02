import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import redis
import threading


r = redis.Redis()

timers = {}


def check_if_cheating(bot, update):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat.id

    hash_name = f"pomodoro:{chat_id}:{user_id}"
    if timers[hash_name] is not None:
        timers[hash_name].cancel()
        timers[hash_name] = None
        bot.send_message(
            chat_id=update.message.chat_id, text=f"@{username} ha barato 😡"
        )


def end_pomodoro(bot, hash_name, chat_id, username, count):
    r.hincrby(hash_name, "count")
    timers[hash_name] = None

    bot.send_message(
        chat_id=chat_id, text=f"🍅 @{username} ha completato il pomodoro #{count + 1}"
    )


def start_pomodoro(bot, update):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat.id

    hash_name = f"pomodoro:{chat_id}:{user_id}"
    if r.hexists(hash_name, "count"):
        pomodoro_counts = r.hget(hash_name, "count")
    else:
        pomodoro_counts = 0
        r.hset(hash_name, "count", 0)

    timers[hash_name] = threading.Timer(
        1500, end_pomodoro, [bot, hash_name, chat_id, username, pomodoro_counts]
    )

    timers[hash_name].start()
    bot.send_message(
        chat_id=chat_id, text=f"🍅 Pomodoro #{pomodoro_counts + 1} per @{username}"
    )


updater = Updater(os.environ["POMODORO_TELEGRAM_TOKEN"])

updater.dispatcher.add_handler(CommandHandler("pomodoro", start_pomodoro))
updater.dispatcher.add_handler(MessageHandler(Filters.text, check_if_cheating))

updater.start_polling()
updater.idle()
