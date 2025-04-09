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
import random


class RZDParser:
    def __init__(self, from_station, to_station, date):
        self.driver = None
        self.wait_timeout = 30
        self.setup_driver()
        self.from_station=from_station
        self.to_station=to_station
        self.date=date

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
            self.driver.execute_script("arguments[0].value = ''; arguments[0].focus();", from_input)

            self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//li[contains(., '{self.from_station}')][1]"))
            ).click()
            time.sleep(0.5)  # Важная пауза после выбора

            # 2. Ввод "Куда" с расширенными проверками
            to_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Куда')]"))
            )

            # Тройная проверка доступности поля
            WebDriverWait(self.driver, 5).until(lambda d: to_input.is_displayed() and to_input.is_enabled())
            self.driver.execute_script("arguments[0].scrollIntoView(true);", to_input)

            # Очистка и ввод с человекообразным поведением
            self.driver.execute_script("arguments[0].value = '';", to_input)
            to_input.click()
            time.sleep(0.5)

            # Ожидание и выбор варианта
            time.sleep(0.5)
            self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//li[contains(., '{self.to_station}')][1]"))
            ).click()

            # 3. Ввод даты
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
                        'arrival_time': card.find_element(By.XPATH, ".//div[contains(@class, 'card-route__date-time--to')]").text,
                        'duration': card.find_element(By.XPATH, ".//div[contains(@class, 'card-route__duration')]").text,
                        'seats': self.get_seats2(card)
                    }
                    trains.append(train_data)
                except Exception as e:
                    print(f"Ошибка парсинга карточки: {e}")
                    continue

            print(f"Найдено {len(trains)} поездов")
            return trains
        except Exception as e:
            print(f"Ошибка парсинга результатов: {e}")
            return []

    def get_seats2(self,card):
        aseats=[]
        i=0
        try:
             seats=card.find_elements(By.XPATH,".//div[contains(@class, 'col body__classes')]")
             try:
                for seat in seats:
                    t=seat.text
                    seat_datum=t.splitlines()
                    while i <= len(seat_datum)/4-1:
                        seat_data = {
                            'name': seat_datum[4*i],
                            'price': seat_datum[4*i+3],
                            'sum':  seat_datum[4*i+1]
                        }
                        i+=1
                        aseats.append(seat_data)
             except Exception as e:
                aseats.append("Мест нет")
             return aseats
        except Exception as e:
            print(f"Ошибка парсинга результатов: {e}")
            return "Мест нет"


    def save_results(self, data, filename="rzd_results.csv"):
        """Сохранение результатов в CSV"""
        if not data:
            print("Нет данных для сохранения")
            return False

        try:
            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"Результаты сохранены в {filename}")
            return True
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return False

    def run(self, from_station="Москва", to_station="Казань", date="20.02.2025"):
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

            return True

        except Exception as e:
            print(f"Критическая ошибка: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("Браузер закрыт")

class AVIAParser:
    def __init__(self, from_station, to_station, date):
        self.driver = None
        self.wait_timeout = 30
        self.setup_driver()
        self.from_station=from_station
        self.to_station=to_station
        self.date=date

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

    def search_planes(self):
        """Поиск поездов по заданным параметрам"""
        try:
            # 1. Ввод "Откуда"
            from_input = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@placeholder, 'ткуда') or contains(@placeholder, 'Откуда')]"))
            )
            self.driver.execute_script("arguments[0].value = ''; arguments[0].focus();", from_input)

            self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//li[contains(., '{self.from_station}')][1]"))
            ).click()
            time.sleep(0.5)  # Важная пауза после выбора

            # 2. Ввод "Куда" с расширенными проверками
            to_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Куда')]"))
            )

            # Тройная проверка доступности поля
            WebDriverWait(self.driver, 5).until(lambda d: to_input.is_displayed() and to_input.is_enabled())
            self.driver.execute_script("arguments[0].scrollIntoView(true);", to_input)

            # Очистка и ввод с человекообразным поведением
            self.driver.execute_script("arguments[0].value = '';", to_input)
            to_input.click()
            time.sleep(0.5)

            # Ожидание и выбор варианта
            time.sleep(0.5)
            self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//li[contains(., '{self.to_station}')][1]"))
            ).click()

            # 3. Ввод даты
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
        plains = []
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
                        'arrival_time': card.find_element(By.XPATH, ".//div[contains(@class, 'card-route__date-time--to')]").text,
                        'duration': card.find_element(By.XPATH, ".//div[contains(@class, 'card-route__duration')]").text,
                        'seats': self.get_seats2(card)
                    }
                    trains.append(train_data)
                except Exception as e:
                    print(f"Ошибка парсинга карточки: {e}")
                    continue

            print(f"Найдено {len(trains)} поездов")
            return trains
        except Exception as e:
            print(f"Ошибка парсинга результатов: {e}")
            return []

    def get_seats2(self,card):
        aseats=[]
        i=0
        try:
             seats=card.find_elements(By.XPATH,".//div[contains(@class, 'col body__classes')]")
             try:
                for seat in seats:
                    t=seat.text
                    seat_datum=t.splitlines()
                    while i <= len(seat_datum)/4-1:
                        seat_data = {
                            'name': seat_datum[4*i],
                            'price': seat_datum[4*i+3],
                            'sum':  seat_datum[4*i+1]
                        }
                        i+=1
                        aseats.append(seat_data)
             except Exception as e:
                aseats.append("Мест нет")
             return aseats
        except Exception as e:
            print(f"Ошибка парсинга результатов: {e}")
            return "Мест нет"


    def save_results(self, data, filename="aviasales_results.csv"):
        """Сохранение результатов в CSV"""
        if not data:
            print("Нет данных для сохранения")
            return False

        try:
            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"Результаты сохранены в {filename}")
            return True
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return False

    def run(self, from_station="Москва", to_station="Казань", date="20.02.2025"):
        """Основной метод запуска парсера"""
        try:
            print("=== Начало работы парсера AVIASALES ===")

            # Открытие сайта
            self.driver.get("https://www.aviasales.ru/")
            print("Сайт открыт")

            # Принятие cookies
            self.accept_cookies()

            # Переход к поиску билетов
            if not self.navigate_to_tickets():
                return False

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

if __name__ == "__main__":
    from_station="Москва"
    to_station="Казань"
    date="20.04.2025"  # Формат: ДД.ММ.ГГГГ

    rzd_parser = RZDParser(from_station, to_station, date)
    #aviasales_parser = AviasalesParser(from_city, to_city, date)

    with ThreadPoolExecutor(max_workers=2) as executor:
        # Отправляем задачи в пул потоков
        future_rzd = executor.submit(rzd_parser.run)
        #future_aviasales = executor.submit(aviasales_parser.parse)
    if future_rzd.done():  # Проверяем, завершена ли задача
        if future_rzd.exception() is None:  # Если нет ошибок
            print("=== Работа завершена успешно ===")
        else:
            print("=== Возникли проблемы при работе ===")
    # if success:
    #     print("=== Работа завершена успешно ===")
    # else:
    #     print("=== Возникли проблемы при работе ===")
