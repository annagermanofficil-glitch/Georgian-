import sqlite3
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8657938353:AAF4J5tnTpdS02zR-T3AuIfrjwT76N_rcp8"
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_NAME = "georgian_rpg.db"

class RegistrationStates(StatesGroup):
    waiting_for_race = State()
    waiting_for_class = State()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            race TEXT,
            hero_class TEXT,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            gold INTEGER DEFAULT 100,
            attack INTEGER DEFAULT 12,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            next_level_exp INTEGER DEFAULT 100,
            location TEXT DEFAULT 'Мцхета (Столиця)'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            item_type TEXT,
            bonus_attack INTEGER DEFAULT 0,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit()
    conn.close()

def get_menu_keyboard(location: str):
    builder = ReplyKeyboardBuilder()
    if location.startswith("Мцхета") or location.startswith("Таверна"):
        builder.button(text="🍻 Зайти в Таверну")
        builder.button(text="🛒 Лавка торговця")
        builder.button(text="🗺️ Вийти на тракт")
        builder.button(text="👤 Мій Герой")
    elif location.startswith("Гори") or location.startswith("Руїни"):
        builder.button(text="⚔️ Шукати ворога")
        builder.button(text="🎒 Інвентар")
        builder.button(text="⛺ Розбити табір (Лікуватись)")
        builder.button(text="🗺️ Повернутися у Мцхету")
    else:
        builder.button(text="👤 Мій Герой")
        builder.button(text="🗺️ Вибрати шлях")
        builder.button(text="🎒 Інвентар")
        
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_battle_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="⚔️ Вдарити мечем/магією")
    builder.button(text="🧪 Випити цілюще зілля")
    builder.button(text="🏃 Спробувати втекти")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        await message.answer(
            "📜 Вітаю з поверненням у легенди Кавказу! Твій шлях уже записано в хроніках.",
            reply_markup=get_menu_keyboard("Мцхета")
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🧝 Ельф (Дзвідорі)", callback_data="race_Ельф")
    builder.button(text="👹 Орк (Гірський клан)", callback_data="race_Орк")
    builder.button(text="🧙‍♂️ Чаклун (Картулі)", callback_data="race_Чаклун")
    builder.button(text="🛡️ Людина-Воїн", callback_data="race_Воїн")
    builder.adjust(2, 2)

    await message.answer(
        "✨ **Таємниці королівства Остромах та давньої Грузії** відкриваються перед тобою.\n\n"
        "Обери свою **расу**:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationStates.waiting_for_race)

@dp.callback_query(F.data.startswith("race_"), RegistrationStates.waiting_for_race)
async def process_race(callback: types.CallbackQuery, state: FSMContext):
    race = callback.data.split("_")[1]
    await state.update_data(race=race)

    builder = InlineKeyboardBuilder()
    builder.button(text="⚔️ Воїн (Ближній бій)", callback_data="class_Воїн")
    builder.button(text="🔮 Маг (Володар стихій)", callback_data="class_Маг")
    builder.button(text="🗡️ Асасин (Тіньовий клин)", callback_data="class_Асасин")
    builder.adjust(1)

    await callback.message.edit_text(
        f"Обрана раса: **{race}**.\n\nТепер обери свій **клас**:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationStates.waiting_for_class)
    await callback.answer()

@dp.callback_query(F.data.startswith("class_"), RegistrationStates.waiting_for_class)
async def process_class(callback: types.CallbackQuery, state: FSMContext):
    hero_class = callback.data.split("_")[1]
    data = await state.get_data()
    race = data.get("race")
    user_id = callback.from_user.id
    name = callback.from_user.first_name

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, name, race, hero_class) VALUES (?, ?, ?, ?)",
        (user_id, name, race, hero_class)
    )
    cursor.execute(
        "INSERT INTO inventory (user_id, item_name, item_type, bonus_attack, quantity) VALUES (?, ?, ?, ?, ?)",
        (user_id, "Старий кинджал", "weapon", 6, 1)
    )
    cursor.execute(
        "INSERT INTO inventory (user_id, item_name, item_type, quantity) VALUES (?, ?, ?, ?)",
        (user_id, "Цілющий напій з наявту", "potion", 3)
    )
    conn.commit()
    conn.close()
    await state.clear()

    await callback.message.edit_text(
        f"⚔️ Персонажа створено!\nРаса: {race} | Клас: {hero_class}\n\n"
        f"Ти опинився біля стін стародавньої столиці Мцхета. Тумани огортають гори Кавказу..."
    )
    await callback.message.answer(
        "Використовуй клавіатуру нижче для керування:",
        reply_markup=get_menu_keyboard("Мцхета")
    )

@dp.message(F.text == "👤 Мій Герой")
async def show_hero(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT race, hero_class, hp, max_hp, gold, attack, level, exp, next_level_exp, location FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        race, h_class, hp, max_hp, gold, attack, lvl, exp, next_exp, loc = row
        await message.answer(
            f"👤 **Герой:** {message.from_user.first_name}\n"
            f"🧝 Раса: {race} | Клас: {h_class}\n"
            f"📍 Локація: {loc}\n"
            f"⭐ Рівень: {lvl} (Досвід: {exp}/{next_exp} XP)\n"
            f"❤️ Здоров'я: {hp}/{max_hp}\n"
            f"⚔️ Сила атаки: {attack}\n"
            f"💰 Золото: {gold}",
            parse_mode="Markdown"
        )

@dp.message(F.text == "🗺️ Вибрати шлях")
async def choose_path(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏰 Залишитися у Мцхеті", callback_data="loc_Мцхета")
    builder.button(text="⛰️ Високі Гори Кавказу", callback_data="loc_Гори")
    builder.button(text="🏛️ Руїни Давнього Храму", callback_data="loc_Руїни")
    builder.adjust(1)
    await message.answer("Обери напрямок своєї мандрівки:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("loc_"))
async def set_location(callback: types.CallbackQuery):
    loc = callback.data.split("_")[1]
    loc_names = {"Мцхета": "Мцхета (Столиця)", "Гори": "Високі Гори Кавказу", "Руїни": "Руїни Давнього Храму"}
    full_loc = loc_names.get(loc, "Мцхета")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET location = ? WHERE user_id = ?", (full_loc, callback.from_user.id))
    conn.commit()
    conn.close()

    await callback.message.edit_text(f"📍 Ти перемістився до локації: **{full_loc}**.", parse_mode="Markdown")
    await callback.message.answer("Ось твоє нове оточення:", reply_markup=get_menu_keyboard(full_loc))
    await callback.answer()

@dp.message(F.text == "🗺️ Повернутися у Мцхету")
async def return_mtskheta(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET location = 'Мцхета (Столиця)' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("🏰 Ти повернувся до спокійної Мцхети.", reply_markup=get_menu_keyboard("Мцхета"))

@dp.message(F.text == "🎒 Інвентар")
async def show_inventory(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, item_type, bonus_attack, quantity FROM inventory WHERE user_id = ?", (message.from_user.id,))
    items = cursor.fetchall()
    conn.close()

    if not items:
        await message.answer("🎒 Твій інвентар порожній.")
        return

    text = "🎒 **Твій Інвентар:**\n\n"
    for name, itype, bonus, qty in items:
        icon = "⚔️" if itype == "weapon" else "🧪"
        text += f"{icon} {name} (К-ть: {qty})\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⛺ Розбити табір (Лікуватись)")
async def rest_camp(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET hp = max_hp WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("⛺ Ти розбив табір біля вогнища, поїв гарячого хліба та повністю відновив здоров'я (HP)!")

active_battles = {}

@dp.message(F.text == "⚔️ Шукати ворога")
async def start_battle(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT hp, location FROM users WHERE user_id = ?", (user_id,))
    hp, location = cursor.fetchone()
    conn.close()

    if hp <= 0:
        await message.answer("💀 Ти без свідомості! Повернись у Мцхету або віднови сили в таборі.")
        return

    monsters = [
        {"name": "Гірський Розбійник", "hp": 45, "attack": 10, "gold": 20, "exp": 30},
        {"name": "Містичний Кадхі (Демон туману)", "hp": 70, "attack": 16, "gold": 45, "exp": 60},
        {"name": "Страж Древнього Храму", "hp": 100, "attack": 22, "gold": 80, "exp": 100}
    ]
    monster = random.choice(monsters)

    active_battles[user_id] = {
        "name": monster["name"],
        "hp": monster["hp"],
        "max_hp": monster["hp"],
        "attack": monster["attack"],
        "gold": monster["gold"],
        "exp": monster["exp"]
    }

    await message.answer(
        f"⚠️ **УВАГА! БІЙ!**\n\nЗ тіні вискочив ворог: **{monster['name']}**!\nОбери дію на клавіатурі нижче:",
        reply_markup=get_battle_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "⚔️ Вдарити мечем/магією")
async def battle_hit(message: types.Message):
    user_id = message.from_user.id
    battle = active_battles.get(user_id)
    if not battle:
        await message.answer("Зараз немає активного бою.", reply_markup=get_menu_keyboard("Мцхета"))
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT hp, max_hp, attack, level, exp, next_level_exp FROM users WHERE user_id = ?", (user_id,))
    user_hp, user_max_hp, user_attack, lvl, exp, next_exp = cursor.fetchone()

    damage_to_monster = user_attack + random.randint(-3, 5)
    battle["hp"] -= damage_to_monster
    log = f"⚔️ Ти завдав ворогу **{damage_to_monster}** шкоди!\n"

    if battle["hp"] <= 0:
        gold = battle["gold"]
        gained_exp = battle["exp"]
        exp += gained_exp
        
        level_text = ""
        if exp >= next_exp:
            lvl += 1
            exp -= next_exp
            next_exp = lvl * 140
            user_max_hp += 30
            user_hp = user_max_hp
            level_text = f"\n\n⭐ **РІВЕНЬ ПІДВИЩЕНО! Тепер у тебе {lvl} рівень!**"
            cursor.execute("UPDATE users SET level = ?, max_hp = ?, hp = ? WHERE user_id = ?", (lvl, user_max_hp, user_max_hp, user_id))

        cursor.execute("UPDATE users SET gold = gold + ?, exp = ?, next_level_exp = ? WHERE user_id = ?", (gold, exp, next_exp, user_id))
        conn.commit()
        conn.close()
        
        del active_battles[user_id]
        
        await message.answer(
            f"🎉 **Перемога!** Ти здолав **{battle['name']}**!\n💰 Золото: +{gold} | ⭐ Досвід: +{gained_exp} XP{level_text}",
            reply_markup=get_menu_keyboard("Гори"),
            parse_mode="Markdown"
        )
        return

    monster_damage = battle["attack"] + random.randint(-2, 3)
    user_hp = max(0, user_hp - monster_damage)
    cursor.execute("UPDATE users SET hp = ? WHERE user_id = ?", (user_hp, user_id))
    conn.commit()
    conn.close()

    log += f"👹 {battle['name']} контратакував і завдав тобі **{monster_damage}** шкоди!\n\n"
    log += f"❤️ Твоє HP: {user_hp}/{user_max_hp} | 👹 HP Ворога: {battle['hp']}/{battle['max_hp']}"

    if user_hp <= 0:
        del active_battles[user_id]
        await message.answer("💀 Ти загинув у бою... Відпочинь у таборі.", reply_markup=get_menu_keyboard("Мцхета"))
        return

    await message.answer(log, parse_mode="Markdown")

@dp.message(F.text == "🧪 Випити цілюще зілля")
async def battle_heal(message: types.Message):
    user_id = message.from_user.id
    battle = active_battles.get(user_id)
    if not battle:
        await message.answer("Зараз немає бою.", reply_markup=get_menu_keyboard("Мцхета"))
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_type = 'potion' AND quantity > 0", (user_id,))
    potion = cursor.fetchone()

    if not potion:
        await message.answer("❌ У тебе немає цілющого напою в інвентарі!")
        conn.close()
        return

    if potion[1] == 1:
        cursor.execute("DELETE FROM inventory WHERE id = ?", (potion[0],))
    else:
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (potion[0],))

    cursor.execute("SELECT hp, max_hp FROM users WHERE user_id = ?", (user_id,))
    hp, max_hp = cursor.fetchone()
    new_hp = min(max_hp, hp + 50)
    cursor.execute("UPDATE users SET hp = ? WHERE user_id = ?", (new_hp, user_id))
    conn.commit()
    conn.close()

    await message.answer(f"🧪 Ти випив напій і відновив здоров'я! Тепер у тебе {new_hp}/{max_hp} HP.")

@dp.message(F.text == "🏃 Спробувати втекти")
async def battle_run(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_battles:
        del active_battles[user_id]
    await message.answer("🏃‍♂️ Ти кинув зброю і швидко втік у безпечне місце!", reply_markup=get_menu_keyboard("Мцхета"))

if __name__ == "__main__":
    import asyncio
    init_db()
    asyncio.run(dp.start_polling(bot))
