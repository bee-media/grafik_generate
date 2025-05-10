#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Project krik

import sys
import asyncio
from telegram import Bot #python-telegram-bot=21.5
from telegram.constants import ParseMode
import locale
import mysql.connector #mysql-connector
import datetime
import os

# Устанавливаем локаль для русского языка
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8') #ru_RU.UTF-8
now = datetime.datetime.now()
month_name = now.strftime('%B').capitalize()
next_month = (now.month % 12) + 1
next_month_name = datetime.date(1900, next_month, 1).strftime('%B').capitalize()

chat_id = int(os.getenv("CHAT_ID", "YOU_ID_CHAT"))
TOKEN = os.getenv("TELEGRAM_TOKEN", "TOKEN")
bot = Bot(token=TOKEN)


# Создаем подключение к базе данных
def connect_db():
    return mysql.connector.connect(
        user=os.getenv("DB_USER", "LOGIN"),
        password=os.getenv("DB_PASSWORD", "PASS"),
        host=os.getenv("DB_HOST", "IP_SERVER"),
        database=os.getenv("DB_NAME", "DB_NAME")
    )


# Функция для получения последнего дня месяца
def get_last_day_of_month(year, month):
    next_month = month % 12 + 1
    next_month_first_day = datetime.date(year, next_month, 1)
    last_day = next_month_first_day - datetime.timedelta(days=1)
    return last_day


# Генерация выходных дней
def get_weekends(year, month):
    last_day = get_last_day_of_month(year, month)
    weekends = [datetime.date(year, month, day) for day in range(1, last_day.day + 1)
                if datetime.date(year, month, day).weekday() >= 5]
    return weekends


# Генерация графика дежурств
def generate_schedule():
    today = datetime.datetime.today()
    year = today.year
    month = today.month + 1

    # Если месяц декабрь, то переключаемся на январь следующего года
    if today.month == 12:
        month = 1  # Январь
        year += 1  # Следующий год

    weekends = get_weekends(year, month)
    first_day_of_month = datetime.date(year, month, 1)

    workers = ('СОТРУДНИК1', 'СОТРУДНИК2', 'СОТРУДНИК3', 'СОТРУДНИК4')
    days_one_part = 2
    max_days_per_worker = 3

    workers_with_days = {worker: [] for worker in workers}

    if first_day_of_month.weekday() == 6:  # Воскресенье
        # Назначаем первый день месяца первому сотруднику
        workers_with_days[workers[0]].append(first_day_of_month)
        remaining_weekends = [day for day in weekends if day != first_day_of_month]
        workers_list = list(workers[1:]) + [workers[0]]
    else:
        remaining_weekends = weekends
        workers_list = list(workers)

    worker_index = 0
    for i in range(0, len(remaining_weekends), days_one_part):
        while True:
            current_worker = workers_list[worker_index]
            if len(workers_with_days[current_worker]) < max_days_per_worker:
                worker_days = remaining_weekends[i:i + days_one_part]
                workers_with_days[current_worker].extend(worker_days)
                break
            else:
                worker_index = (worker_index + 1) % len(workers_list)

        worker_index = (worker_index + 1) % len(workers_list)

    # Преобразуем словарь в список кортежей
    workers_with_days_list = [(worker, day) for worker, days in workers_with_days.items() for day in days]

    return workers_with_days_list

# Основная функция
async def main():
    workers_with_days = generate_schedule()

    # Подключение к БД и выполнение запросов
    try:
        cnx = connect_db()
        cursor = cnx.cursor()
        cursor.execute("TRUNCATE TABLE on_duty_copy1")

        text = f"*⚠️Внимание!⚠️*\n*Сгенерирован график дежурств:*\n{next_month_name}\n\n"
        insert_data = []

        for worker_name, worker_days in workers_with_days:
            text += f"*{worker_name}*: {worker_days}\n"
            insert_data.append((worker_name, worker_days))

        cursor.executemany("INSERT INTO on_duty_copy1 (surname, date) VALUES (%s, %s)", insert_data)
        cnx.commit()
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        cnx.close()


# Запуск асинхронной функции
if __name__ == "__main__":
    asyncio.run(main())
