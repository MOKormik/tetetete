import disnake
from disnake.ext import commands
import requests
import sqlite3
import os

intents = disnake.Intents.default()
intents.message_content = True

if not os.path.exists("sessions.db"):
    conn = sqlite3.connect("sessions.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        discord_user_id INTEGER PRIMARY KEY,
        account_id INTEGER,
        initial_battles INTEGER DEFAULT 0,
        initial_damage_dealt INTEGER DEFAULT 0,
        current_battles INTEGER DEFAULT 0,
        current_damage_dealt INTEGER DEFAULT 0,
        initial_wins INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()

bot = commands.Bot(command_prefix='!', intents=intents)

api_key = "f52d164fe93bfd86eeb8888ba932e7dd"

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.slash_command(name="debug_session", description="Отладочная информация о сессии")
async def debug_session(ctx):
    conn = sqlite3.connect("sessions.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE discord_user_id=?", (ctx.author.id,))
    session_data = cursor.fetchone()

    conn.close()

    if session_data:
        await ctx.send(f"Информация о сессии для пользователя {ctx.author.id}:\n"
                       f"Account ID: {session_data[1]}\n"
                       f"Initial Damage Dealt: {session_data[3]}\n"
                       f"Initial Battles: {session_data[4]}\n"
                       f"Current Damage Dealt: {session_data[5]}\n"
                       f"Current Battles: {session_data[6] if len(session_data) > 6 else 'N/A'}")
    else:
        await ctx.send("Сессия не найдена. Начните сессию с помощью `/start_session`.")

@bot.slash_command(name="start_session", description="Начать сессию для игрока Tanks Blitz")
async def start_session(ctx, nickname: str):
    api_key = "f52d164fe93bfd86eeb8888ba932e7dd"

    search_url = f"https://papi.tanksblitz.ru/wotb/account/list/?application_id={api_key}&search={nickname}"

    try:
        response = requests.get(search_url)
        data = response.json()
        account_id = data["data"][0]["account_id"]

        info_url = f"https://papi.tanksblitz.ru/wotb/account/info/?application_id={api_key}&account_id={account_id}"
        response_info = requests.get(info_url)
        data_info = response_info.json()
        current_damage_dealt = data_info["data"][str(account_id)]["statistics"]["all"]["damage_dealt"]
        current_battles = data_info["data"][str(account_id)]["statistics"]["all"]["battles"]

        conn = sqlite3.connect("sessions.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE discord_user_id=?", (ctx.author.id,))
        existing_session = cursor.fetchone()

        if existing_session:
            cursor.execute(
                "UPDATE sessions SET account_id=?, initial_damage_dealt=?, initial_battles=?, current_damage_dealt=?, current_battles=? WHERE discord_user_id=?",
                (account_id, current_damage_dealt, current_battles, current_damage_dealt, current_battles,
                 ctx.author.id))
        else:
            cursor.execute(
                "INSERT INTO sessions (discord_user_id, account_id, initial_damage_dealt, initial_battles, current_damage_dealt, current_battles) VALUES (?, ?, ?, ?, ?, ?)",
                (ctx.author.id, account_id, current_damage_dealt, current_battles, current_damage_dealt,
                 current_battles))

        conn.commit()
        conn.close()

        await ctx.send(f"Сессия для {nickname} начата. Account ID: {account_id}")

    except Exception as e:
        print(e)
        await ctx.send("Произошла ошибка при обработке запроса.")


@bot.slash_command(name="session", description="Статистика сессии игрока Tanks Blitz")
async def session(ctx):
    conn = sqlite3.connect("sessions.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE discord_user_id=?", (ctx.author.id,))
    session_data = cursor.fetchone()

    if session_data and len(session_data) >= 5:
        initial_damage_dealt = session_data[3]
        initial_battles = session_data[4]
        initial_wins = session_data[6]

        info_url = f"https://papi.tanksblitz.ru/wotb/account/info/?application_id={api_key}&account_id={session_data[1]}"
        response_info = requests.get(info_url)
        data_info = response_info.json()
        current_damage_dealt = data_info["data"][str(session_data[1])]["statistics"]["all"]["damage_dealt"]
        current_battles = data_info["data"][str(session_data[1])]["statistics"]["all"]["battles"]
        current_wins = data_info["data"][str(session_data[1])]["statistics"]["all"]["wins"]

        # Обновляем initial_damage_dealt, initial_battles и initial_wins
        cursor.execute("UPDATE sessions SET initial_damage_dealt=?, initial_battles=?, initial_wins=? WHERE discord_user_id=?",
                       (current_damage_dealt, current_battles, current_wins, ctx.author.id))

        # Рассчитываем разницу в боях, среднем уроне за бой и проценте побед
        battles_difference = current_battles - initial_battles
        average_damage_per_battle = round((current_damage_dealt - initial_damage_dealt) / battles_difference) if battles_difference > 0 else 0
        win_percentage = round((current_wins - initial_wins) / battles_difference * 100, 2) if battles_difference > 0 else 0

        await ctx.send(f"Средний урон: {average_damage_per_battle}\nБои: {battles_difference}\n"
                       f"Процент побед: {win_percentage}%")
    else:
        await ctx.send("Сессия не найдена. Начните сессию с помощью `/start_session`.")

    conn.commit()
    conn.close()

@bot.slash_command(name="tanker", description="Информация о игроке Tanks Blitz")
async def tanker(ctx, nickname: str):
    api_key = "f52d164fe93bfd86eeb8888ba932e7dd"

    search_url = f"https://papi.tanksblitz.ru/wotb/account/list/?application_id={api_key}&search={nickname}"

    try:
        response = requests.get(search_url)
        data = response.json()
        account_id = data["data"][0]["account_id"]

        info_url = f"https://papi.tanksblitz.ru/wotb/account/info/?application_id={api_key}&account_id={account_id}"

        response = requests.get(info_url)
        data = response.json()

        statistics = data["data"][str(account_id)].get("statistics", {}).get("all", {})

        wins = statistics.get('wins', 0)
        losses = statistics.get('losses', 0)
        battles = statistics.get('battles', 0)

        win_rate = (wins / battles) * 100 if battles > 0 else 0

        damage_dealt = statistics.get('damage_dealt', 0)
        average_damage_per_battle = round(damage_dealt / battles) if battles > 0 else 0

        embed = disnake.Embed(
            title=f"Информация о игроке {nickname}",
            description=f"Account ID: {account_id}",
            color=disnake.Color.green()
        )

        embed.add_field(name='Бои', value=battles, inline=False)
        embed.add_field(name='Победы', value=wins, inline=False)
        embed.add_field(name='Поражения', value=losses, inline=False)
        embed.add_field(name='Процент побед', value=f'{win_rate:.2f}%', inline=False)
        embed.add_field(name='Средний урон за бой', value=f'{average_damage_per_battle}', inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        print(e)
        await ctx.send("Произошла ошибка при обработке запроса.")

