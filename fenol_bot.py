8052557793:AAGuVbAjR-d3QpMONU7c1YVbAqBvZ4VIiFo
import asyncio
import os
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.getenv("TOKEN")  
bot = Bot(token=TOKEN)
dp = Dispatcher()

players = {}  

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎨 Бомбить стену")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🛠 Заправить баллон")],
        [KeyboardButton(text="😴 Отдохнуть")],
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: types.Message):
    uid = message.from_user.id
    if uid not in players:
        players[uid] = {
            "paint": 0,
            "can": 100,
            "adrenaline": 100,
            "last_action": time.time(),
            "busted_until": 0,
            "level": 1
        }

    text = (
        "🌃 Добро пожаловать в <b>Fenol</b> — мир настоящего стрит-арта!\n\n"
        "Ты — writer. Ночью выходишь на стены, кидаешь теги, throw-ups, иногда burner'ы.\n"
        "Не попадись копам, не кончи краску, держи адреналин.\n\n"
        "<i>Бери баллон и поехали бомбить город 🔥</i>"
    )
    await message.answer(text, reply_markup=MAIN_MENU, parse_mode="HTML")


@dp.message(lambda m: m.text == "🎨 Бомбить стену")
async def bomb(message: types.Message):
    uid = message.from_user.id
    if uid not in players:
        await start(message)
        return

    p = players[uid]
    now = time.time()

    # реген адреналина
    passed = now - p["last_action"]
    regen = int(passed // 180) * 12
    if regen > 0:
        p["adrenaline"] = min(100, p["adrenaline"] + regen)
        p["last_action"] = now

    if now < p["busted_until"]:
        left = int(p["busted_until"] - now)
        await message.answer(f"🚨 Копы ищут тебя! Сиди тихо ещё {left//60} мин.")
        return

    if p["adrenaline"] < 18:
        await message.answer("Адреналин на нуле... Пора валить домой 😴")
        return

    if p["can"] < 8:
        await message.answer("Баллон почти пустой! Заправь скорее 🛠")
        return

    p["adrenaline"] -= random.randint(9, 24)
    p["can"] -= random.randint(5, 14)
    p["last_action"] = now

    roll = random.random()

    if roll < 0.03:
        penalty = random.randint(40, 120)
        p["paint"] = max(0, p["paint"] - penalty)
        p["busted_until"] = now + random.randint(300, 900)
        text = f"🚨 КОПЫ! Потерял {penalty} краски!\nСиди тихо ещё {(p['busted_until']-now)//60} мин."
    elif roll < 0.55:
        paint = random.randint(10, 22)
        text = f"Быстрый тег → +{paint} 🎨"
    elif roll < 0.82:
        paint = random.randint(28, 55)
        text = f"Чёткий throw-up! → +{paint} 🔥"
    elif roll < 0.97:
        paint = random.randint(70, 140)
        text = f"BURNER на всю стену! → +{paint} ✨"
    else:
        text = "Пустая стена... зря тратил краску 😤"
        paint = 0

    p["paint"] += paint

    old_level = p["level"]
    p["level"] = max(1, 1 + p["paint"] // 500)
    if p["level"] > old_level:
        text += f"\n\n🎉 LEVEL UP! Теперь {p['level']} уровень!"

    status = (
        f"\n\n🎨 Краска: {p['paint']:,}\n"
        f"🛠 Баллон: {max(0, p['can'])}%\n"
        f"⚡ Адреналин: {max(0, p['adrenaline'])}%"
    )

    if p["can"] < 15: status += "\n⚠️ Баллон почти пуст!"
    if p["adrenaline"] < 25: status += "\n⚠️ Нервы на пределе!"

    await message.answer(text + status)


@dp.message(lambda m: m.text == "📊 Статистика")
async def stats(message: types.Message):
    uid = message.from_user.id
    if uid not in players:
        await message.answer("Ты ещё не начинал бомбить...")
        return

    p = players[uid]
    now = time.time()

    # реген перед показом
    passed = now - p["last_action"]
    regen = int(passed // 180) * 12
    if regen > 0:
        p["adrenaline"] = min(100, p["adrenaline"] + regen)
        p["last_action"] = now

    text = (
        f"<b>Твоя статистика в Fenol</b>\n\n"
        f"🎨 Краска / репа: {p['paint']:,}\n"
        f"🏆 Уровень: {p['level']}\n"
        f"🛠 Баллон: {max(0, p['can'])}%\n"
        f"⚡ Адреналин: {max(0, p['adrenaline'])}%"
    )

    if p["busted_until"] > now:
        left = int(p["busted_until"] - now)
        text += f"\n\n🚨 В розыске ещё {left//60} мин"

    await message.answer(text, parse_mode="HTML")


@dp.message(lambda m: m.text == "🛠 Заправить баллон")
async def refill(message: types.Message):
    uid = message.from_user.id
    if uid not in players:
        await start(message)
        return

    p = players[uid]

    if p["can"] >= 98:
        await message.answer("Баллон почти полный — иди рисуй!")
        return

    cost = 45 if p["level"] >= 3 else 35
    if p["paint"] < cost:
        await message.answer(f"Недостаточно краски. Нужно {cost} 🎨")
        return

    p["paint"] -= cost
    add = 80 if p["level"] >= 5 else 70
    p["can"] = min(100, p["can"] + add)

    await message.answer(
        f"Заправил баллон 🛠\n"
        f"Теперь {p['can']}% давления\n"
        f"Остаток краски: {p['paint']:,}"
    )


@dp.message(lambda m: m.text == "😴 Отдохнуть")
async def rest(message: types.Message):
    uid = message.from_user.id
    if uid not in players:
        await start(message)
        return

    p = players[uid]

    if p["adrenaline"] >= 95:
        await message.answer("Ты и так свежий как после сна 😏")
        return

    regen = random.randint(25, 45)
    p["adrenaline"] = min(100, p["adrenaline"] + regen)
    p["last_action"] = time.time()

    await message.answer(f"Отоспался в заброшке... +{regen}% адреналина ⚡\nТеперь {p['adrenaline']}%")


@dp.message()
async def unknown(message: types.Message):
    await message.answer("Жми кнопки ниже, writer 🎨 Не теряй ночь!")
async def on_startup():
    base_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
    webhook_path = "/webhook"
    await bot.set_webhook(f"{base_url}{webhook_path}")
    print("Webhook установлен автоматически!")

async def main():
    await on_startup()

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print(f"Бот запущен на порту {port}")
    await asyncio.Event().wait()  # держим процесс живым

if __name__ == "__main__":
    asyncio.run(main())