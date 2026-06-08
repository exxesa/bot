import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

from telethon import TelegramClient
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputPeerEmpty


# ================= НАСТРОЙКИ =================

BOT_TOKEN = "8140976640:AAEDUuzCs_qNVYbXD1T3yHPPCOi1xFxjPbM"

API_ID = 35531653
API_HASH = "0570028725a6b058cd475f75c09b30de"

CHANNELS = [
    "kazinform_news",
    "tengrinews",
    "newsnurkz",
    "zakonkz",
    "ztb_qaz",
    "informburo_kz"
]

MAX_RESULTS = 5

# ============================================


# ---------- BOT ----------
bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()

# ---------- TELETHON ----------
telethon = TelegramClient(
    "user_session",
    API_ID,
    API_HASH
)

# ---------- STATE ----------
user_state = {}        # user_id -> {"keyword": str, "days": int}
active_search = set()  # user_id


# ---------- KEYBOARD ----------

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="▶️ Старт")],
        [KeyboardButton(text="⏹ Стоп")]
    ],
    resize_keyboard=True
)


# ---------- COMMANDS ----------

@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    user_state.pop(uid, None)
    active_search.discard(uid)

    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Нажми <b>▶️ Старт</b>, чтобы начать поиск новостей",
        reply_markup=main_kb
    )


@dp.message(Command("stop"))
@dp.message(F.text == "⏹ Стоп")
async def stop(message: Message):
    uid = message.from_user.id

    stopped = False
    if uid in user_state:
        user_state.pop(uid, None)
        stopped = True

    if uid in active_search:
        active_search.discard(uid)
        stopped = True

    if stopped:
        await message.answer("🛑 Поиск остановлен", reply_markup=main_kb)
    else:
        await message.answer("ℹ️ Сейчас нет активного поиска", reply_markup=main_kb)


# ---------- START BUTTON ----------

@dp.message(F.text == "▶️ Старт")
async def start_button(message: Message):
    uid = message.from_user.id
    user_state.pop(uid, None)
    active_search.discard(uid)

    await message.answer(
        "✍️ Введи <b>ключевое слово</b> для поиска:",
        reply_markup=main_kb
    )


# ---------- TEXT HANDLER ----------

@dp.message(F.text)
async def handler(message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if text in ("▶️ Старт", "⏹ Стоп"):
        return

    # 1️⃣ ключевое слово
    if uid not in user_state:
        user_state[uid] = {"keyword": text}
        await message.answer("📅 За сколько <b>последних дней</b> искать? (число)")
        return

    # 2️⃣ количество дней
    if "days" not in user_state[uid]:
        if not text.isdigit():
            await message.answer("❌ Введи число, например <b>3</b>")
            return

        user_state[uid]["days"] = int(text)
        await message.answer("🔍 Ищу новости, подожди...")

        active_search.add(uid)
        await search_news(message, user_state[uid], uid)

        user_state.pop(uid, None)
        active_search.discard(uid)
        await message.answer("✅ Поиск завершён", reply_markup=main_kb)


# ---------- SEARCH ----------

async def search_news(message: Message, data: dict, uid: int):
    keyword = data["keyword"]
    days = data["days"]

    since = datetime.now(timezone.utc) - timedelta(days=days)
    found = 0

    for channel in CHANNELS:
        if uid not in active_search:
            return  # ⛔ мгновенный стоп

        try:
            result = await telethon(
                SearchRequest(
                    peer=channel,
                    q=keyword,
                    filter=InputPeerEmpty(),
                    min_date=since,
                    max_date=None,
                    offset_id=0,
                    add_offset=0,
                    limit=MAX_RESULTS,
                    max_id=0,
                    min_id=0,
                    hash=0
                )
            )

            for msg in result.messages:
                if uid not in active_search:
                    return

                if not msg.message:
                    continue

                link = f"https://t.me/{channel}/{msg.id}"
                await message.answer(
                    f"📰 <b>{channel}</b>\n"
                    f"{msg.message[:300]}...\n\n"
                    f"🔗 <a href='{link}'>Открыть новость</a>"
                )
                found += 1

        except Exception as e:
            print(f"❌ Ошибка {channel}: {e}")

    if uid in active_search and found == 0:
        await message.answer("😕 Ничего не найдено")


# ---------- MAIN ----------

async def main():
    print("🔐 Подключение Telethon...")
    await telethon.start()
    print("✅ Telethon подключен")

    print("🚀 Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
