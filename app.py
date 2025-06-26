import streamlit as st
import pandas as pd
import time
import random
import sqlite3
import requests
import numpy as np
PAGE_SETTINGS = 'Настройки'
MAIN_PAGE='ГЛАВНАЯ'
PAGES = [MAIN_PAGE, PAGE_SETTINGS ]
# Настройки страницы
st.set_page_config(
    page_title="ATroute",
    page_icon="✈️",
    layout="wide"
)
def convert_duration_to_minutes(duration_str):
    """Конвертирует строку длительности (2ч 30м) в минуты"""
    hours = 0
    minutes = 0
    if 'ч' in duration_str:
        hours = int(duration_str.split('ч')[0])
    if 'м' in duration_str:
        minutes_part = duration_str.split('м')[0]
        minutes = int(minutes_part.split()[-1])
    return hours * 60 + minutes

current_page = None
with st.sidebar:
    st.markdown('## Меню')
    current_page = st.selectbox(' ',
                                (PAGES), label_visibility='collapsed')

if current_page == MAIN_PAGE:
    st.markdown(F'# {MAIN_PAGE}')
    # st.markdown(F'{username}')
    st.title(" Сравнение путешествий: поезда vs самолеты")
    st.markdown("""
    **Найдите лучший вариант для вашей поездки!**  
    Программа сравнивает стоимость и длительность путешествия на поезде и самолете.
    """)

