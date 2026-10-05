import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)

# ====== SOZLAMALAR (muhit o'zgaruvchilaridan o'qiladi) ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD = os.getenv("CARD", "8600 0000 0000 0000 (Ism Familiya)")
PACKS = {"60": 12000, "325": 60000, "660": 120000, "1800": 300000}  # UC: so'm
# ============================================================

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN o'rnatilmagan!")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
orders = {}  # buyurtmalar (hozircha xotirada)


class Order(StatesGroup):
    pubg_id = State()
    receipt = State()


@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    kb = [[InlineKeyboardButton(text=f"{uc} UC — {p:,} so'm",
                                callback_data=f"buy:{uc}")]
          for uc, p in PACKS.items()]
    await m.answer("PUBG Mobile UC do'koniga xush kelibsiz!\nPaketni tanlang:",
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("buy:"))
async def choose(c: CallbackQuery, state: FSMContext):
    uc = c.data.split(":")[1]
    await state.update_data(uc=uc)
    await state.set_state(Order.pubg_id)
    await c.message.answer(f"{uc} UC tanlandi.\nPUBG ID raqamingizni yuboring:")
    await c.answer()


@dp.message(Order.pubg_id)
async def get_id(m: Message, state: FSMContext):
    pid = (m.text or "").strip()
    if not pid.isdigit() or not 8 <= len(pid) <= 12:
        return await m.answer("ID noto'g'ri. Faqat raqam yuboring (8-12 ta).")
    d = await state.get_data()
    await state.update_data(pid=pid)
    await state.set_state(Order.receipt)
    await m.answer(f"{d['uc']} UC — {PACKS[d['uc']]:,} so'm\n"
                   f"PUBG ID: {pid}\n\n"
                   f"Shu kartaga to'lang:\n{CARD}\n\n"
                   f"So'ng to'lov chekining rasmini yuboring.")


@dp.message(Order.receipt, F.photo)
async def get_receipt(m: Message, state: FSMContext):
    d = await state.get_data()
    oid = str(len(orders) + 1)
    orders[oid] = {"user": m.from_user.id, "uc": d["uc"], "pid": d["pid"]}
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"ok:{oid}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"no:{oid}")]])
    await bot.send_photo(
        ADMIN_ID, m.photo[-1].file_id, reply_markup=kb,
        caption=f"Buyurtma #{oid}\n{d['uc']} UC\nPUBG ID: {d['pid']}\n"
                f"Mijoz: @{m.from_user.username} ({m.from_user.id})")
    await m.answer("Chek qabul qilindi. Admin tekshirib, UC ni yuboradi. ⏳")
    await state.clear()


@dp.message(Order.receipt)
async def need_photo(m: Message):
    await m.answer("Iltimos, to'lov chekining rasmini yuboring.")


@dp.callback_query(F.data.regexp(r"^(ok|no):"))
async def admin_decide(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("Ruxsat yo'q", show_alert=True)
    act, oid = c.data.split(":")
    o = orders.get(oid)
    if not o:
        return await c.answer("Buyurtma topilmadi")
    if act == "ok":
        await bot.send_message(o["user"], f"✅ Buyurtma #{oid}: {o['uc']} UC "
                                          f"ID {o['pid']} ga yuborildi. Rahmat!")
        status = "TASDIQLANDI"
    else:
        await bot.send_message(o["user"], f"❌ Buyurtma #{oid} rad etildi. "
                                          f"Muammo bo'lsa adminga yozing.")
        status = "RAD ETILDI"
    await c.message.edit_caption(caption=f"{c.message.caption}\n\n{status}")
    await c.answer()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
