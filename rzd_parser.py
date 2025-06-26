from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import sqlite3
from datetime import datetime
class RZDParser:
    def __init__(self, from_station, to_station, date):
        self.driver = None
        self.wait_timeout = 30
        self.setup_driver()
        self.from_station = from_station
        self.to_station = to_station
        self.date = date
    def setup_driver(self):
            """Настройка веб-драйвера с опциями"""
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Включение headless-режима
            chrome_options.add_argument("--disable-gpu")  # Иногда требуется на Windows
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
    def accept_cookies(self):
            """Принятие cookie-уведомления"""
            try:
                cookie_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Принять') or contains(., 'Accept')]"))
                )
                cookie_btn.click()
                print("Приняли cookies")
            except:
                print("Не найдено уведомление о cookies")

    def navigate_to_tickets(self):
            """Переход на страницу поиска билетов"""
            try:
                tickets_link = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Пассажирам') or contains(., 'Билеты')]"))
                )
                tickets_link.click()
                print("Перешли в раздел билетов")
                return True
            except Exception as e:
                print(f"Ошибка перехода: {e}")
                return False

    def search_trains(self):
            """Поиск поездов по заданным параметрам"""
            try:
                # 1. Ввод "Откуда"
                from_input = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//input[contains(@placeholder, 'ткуда') or contains(@placeholder, 'Откуда')]"))
                )
                from_input.send_keys(self.from_station)
                self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//li[contains(., '{self.from_station}')][1]"))
                ).click()
                time.sleep(0.5)  # Важная пауза после выбора

                # 2. Ввод "Куда" с расширенными проверками
                to_input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Куда')]"))
                )
                time.sleep(0.5)
                to_input.send_keys(self.to_station)

                # Тройная проверка доступности поля
                WebDriverWait(self.driver, 5).until(lambda d: to_input.is_displayed() and to_input.is_enabled())
                self.driver.execute_script("arguments[0].scrollIntoView(true);", to_input)

                # Ожидание и выбор варианта
                time.sleep(0.5)
                self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//li[contains(., '{self.to_station}')][1]"))
                ).click()

                # 3. Ввод даты
                date_input = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Туда')]"))
                )
                date_obj = datetime.strptime(self.date, "%Y-%m-%d")
                self.date = date_obj.strftime("%d.%m.%Y")
                date_input.send_keys(self.date)
                time.sleep(0.5)
                date_input = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Туда')]"))
                )
                date_input.send_keys(self.date)
                time.sleep(0.5)
                # 4. Поиск
                search_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(.,'Найти')]"))
                ).click()

                print("Поиск выполнен успешно")
                return True
            except Exception as e:
                print(f"Ошибка поиска: {e}")
                return False

    def parse_results(self):
            """Парсинг результатов поиска"""
            trains = []
            try:
                # Ожидание загрузки результатов
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//rzd-search-results-card-list"))
                )

                # Поиск всех карточек поездов
                train_cards = self.driver.find_elements(By.XPATH, "//rzd-search-results-card-railway-flat-card")
                for card in train_cards:
                    try:
                        train_data = {
                            'number': card.find_element(By.XPATH, ".//h3").text,
                            'departure_time': card.find_element(By.XPATH,
                                                                ".//div[contains(@class, 'card-route__date-time--from')]").text,
                            'arrival_time': card.find_element(By.XPATH,
                                                              ".//div[contains(@class, 'card-route__date-time--to')]").text,
                            'duration': card.find_element(By.XPATH,
                                                          ".//div[contains(@class, 'card-route__duration')]").text,
                        }
                        seats = self.get_seats2(card)
                        for seat in seats:
                            train_data = {
                                **train_data,  # Копируем общую информацию о поезде
                                'name': seat[0],  # Название места
                                'price': seat[1],  # Цена
                                'sum': seat[2]  # Сумма
                            }
                            trains.append(train_data)


                    except Exception as e:
                        print(f"Ошибка парсинга карточки: {e}")
                        continue

                print(f"Найдено {len(trains)} поездов")
                print(trains)
                return trains
            except Exception as e:
                print(f"Ошибка парсинга результатов: {e}")
                return []

    def get_seats2(self, card):
            aseats = []
            i = 0
            try:
                seats = card.find_elements(By.XPATH, ".//div[contains(@class, 'col body__classes')]")
                try:
                    for seat in seats:
                        t = seat.text
                        seat_datum = t.splitlines()
                        while i <= len(seat_datum) / 4 - 1:
                            seat_data = [seat_datum[4 * i], seat_datum[4 * i + 3], seat_datum[4 * i + 1]]
                            i += 1
                            aseats.append(seat_data)

                except Exception as e:
                    aseats.append("Мест нет")
                return aseats
            except Exception as e:
                print(f"Ошибка парсинга результатов: {e}")
                return "Мест нет"

    def save_results(self, trains, db_name="rzd_parsers.db"):
        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS rzd_tickets
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          number TEXT,
                          departure_time TEXT,
                          arrival_time TEXT,
                          duration TEXT,
                          name TEXT,
                          price TEXT,
                          sum TEXT,
                          saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            c.execute("DELETE FROM rzd_tickets")
            # Вставляем новые данные
            for item in trains:
                required_fields = ['number', 'departure_time', 'arrival_time',
                                   'duration', 'name', 'price', 'sum']
                if not all(field in item for field in required_fields):
                    print(f"Пропуск записи: отсутствуют обязательные поля - {item}")
                    continue

                # Вставляем запись
                c.execute('''INSERT INTO rzd_tickets 
                                             (number, departure_time, arrival_time, duration, 
                                              name, price, sum)
                                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (item['number'],
                           item['departure_time'],
                           item['arrival_time'],
                           item['duration'],
                           item['name'],
                           item['price'],
                           item['sum']))
            conn.commit()
            conn.close()
            print(f"Успешно сохранено {len(trains)} записей в базу данных {db_name}")
            return True

        except sqlite3.Error as e:
            print(f"Ошибка сохранения в SQLite: {e}")
            return False
        except Exception as e:
            print(f"Общая ошибка: {e}")
            return False
    def run(self):
            """Основной метод запуска парсера"""
            try:
                print("=== Начало работы парсера РЖД ===")

                # Открытие сайта
                self.driver.get("https://ticket.rzd.ru/")
                print("Сайт открыт")

                # Принятие cookies
                self.accept_cookies()

                # Переход к поиску билетов
                if not self.navigate_to_tickets():
                    return False

                # Выполнение поиска
                if not self.search_trains():
                    return False

                # Парсинг результатов
                results = self.parse_results()

                # Сохранение результатов
                self.save_results(results)
            except Exception as e:
                print(f"Критическая ошибка: {e}")
                return False
            finally:
                if self.driver:
                    self.driver.quit()
                    print("Браузер закрыт")
