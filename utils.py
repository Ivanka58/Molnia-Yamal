import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from datetime import datetime
import json
from webdriver_manager.chrome import ChromeDriverManager  # <-- Импортируем менеджер драйверов

load_dotenv()

PASSWORD = os.getenv('PASSWORD')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

def authenticate_user(user_password):
    return user_password == PASSWORD

def check_availability(check_in_date, check_out_date, adults_count, children_count):
    # AUTOINSTALL ChromeDriver нужной версии с помощью webdriver_manager
    service = ChromeService(executable_path=ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Открываем главную страницу сайта
        driver.get("https://molnia.ru/")
        
        # Поиск элементов формы
        date_field = driver.find_element(By.ID, "checkin-date")
        date_field.clear()
        date_field.send_keys(check_in_date)
        
        out_date_field = driver.find_element(By.ID, "checkout-date")
        out_date_field.clear()
        out_date_field.send_keys(check_out_date)
        
        # Разделённый ввод взрослого и детского контингента
        guests_field_adults = driver.find_element(By.ID, "adults-count")
        guests_field_adults.clear()
        guests_field_adults.send_keys(str(adults_count))
        
        guests_field_children = driver.find_element(By.ID, "children-count")
        guests_field_children.clear()
        guests_field_children.send_keys(str(children_count))
        
        submit_btn = driver.find_element(By.CLASS_NAME, "search-button")
        submit_btn.click()
        
        # Ожидание результата
        wait = WebDriverWait(driver, 10)
        results = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "room-item")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rooms = soup.select('.room-item')
        
        responses = []
        for room in rooms:
            title = room.select_one('.room-title')
            price = room.select_one('.price')
            
            response = f"""
            🌟 Номер найден!
            
            Корпус: {title.text.strip() if title else "Не указано"}
            
            Номер: {title.text.strip() if title else "Не указано"}
            
            Числа: {check_in_date} — {check_out_date}
            
            Стоимость: {price.text.strip() if price else "Не указана"}
            """
            responses.append(response)
        
        return "\\n\\n".join(responses) if responses else "🚫 На данный момент свободных номеров нет."
    except Exception as e:
        error_msg = f"Произошла ошибка при обработке сайта: {str(e)}"
        bot.send_message(ADMIN_CHAT_ID, error_msg)  # Отправляем сообщение администратору
        return error_msg
    finally:
        driver.quit()

# Универсальные функции для работы с JSON
def save_to_file(data, filename="monitoring.json"):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

def load_from_file(filename="monitoring.json"):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
