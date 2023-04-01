import os
import json
import threading
import requests
from flask import Flask, render_template
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Замените значения YOUR_TELEGRAM_API_TOKEN и YOUR_GROUP_CHAT_ID на соответствующие значения
TOKEN = "920834262:AAFbgVXgqhrEkDjfxfmHPL3tcS9QyrhywDM"
GROUP_CHAT_ID = "-1001877067791"
STEAM_API_KEY = "8C545C76AF8E0364D0D5B73EE1A3AAB2"

app = Flask(__name__)
app.env = "development"
tracked_games = {}

# Получение информации об игре из Steam API
def get_app_details(app_id: str, language: str = "en") -> dict:
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l={language}&cc=us"
    response = requests.get(url)
    data = json.loads(response.text)

    if data[str(app_id)]["success"]:
        return data[str(app_id)]["data"]
    else:
        return None

# Получение цены игры
def get_price(app_id: str, language: str = "en") -> str:
    app_details = get_app_details(app_id, language)

    if app_details and "price_overview" in app_details:
        price = app_details["price_overview"]["final_formatted"]
        return price
    else:
        return "N/A"

# Получение названия игры
def get_game_name(app_id: str, language: str = "en") -> str:
    app_details = get_app_details(app_id, language)

    if app_details:
        return app_details["name"]
    else:
        return "N/A"

# Получение изображения игры
def get_game_image(app_id: str) -> str:
    app_details = get_app_details(app_id)

    if app_details:
        return f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/{app_details['header_image']}"
    else:
        return "N/A"

# Обработка команды /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Привет! Я бот для отслеживания цен игр в магазине Steam.")

# Обработка команды /add_game
def add_game(update: Update, context: CallbackContext) -> None:
    game_url = ' '.join(context.args)

    if not game_url:
        update.message.reply_text("Пожалуйста, укажите ссылку на игру в магазине Steam.")
        return

    app_id = game_url.split("/")[4]

    if app_id in tracked_games:
        update.message.reply_text("Эта игра уже добавлена в список отслеживаемых.")
        return

    game_name = get_game_name(app_id)
    game_price = get_price(app_id)
    game_image = get_game_image(app_id)

    if game_name == "N/A":
        update.message.reply_text("Не удалось найти игру по указанной ссылке. Проверьте правильность ссылки.")
        return

    tracked_games[app_id] = {"name": game_name, "price": game_price, "image": game_image}
    update.message.reply_text(f"Игра '{game_name}' добавлена в список отслеживаемых.")

# Обработка команды /remove_game
def remove_game(update: Update, context: CallbackContext) ->None:
    game_url = ' '.join(context.args)

    if not game_url:
        update.message.reply_text("Пожалуйста, укажите ссылку на игру в магазине Steam.")
        return

    app_id = game_url.split("/")[4]

    if app_id not in tracked_games:
     update.message.reply_text("Эта игра не найдена в списке отслеживаемых.")
     return

    game_name = tracked_games[app_id]["name"]
    del tracked_games[app_id]
    update.message.reply_text(f"Игра '{game_name}' удалена из списка отслеживаемых.")

#Функция для отправки уведомлений об изменении цены
def send_price_notification(context: CallbackContext) -> None:
    for app_id, game in tracked_games.items():
        current_price = get_price(app_id)
        if current_price != game["price"]:
            game["price"] = current_price
            context.bot.send_message(chat_id=GROUP_CHAT_ID, text=f"Цена на игру '{game['name']}' изменилась! Новая цена: {current_price}")

#Функция для запуска сервиса отслеживания изменений цены
def price_tracking_service() -> None:
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add_game", add_game))
    dp.add_handler(CommandHandler("remove_game", remove_game))

# Запуск отправки уведомлений каждые 60 секунд
    job_queue = updater.job_queue
    job_queue.run_repeating(send_price_notification, interval=60, first=0)

    updater.start_polling()
    updater.idle()

#Запуск веб-сервера для микросервиса
@app.route("/")
def display_tracked_games():
    return render_template("tracked_games.html", games=tracked_games)

if __name__ == "__main__":
    # Запуск веб-сервера в отдельном потоке
    flask_thread = threading.Thread(target=app.run, kwargs={'threaded': True}, daemon=True)
    flask_thread.start()

    # Запуск сервиса отслеживания изменений цены в основном потоке
    price_tracking_service()

    # Запуск веб-сервера в отдельном потоке
    app.run(threaded=True)