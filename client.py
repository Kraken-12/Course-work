import streamlit as st
import pandas as pd
import time
import random
import sqlite3

PAGE_SETTINGS = 'Настройки'
MAIN_PAGE='ГЛАВНАЯ'
PAGES = [MAIN_PAGE, PAGE_SETTINGS ]
# Настройки страницы
st.set_page_config(
    page_title="ATroute",
    page_icon="✈️",
    layout="wide"
)
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
def mock_parse_trains(from_city, to_city, travel_date):
    """Имитация парсинга данных о самолетах"""
    time.sleep(2)  # Имитация загрузки

    # Генерация случайных данных
    trains = []
    for i in range(random.randint(2, 5)):
        price = random.randint(3000, 15000)
        duration_hours = random.uniform(1, 3.5)
        trains.append({
            "Тип": "Поезд",
            "Авиакомпания": random.choice(["Аэрофлот", "S7", "Победа", "Utair"]),
            "Рейс": f"{random.choice(['SU', 'S7', 'DP', 'U6'])}{random.randint(1000, 9999)}",
            "Отправление": f"{random.randint(5, 22):02d}:{random.randint(0, 59):02d}",
            "Прибытие": f"{(random.randint(0, 2) + int(duration_hours)) % 24:02d}:{random.randint(0, 59):02d}",
            "Длительность": f"{int(duration_hours)} ч {int((duration_hours % 1) * 60)} мин",
            "Цена": f"{price} руб.",
            "Цена (число)": price,
            "Длительность (часы)": duration_hours,
            "Ссылка": "#"
        })
    return trains
def mock_parse_flights(from_city, to_city, travel_date):
    """Имитация парсинга данных о самолетах"""
    time.sleep(2)  # Имитация загрузки

    # Генерация случайных данных
    flights = []
    for i in range(random.randint(2, 5)):
        price = random.randint(3000, 15000)
        duration_hours = random.uniform(1, 3.5)
        flights.append({
            "Тип": "Самолет",
            "Авиакомпания": random.choice(["Аэрофлот", "S7", "Победа", "Utair"]),
            "Рейс": f"{random.choice(['SU', 'S7', 'DP', 'U6'])}{random.randint(1000, 9999)}",
            "Отправление": f"{random.randint(5, 22):02d}:{random.randint(0, 59):02d}",
            "Прибытие": f"{(random.randint(0, 2) + int(duration_hours)) % 24:02d}:{random.randint(0, 59):02d}",
            "Длительность": f"{int(duration_hours)} ч {int((duration_hours % 1) * 60)} мин",
            "Цена": f"{price} руб.",
            "Цена (число)": price,
            "Длительность (часы)": duration_hours,
            "Ссылка": "#"
        })
    return flights



if current_page == PAGE_SETTINGS:
    st.markdown(F'# {PAGE_SETTINGS}')

    with st.sidebar:
        st.header("Параметры поиска")
        city_from = st.text_input("Откуда (Город)")
        city_to = st.text_input("Куда (Город)")
        travel_date = st.date_input("Дата поездки")
        if st.button("Сохранить данные", type="primary"):
            # Создаем подключение к базе данных
            conn = sqlite3.connect('settings.db')
            cursor = conn.cursor()
            # Создаем таблицу, если она не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS travel_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_from TEXT,
                    city_to TEXT,
                    travel_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Вставляем данные
            cursor.execute('''
            INSERT
            INTO
            travel_settings(city_from, city_to, travel_date)
            VALUES(?, ?, ?)
            ''', (city_from, city_to, str(travel_date)))

            # Сохраняем изменения и закрываем соединение
            conn.commit()
            conn.close()

            st.success("Данные успешно сохранены в базу данных!")
    if st.button("Найти варианты", type="primary"):
        with st.spinner("Ищем лучшие варианты..."):
            # Получаем данные (в реальном приложении здесь будет настоящий парсинг)
            trains = mock_parse_trains(city_from, city_to, travel_date)
            flights = mock_parse_flights(city_from, city_to, travel_date)

            # Объединяем результаты
            all_options = trains + flights
            df = pd.DataFrame(all_options)

            # Сохраняем в сессии
            st.session_state.search_results = df

        # Показываем успешное сообщение
        st.success("Поиск завершен!")



# Кнопка поиска

# Если есть результаты поиска, отображаем их
if "search_results" in st.session_state:
    df = st.session_state.search_results

    st.markdown("---")
    st.header("Результаты поиска")

    # Вкладки для разных типов отображения
    tab1, tab2 = st.tabs(["Таблица", "Лучшие варианты"])

    with tab1:
        # Отображаем таблицу с результатами
        st.dataframe(
            df[["Тип", "Номер" if "Номер" in df.columns else "Рейс",
                "Отправление", "Прибытие", "Длительность", "Цена"]],
            column_config={
                "Ссылка": st.column_config.LinkColumn("Ссылка на билет")
            },
            hide_index=True,
            use_container_width=True
        )



    with tab2:
        # Лучшие варианты по цене и длительности
        st.subheader("Самые дешевые варианты")
        cheapest = df.sort_values("Цена (число)").head(3)
        for _, row in cheapest.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**{row['Тип']}**")
                    st.markdown(f"**{row['Цена']}**")
                with col2:
                    st.markdown(f"**{row['Номер'] if 'Номер' in row else row['Рейс']}**")
                    st.markdown(f"{row['Отправление']} → {row['Прибытие']} ({row['Длительность']})")

        st.subheader("Самые быстрые варианты")
        fastest = df.sort_values("Длительность (часы)").head(3)
        for _, row in fastest.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"**{row['Тип']}**")
                    st.markdown(f"**{row['Длительность']}**")
                with col2:
                    st.markdown(f"**{row['Номер'] if 'Номер' in row else row['Рейс']}**")
                    st.markdown(f"{row['Отправление']} → {row['Прибытие']} ({row['Цена']})")


st.markdown("---")
st.markdown("""
### Как это работает?
1. Введите города отправления и назначения
2. Укажите дату поездки
3. Нажмите кнопку "Найти варианты"
4. Сравните результаты и выберите лучший вариант""" )
