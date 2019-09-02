import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import redis
import threading


r = redis.Redis()

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