if current_page == PAGE_SETTINGS:
    st.markdown(F'# {PAGE_SETTINGS}')

    with st.sidebar:
        st.header("Параметры поиска")
        city_from = st.text_input("Откуда (Город)")
        city_to = st.text_input("Куда (Город)")
        travel_date = st.date_input("Дата поездки")
        if st.button("Сохранить данные", type="primary"):
            if not city_from or not city_to:
                st.error("Укажите города!")
            else:
                # Отправка данных на Flask-сервер
                try:
                    response = requests.post(
                        "http://localhost:5000/api/search_tickets",
                        json={
                            "city_from": city_from,
                            "city_to": city_to,
                            "travel_date": str(travel_date)
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.search_results = data
                        st.success("Данные отправлены!")
                    else:
                        st.error(f"Ошибка сервера: {response.text}")

                except requests.exceptions.RequestException as e:
                    st.error(f"Ошибка подключения: {e}")


                def get_data_from_db():
                    try:
                        conn = sqlite3.connect('../pythonProject14/rzd_parsers.db')
                        cursor = conn.cursor()
                        # Получаем данные поездов
                        cursor.execute("SELECT number,departure_time ,arrival_time,duration,name, price, sum  FROM rzd_tickets")
                        trains = [{'number': row[0], 'departure_time ': row[1], 'arrival_time': row[2], 'duration': row[3], 'name': row[4], 'price': row[5], 'sum': row[6]} for row in cursor.fetchall()]
                        cursor.close()
                        conn.close()
                        # Получаем данные самолетов
                        conn = sqlite3.connect('../pythonProject14/avia_parsers.db')
                        cursor = conn.cursor()
                        cursor.execute("SELECT avialine,price,departure_time ,arrival_time,duration FROM avia_tickets")
                        flights = [{'avialine': row[0], 'price': row[1], 'departure_time': row[2] , 'arrival_time': row[3], 'duration': row[4]} for row in cursor.fetchall()]

                        cursor.close()
                        conn.close()

                        return {'trains': trains,
                                'flight':flights}

                    except Exception as e:
                        st.error(f"Ошибка при работе с базой данных: {e}")
                        return None


                # Основной код Streamlit
                data = get_data_from_db()
                if data:
                    st.success("Данные получены из базы данных!")
                else:
                    st.error(f"Ошибка сервера (код {response.status_code}): {response.text}")


# Кнопка поиска

# Если есть результаты поиска, отображаем их
if "search_results" in st.session_state:
    try:
        data = get_data_from_db()
        st.markdown("---")
        st.header("Результаты поиска")
        # Вкладки для разных типов отображения
        (tab1,tab2) = st.tabs(["RZD","AVIASALES"])

        with tab1:
            if isinstance(data, dict) and 'trains' in data:  # Проверяем тип и наличие ключа
                # Создаем DataFrame для поездов
                trains_df = pd.DataFrame(data['trains'])

                # Добавляем тип транспорта
                trains_df['Тип'] = 'Поезд'

                # Проверяем и преобразуем цены в числовой формат
                if 'price' in trains_df.columns:
                    trains_df['price'] = (
                        trains_df['price']
                        .str.replace(r'[^\d.,-]', '', regex=True)
                    )
                    trains_df['price'] = trains_df['price'].astype(int)

                # Переименовываем столбцы
                trains_df = trains_df.rename(columns={
                    'number': 'Номер',
                    'departure_time': 'Отправление',
                    'arrival_time': 'Прибытие',
                    'duration': 'Длительность',
                    'name': 'Класс',
                    'price': 'Цена',
                    'sum': 'Сумма'
                })

                # Выбираем нужные колонки для отображения
                display_columns = ['Тип', 'Номер', 'Прибытие', 'Длительность', 'Класс', 'Цена']
                available_columns = [col for col in display_columns if col in trains_df.columns]

                # Отображаем таблицу
                st.dataframe(
                    trains_df[available_columns],
                    column_config={
                        'Цена': st.column_config.NumberColumn(format='%d ₽'),
                        'Длительность': st.column_config.TextColumn(width='medium')
                    },
                    hide_index=True,
                    use_container_width=True
                )

                # Статистика
                if 'Цена' in trains_df.columns:
                    col2, col3 = st.columns(2)
                    with col2:
                        st.metric("Минимальная цена", f"{int(trains_df['Цена'].min())} ₽")
                    with col3:
                        st.metric("Максимальная цена", f"{int(trains_df['Цена'].max())} ₽")
            with tab2:
                if isinstance(data, dict) and 'flight' in data:  # Проверяем тип и наличие ключа
                    # Создаем DataFrame для поездов
                    plain_df = pd.DataFrame(data['flight'])

                    # Добавляем тип транспорта
                    plain_df['Тип'] = 'Самолет'

                    # Проверяем и преобразуем цены в числовой формат
                    if 'price' in plain_df.columns:
                        plain_df['price'] = (
                            plain_df['price']
                            .str.replace(r'[^\d.,-]', '', regex=True)
                        )
                        plain_df['price'] = plain_df['price'].astype(int)

                    # Переименовываем столбцы
                    plain_df = plain_df.rename(columns={
                        'avialine': 'Авиакомпания',
                        'departure_time': 'Отправление',
                        'arrival_time': 'Прибытие',
                        'duration': 'Длительность',
                        'price': 'Цена'
                    })

                    # Выбираем нужные колонки для отображения
                    display_columns = ['Тип', 'Авиакомпания', 'Отправление', 'Прибытие', 'Длительность', 'Цена']
                    available_columns = [col for col in display_columns if col in plain_df.columns]

                    # Отображаем таблицу
                    st.dataframe(
                        plain_df[available_columns],
                        column_config={
                            'Цена': st.column_config.NumberColumn(format='%d ₽'),
                            'Длительность': st.column_config.TextColumn(width='medium')
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                    # Статистика
                    if 'Цена' in plain_df.columns:
                        col2, col3 = st.columns(2)
                        with col2:
                            st.metric("Минимальная цена", f"{int(plain_df['Цена'].min())} ₽")
                        with col3:
                            st.metric("Максимальная цена", f"{int(plain_df['Цена'].max())} ₽")
    except:
        st.header("Результата нет")

st.markdown("---")

st.markdown("""
### Как это работает?
1. Введите города отправления и назначения
2. Укажите дату поездки
3. Нажмите кнопку "Найти варианты"
4. Сравните результаты и выберите лучший вариант""" )
