import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import redis
import threading
from datetime import date, timedelta


r = redis.Redis(
    host="localhost",
    charset="utf-8",
    decode_responses=True,
    db=os.environ["REDIS_DB_NUM"],
)

timers = {}


def check_if_cheating(update, context):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat.id

    hash_name = f"pomodoro:{chat_id}:{user_id}"
    if timers[hash_name] is not None:
        timers[hash_name].cancel()
        timers[hash_name] = None
        context.bot.send_message(
            chat_id=update.message.chat_id, text=f"@{username} ha barato 😡"
        )


def end_pomodoro(bot, hash_name, chat_id, username, count):
    """
    Callback for successful pomodoro timer
    """
    r.hincrby(hash_name, "count")
    r.lpush(f"{hash_name}:list", date.today().isoformat())
    timers[hash_name] = None

    bot.send_message(
        chat_id=chat_id, text=f"🍅 @{username} ha completato il pomodoro #{count}"
    )


def start_pomodoro(update, context):
    """
    Handles new pomodoro timer
    """
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat.id
    hash_name = f"pomodoro:{chat_id}:{user_id}"

    # if timer already exists cancel
    timer = timers.get(hash_name, None)
    if timer is not None:
        timer.cancel()

    # initialize hash if not present
    if r.hexists(hash_name, "count"):
        pomodoro_counts = int(r.hget(hash_name, "count")) + 1
    else:
        pomodoro_counts = 0 + 1
        r.hset(hash_name, "count", 0)
        r.hset(hash_name, "username", username)

    # set timer and store in global dict
    timer = threading.Timer(
        25 * 60,
        end_pomodoro,
        [context.bot, hash_name, chat_id, username, pomodoro_counts],
    )
    timers[hash_name] = timer
    timer.start()

    context.bot.send_message(
        chat_id=chat_id, text=f"🍅 Pomodoro #{pomodoro_counts} per @{username}"
    )


def stats(update, context, total=False):
    """
    Returns stats for past seven days
    """
    chat_id = update.message.chat.id
    hash_name = f"pomodoro:{chat_id}:*:list"

    keys = r.scan(0, hash_name, 1000)[1]
    pomodoros = [r.lrange(k, 0, -1) for k in keys]
    # filter last seven days
    last_week = date.today() - timedelta(days=7)
    pomodoros = [
        (
            # pomodoros completed in last week
            [p for p in pomodoro if (not total and date.fromisoformat(p) > last_week)],
            # username
            r.hget(keys[i][:-5], "username"),
        )
        for i, pomodoro in enumerate(pomodoros)
    ]
    # sort by number of pomodoros completed
    pomodoros = sorted(pomodoros, key=lambda k: len(k[0]), reverse=True)
    text = "\n".join([f"{p[1]}: {len(p[0])}" for p in pomodoros])
    context.bot.send_message(
        chat_id=chat_id, text=f"🍅 STATS POMODORI {date.today().isoformat()} 🍅\n{text}"
    )


def total(update, context):
    """
    Returns total stats
    """
    stats(update, context, total=True)


updater = Updater(os.environ["POMODORO_TELEGRAM_TOKEN"], use_context=True)

updater.dispatcher.add_handler(CommandHandler("pomodoro", start_pomodoro))
updater.dispatcher.add_handler(CommandHandler("stats", stats))
updater.dispatcher.add_handler(CommandHandler("total", stats))
updater.dispatcher.add_handler(MessageHandler(Filters.all, check_if_cheating))

updater.start_polling()
updater.idle()
