import os
import time
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
from selenium.webdriver.common.keys import Keys
class AVIAParser:

    def __init__(self, from_station, to_station, date):
        self.driver = None
        self.wait_timeout = 0.05
        self.setup_driver()
        self.from_station=from_station
        self.to_station=to_station
        self.date=date

    def setup_driver(self):
        """Настройка веб-драйвера с опциями"""
        chrome_options = Options()
        #chrome_options.add_argument("--headless=new")
        #chrome_options.add_argument(
        #    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, self.wait_timeout)


    def accept_cookies(self):
        """Принятие cookie-уведомления"""
        try:
            cookie_btn = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Да без проблем') or contains(., 'Accept')]"))
            )
            cookie_btn.click()
            print("Приняли cookies")
        except:
            print("Не найдено уведомление о cookies")

    def search_planes(self):
        try:
            lum=self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div[1]/div/div[2]/div[2]/div[3]/div/form/footer/div/label/span[2]"))
            )
            lum.click()
            # 1. Ввод "Откуда"
            from_input = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@placeholder, 'Москва') or contains(@placeholder, 'Откуда')]"))
            )

            from_input.send_keys(Keys.CONTROL + "a")
            from_input.send_keys(Keys.DELETE)
            from_input.send_keys(self.from_station)
            time.sleep(0.5)
            # 2. Ввод "Куда" с
            # расширенными проверками
            to_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Куда')]"))
            )
            # # Ожидание и выбор варианта
            time.sleep(1.5)
            to_input.send_keys(self.to_station)
            time.sleep(0.5)  # Важная пауза после выбора
            # 3. Ввод даты
            date_input = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@tabindex, '0')] "))
            )
            parsed_date = datetime.strptime(self.date, "%Y-%m-%d")
            formatted_date = parsed_date.strftime("%a %b %d %Y")
            date_input.click()
            date_input.click()
            element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f'//select[@data-test-id="select-month"]')))
            element.click()
            time.sleep(0.5)
            formatted_dates =parsed_date.strftime("%Y-%m")
            element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f'//option[@value="{formatted_dates}"]')))
            element.click()
            time.sleep(0.5)
            element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f'//div[@aria-label="{formatted_date}"]')))
            element.click()
            time.sleep(0.5)
            # 4. Поиск
            button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@data-test-id="form-submit"]'))
            )
            button.click()

            print("Поиск выполнен успешно")
            return True
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return False

    def parse_results(self):
        """Парсинг результатов поиска"""
        try:
            time.sleep(15)
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
                more = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Показать ещё билеты')]"))
                )
                more.click()
                more.click()
                more.click()
            except:
                pass
            def extract_ticket_data(item):
                try:
                    airline = item.find_element(By.XPATH, ".//div[contains(@data-test-id, 'text')and contains(@style,'color')]").text
                    price = item.find_element(By.XPATH, ".//div[contains(@data-test-id, 'text')]").text
                    times = item.find_elements(By.XPATH, ".//span[contains(@class, 's__o7ypa') and contains(@data-test-id, 'text')]")
                    departure_time = times[0].text if len(times) > 0 else "N/A"
                    arrival_time = times[1].text if len(times) > 1 else "N/A"
                    airports = item.find_elements(By.XPATH, ".//span[contains(@class, 's__MqwO') and contains(@data-test-id, 'text')]")
                    departure_airport = airports[0].text if len(airports) > 0 else "N/A"
                    arrival_airport = airports[1].text if len(airports) > 1 else "N/A"
                    duration = item.find_element(By.XPATH,".//span[contains(@class, 's__iPfYoBmp1qVHqkPI5MCQ s__Lrz8pict9CWP2T8btbYb s__PAD5qI5zjZJVo59x3Acm')]").text
                    ticketes={
                        'Авиакомпания': airline,
                        'Цена': price,
                        'Вылет': departure_time,
                        'Прилет': arrival_time,
                        'Аэропорт вылета': departure_airport,
                        'Аэропорт прилета': arrival_airport,
                        'В пути': duration,
                        'Дата': self.date}
                    return ticketes
                except Exception as e:
                    print(f"Ошибка при извлечении данных: {e}")
                    return None

            # Сбор всех билетов

            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'web-app')]"))
            )
            tickets = self.driver.find_elements(By.CSS_SELECTOR, '[data-test-id="ticket-preview"]')
            all_tickets_data = []
            for ticket in tickets:
                ticket_data = extract_ticket_data(ticket)
                if ticket_data:
                    all_tickets_data.append(ticket_data)
            print(all_tickets_data)
            plains=all_tickets_data
            print(f"Найдено {len(plains)} самолетов")
            return plains
        except Exception as e:
            print(f"Ошибка парсинга результатов: {e}")
            return []
    def save_results(self, data, db_name="avia_parsers.db"):
        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS avia_tickets
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          avialine TEXT,
                          price TEXT,
                          departure_time TEXT,
                          arrival_time TEXT,
                          departure_airoport TEXT,
                          arrival_airoport TEXT,
                          duration TEXT,
                          data TEXT)''')
            c.execute("DELETE FROM avia_tickets")
            for item in data:
                required_fields = ['Авиакомпания', 'Цена', 'Вылет', 'Прилет',
                                    'Аэропорт вылета','Аэропорт прилета','В пути', 'Дата']
                if not all(field in item for field in required_fields):
                    print(f"Пропуск записи: отсутствуют обязательные поля - {item}")
                    continue
                c.execute('''INSERT INTO avia_tickets 
                                                        (avialine, price, departure_time, arrival_time,
                                    departure_airoport,arrival_airoport,duration,data)
                                                        VALUES (?, ?, ?, ?, ?, ?, ?,?)''',
                          (item['Авиакомпания'],
                           item['Цена'],
                           item['Вылет'],
                           item['Прилет'],
                           item['Аэропорт вылета'],
                           item['Аэропорт прилета'],
                           item['В пути'],
                           item['Дата']))
            conn.commit()
            conn.close()
            print(f"Успешно сохранено {len(data)} записей в базу данных {db_name}")
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
            print("=== Начало работы парсера AVIASALES ===")

            # Открытие сайта

            self.driver.get("https://www.aviasales.ru")
            print("Сайт открыт")

            # Принятие cookies
            self.accept_cookies()

            # Переход к поиску билетов
            # if not self.navigate_to_tickets():
            #     return False

            # Выполнение поиска
            if not self.search_planes():
                return False

            # Парсинг результатов
            results = self.parse_results()

            # Сохранение результатов
            self.save_results(results)

            return True

        except Exception as e:
            print(f"Критическая ошибка: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("Браузер закрыт")

