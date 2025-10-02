#!/usr/bin/env python3
"""
ПРОДВИНУТЫЙ ГЕНЕРАТОР QR-КОДОВ С ШИФРОВАНИЕМ ИЗОБРАЖЕНИЙ
"""

import os
import sys
import subprocess
import importlib.metadata
from pathlib import Path
import base64
import zlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import hashlib

class DependencyManager:
    """Менеджер зависимостей"""
    
    REQUIRED_PACKAGES = {
        'qrcode': '7.4.2',
        'Pillow': '9.0.0',
        'vobject': '0.9.6',
        'pycryptodome': '3.20.0'
    }
    
    @classmethod
    def check_dependencies(cls):
        """Проверяет и устанавливает зависимости"""
        missing_packages = []
        
        print("🔍 Проверка зависимостей...")
        
        for package, required_version in cls.REQUIRED_PACKAGES.items():
            try:
                installed_version = importlib.metadata.version(package)
                print(f"✅ {package}: {installed_version} (требуется: {required_version}+)")
                
            except importlib.metadata.PackageNotFoundError:
                print(f"❌ {package}: не установлен")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n📦 Установка недостающих пакетов: {', '.join(missing_packages)}")
            cls.install_packages(missing_packages)
        else:
            print("\n✅ Все зависимости установлены!")
    
    @classmethod
    def install_packages(cls, packages):
        """Устанавливает пакеты через pip"""
        try:
            for package in packages:
                print(f"📦 Устанавливаю {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                     f"{package}>={cls.REQUIRED_PACKAGES[package]}"])
            print("✅ Все пакеты успешно установлены!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка установки пакетов: {e}")
            sys.exit(1)

# Импортируем основные библиотеки после проверки зависимостей
DependencyManager.check_dependencies()

import qrcode
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime

class ImageEncoder:
    """Класс для шифрования и кодирования изображений"""
    
    @staticmethod
    def image_to_base64(image_path, max_size_kb=500):
        """Конвертирует изображение в base64 с оптимизацией размера"""
        try:
            with Image.open(image_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Оптимизируем размер для QR-кода
                quality = 85
                while True:
                    # Сохраняем во временный буфер для проверки размера
                    from io import BytesIO
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    size_kb = len(buffer.getvalue()) // 1024
                    
                    if size_kb <= max_size_kb or quality <= 10:
                        break
                    quality -= 15
                
                # Получаем финальные данные
                buffer.seek(0)
                image_data = buffer.getvalue()
                
                # Кодируем в base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                print(f"📊 Размер изображения: {size_kb} KB, качество: {quality}%")
                return f"data:image/jpeg;base64,{base64_data}"
                
        except Exception as e:
            raise Exception(f"Ошибка обработки изображения: {e}")
    
    @staticmethod
    def encrypt_data(data, password):
        """Шифрует данные с использованием AES"""
        try:
            # Генерируем ключ из пароля
            key = hashlib.sha256(password.encode()).digest()
            
            # Генерируем случайный IV
            iv = get_random_bytes(16)
            
            # Создаем шифр
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Шифруем данные
            encrypted_data = cipher.encrypt(pad(data.encode(), AES.block_size))
            
            # Комбинируем IV + зашифрованные данные
            result = iv + encrypted_data
            
            # Кодируем в base64
            return base64.b64encode(result).decode('utf-8')
            
        except Exception as e:
            raise Exception(f"Ошибка шифрования: {e}")
    
    @staticmethod
    def decrypt_data(encrypted_data, password):
        """Расшифровывает данные"""
        try:
            # Декодируем из base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Извлекаем IV и зашифрованные данные
            iv = encrypted_bytes[:16]
            encrypted_bytes = encrypted_bytes[16:]
            
            # Генерируем ключ
            key = hashlib.sha256(password.encode()).digest()
            
            # Создаем шифр для расшифровки
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Расшифровываем
            decrypted_data = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            raise Exception(f"Ошибка расшифровки: {e}")
    
    @staticmethod
    def compress_data(data):
        """Сжимает данные"""
        return base64.b64encode(zlib.compress(data.encode())).decode('utf-8')
    
    @staticmethod
    def decompress_data(compressed_data):
        """Распаковывает данные"""
        return zlib.decompress(base64.b64decode(compressed_data)).decode('utf-8')

class QRCodeGenerator:
    """Основной класс генератора QR-кодов"""
    
    def __init__(self):
        self.data_types = {
            '1': {'name': '🌐 URL/Ссылка', 'handler': self.create_url_qr},
            '2': {'name': '📝 Текст', 'handler': self.create_text_qr},
            '3': {'name': '📶 WiFi', 'handler': self.create_wifi_qr},
            '4': {'name': '📧 Email', 'handler': self.create_email_qr},
            '5': {'name': '💬 SMS', 'handler': self.create_sms_qr},
            '6': {'name': '👤 vCard (контакт)', 'handler': self.create_vcard_qr},
            '7': {'name': '📍 Геолокация', 'handler': self.create_geo_qr},
            '8': {'name': '📞 Телефон', 'handler': self.create_phone_qr},
            '9': {'name': '📅 Событие', 'handler': self.create_event_qr},
            '10': {'name': '🖼️ Изображение (Base64)', 'handler': self.create_image_qr},
            '11': {'name': '🔐 Зашифрованное изображение', 'handler': self.create_encrypted_image_qr},
            '12': {'name': '📁 Файл (текстовый)', 'handler': self.create_file_qr}
        }
        
        self.encoder = ImageEncoder()
    
    def clear_screen(self):
        """Очищает экран консоли"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Выводит заголовок программы"""
        print("🎯" + "="*60)
        print("           ПРОДВИНУТЫЙ ГЕНЕРАТОР QR-КОДОВ С ШИФРОВАНИЕМ")
        print("="*60 + "🎯")
        print()
    
    def get_user_choice(self, options, prompt="Выберите опцию"):
        """Получает выбор пользователя"""
        while True:
            print(f"\n{prompt}:")
            for key, value in options.items():
                print(f"  {key}) {value}")
            
            choice = input("\nВаш выбор: ").strip()
            if choice in options:
                return choice
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
    
    def get_input(self, prompt, required=True, default=None, password=False):
        """Получает ввод от пользователя"""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                if password:
                    import getpass
                    user_input = getpass.getpass(f"{prompt}: ")
                else:
                    user_input = input(f"{prompt}: ").strip()
            
            if not required or user_input:
                return user_input
            print("❌ Это поле обязательно для заполнения.")
    
    def create_url_qr(self):
        """Создает QR-код для URL"""
        print("\n🌐 СОЗДАНИЕ QR-КОДА ДЛЯ URL")
        print("-" * 30)
        
        url = self.get_input("Введите URL (с http:// или https://)", required=True)
        filename = self.get_input("Имя файла для сохранения", required=False, default="url_qr.png")
        
        return url, filename
    
    def create_text_qr(self):
        """Создает QR-код для текста"""
        print("\n📝 СОЗДАНИЕ QR-КОДА ДЛЯ ТЕКСТА")
        print("-" * 30)
        
        text = self.get_input("Введите текст", required=True)
        filename = self.get_input("Имя файла для сохранения", required=False, default="text_qr.png")
        
        return text, filename
    
    def create_wifi_qr(self):
        """Создает QR-код для WiFi"""
        print("\n📶 СОЗДАНИЕ QR-КОДА ДЛЯ WiFi")
        print("-" * 30)
        
        ssid = self.get_input("Название сети (SSID)", required=True)
        password = self.get_input("Пароль", required=False)
        encryption = self.get_user_choice(
            {'WPA': 'WPA/WPA2', 'WEP': 'WEP', 'nopass': 'Без пароля'},
            "Тип шифрования"
        )
        
        hidden = self.get_input("Скрытая сеть? (y/n)", required=False, default="n").lower() == 'y'
        
        wifi_config = f"WIFI:S:{ssid};T:{encryption};"
        if password:
            wifi_config += f"P:{password};"
        if hidden:
            wifi_config += "H:true;"
        wifi_config += ";"
        
        filename = self.get_input("Имя файла для сохранения", required=False, default="wifi_qr.png")
        
        return wifi_config, filename
    
    def create_email_qr(self):
        """Создает QR-код для Email"""
        print("\n📧 СОЗДАНИЕ QR-КОДА ДЛЯ EMAIL")
        print("-" * 30)
        
        email = self.get_input("Email получателя", required=True)
        subject = self.get_input("Тема письма", required=False)
        body = self.get_input("Текст письма", required=False)
        
        email_url = f"mailto:{email}"
        params = []
        if subject:
            params.append(f"subject={self.url_encode(subject)}")
        if body:
            params.append(f"body={self.url_encode(body)}")
        
        if params:
            email_url += "?" + "&".join(params)
        
        filename = self.get_input("Имя файла для сохранения", required=False, default="email_qr.png")
        
        return email_url, filename
    
    def create_sms_qr(self):
        """Создает QR-код для SMS"""
        print("\n💬 СОЗДАНИЕ QR-КОДА ДЛЯ SMS")
        print("-" * 30)
        
        number = self.get_input("Номер телефона", required=True)
        message = self.get_input("Текст сообщения", required=False)
        
        sms_url = f"sms:{number}"
        if message:
            sms_url += f"?body={self.url_encode(message)}"
        
        filename = self.get_input("Имя файла для сохранения", required=False, default="sms_qr.png")
        
        return sms_url, filename
    
    def create_vcard_qr(self):
        """Создает QR-код для vCard"""
        print("\n👤 СОЗДАНИЕ QR-КОДА ДЛЯ VCARD (КОНТАКТ)")
        print("-" * 30)
        
        print("\nЗаполните информацию о контакте:")
        first_name = self.get_input("Имя", required=True)
        last_name = self.get_input("Фамилия", required=False)
        company = self.get_input("Компания", required=False)
        title = self.get_input("Должность", required=False)
        phone = self.get_input("Телефон", required=False)
        email = self.get_input("Email", required=False)
        website = self.get_input("Веб-сайт", required=False)
        
        # Формируем vCard
        vcard = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"N:{last_name or ''};{first_name or ''};;;",
            f"FN:{first_name} {last_name or ''}",
        ]
        
        if company:
            vcard.append(f"ORG:{company}")
        if title:
            vcard.append(f"TITLE:{title}")
        if phone:
            vcard.append(f"TEL;TYPE=WORK,VOICE:{phone}")
        if email:
            vcard.append(f"EMAIL;TYPE=WORK:{email}")
        if website:
            vcard.append(f"URL:{website}")
        
        vcard.append("END:VCARD")
        
        vcard_data = "\n".join(vcard)
        filename = self.get_input("Имя файла для сохранения", required=False, default="contact_qr.png")
        
        return vcard_data, filename
    
    def create_geo_qr(self):
        """Создает QR-код для геолокации"""
        print("\n📍 СОЗДАНИЕ QR-КОДА ДЛЯ ГЕОЛОКАЦИИ")
        print("-" * 30)
        
        latitude = self.get_input("Широта (например: 55.7558)", required=True)
        longitude = self.get_input("Долгота (например: 37.6173)", required=True)
        altitude = self.get_input("Высота (опционально)", required=False)
        
        geo_url = f"geo:{latitude},{longitude}"
        if altitude:
            geo_url += f",{altitude}"
        
        filename = self.get_input("Имя файла для сохранения", required=False, default="geo_qr.png")
        
        return geo_url, filename
    
    def create_phone_qr(self):
        """Создает QR-код для телефона"""
        print("\n📞 СОЗДАНИЕ QR-КОДА ДЛЯ ТЕЛЕФОНА")
        print("-" * 30)
        
        number = self.get_input("Номер телефона", required=True)
        phone_url = f"tel:{number}"
        
        filename = self.get_input("Имя файла для сохранения", required=False, default="phone_qr.png")
        
        return phone_url, filename
    
    def create_event_qr(self):
        """Создает QR-код для события"""
        print("\n📅 СОЗДАНИЕ QR-КОДА ДЛЯ СОБЫТИЯ")
        print("-" * 30)
        
        title = self.get_input("Название события", required=True)
        location = self.get_input("Местоположение", required=False)
        description = self.get_input("Описание", required=False)
        start_date = self.get_input("Дата начала (ГГГГММДД)", required=False)
        end_date = self.get_input("Дата окончания (ГГГГММДД)", required=False)
        
        # Формируем событие
        event = [
            "BEGIN:VEVENT",
            f"SUMMARY:{title}",
        ]
        
        if location:
            event.append(f"LOCATION:{location}")
        if description:
            event.append(f"DESCRIPTION:{description}")
        if start_date:
            event.append(f"DTSTART:{start_date}")
        if end_date:
            event.append(f"DTEND:{end_date}")
        
        event.append("END:VEVENT")
        
        event_data = "\n".join(event)
        filename = self.get_input("Имя файла для сохранения", required=False, default="event_qr.png")
        
        return event_data, filename
    
    def create_image_qr(self):
        """Создает QR-код с изображением в base64"""
        print("\n🖼️ СОЗДАНИЕ QR-КОДА С ИЗОБРАЖЕНИЕМ")
        print("-" * 30)
        
        image_path = self.get_input("Путь к изображению", required=True)
        
        if not os.path.exists(image_path):
            print("❌ Файл не найден!")
            return None, None
        
        try:
            # Конвертируем изображение в base64
            base64_image = self.encoder.image_to_base64(image_path)
            
            # Создаем JSON с метаданными
            image_data = {
                "type": "image",
                "format": "jpeg",
                "data": base64_image,
                "timestamp": datetime.now().isoformat()
            }
            
            data = json.dumps(image_data, ensure_ascii=False)
            filename = self.get_input("Имя файла для сохранения", required=False, default="image_qr.png")
            
            return data, filename
            
        except Exception as e:
            print(f"❌ Ошибка обработки изображения: {e}")
            return None, None
    
    def create_encrypted_image_qr(self):
        """Создает QR-код с зашифрованным изображением"""
        print("\n🔐 СОЗДАНИЕ QR-КОДА С ЗАШИФРОВАННЫМ ИЗОБРАЖЕНИЕМ")
        print("-" * 40)
        
        image_path = self.get_input("Путь к изображению", required=True)
        password = self.get_input("Пароль для шифрования", required=True, password=True)
        confirm_password = self.get_input("Подтвердите пароль", required=True, password=True)
        
        if password != confirm_password:
            print("❌ Пароли не совпадают!")
            return None, None
        
        if not os.path.exists(image_path):
            print("❌ Файл не найден!")
            return None, None
        
        try:
            # Конвертируем изображение в base64
            base64_image = self.encoder.image_to_base64(image_path, max_size_kb=300)
            
            # Шифруем данные
            encrypted_data = self.encoder.encrypt_data(base64_image, password)
            
            # Создаем JSON с метаданными
            encrypted_package = {
                "type": "encrypted_image",
                "algorithm": "AES-256-CBC",
                "data": encrypted_data,
                "timestamp": datetime.now().isoformat()
            }
            
            data = json.dumps(encrypted_package, ensure_ascii=False)
            filename = self.get_input("Имя файла для сохранения", required=False, default="encrypted_image_qr.png")
            
            print("✅ Изображение успешно зашифровано!")
            return data, filename
            
        except Exception as e:
            print(f"❌ Ошибка шифрования: {e}")
            return None, None
    
    def create_file_qr(self):
        """Создает QR-код с текстовым файлом"""
        print("\n📁 СОЗДАНИЕ QR-КОДА С ТЕКСТОВЫМ ФАЙЛОМ")
        print("-" * 35)
        
        file_path = self.get_input("Путь к текстовому файлу", required=True)
        
        if not os.path.exists(file_path):
            print("❌ Файл не найден!")
            return None, None
        
        try:
            # Читаем файл
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Проверяем размер
            if len(file_content) > 10000:  # Ограничение для QR-кода
                print("⚠️ Файл слишком большой для QR-кода. Будут использованы первые 10000 символов.")
                file_content = file_content[:10000]
            
            # Создаем JSON с метаданными
            file_data = {
                "type": "text_file",
                "filename": os.path.basename(file_path),
                "data": file_content,
                "timestamp": datetime.now().isoformat()
            }
            
            data = json.dumps(file_data, ensure_ascii=False)
            filename = self.get_input("Имя файла для сохранения", required=False, default="file_qr.png")
            
            return data, filename
            
        except Exception as e:
            print(f"❌ Ошибка чтения файла: {e}")
            return None, None
    
    def url_encode(self, text):
        """Простое URL кодирование"""
        return text.replace(' ', '%20').replace('&', '%26')
    
    def get_qr_settings(self):
        """Получает настройки для QR-кода"""
        print("\n🎨 НАСТРОЙКИ QR-КОДА")
        print("-" * 20)
        
        settings = {}
        
        # Цвета
        color_choice = self.get_user_choice(
            {'1': '⚫ Классический (черный/белый)',
             '2': '⚪ Инвертированный (белый/черный)',
             '3': '🔵 Синий',
             '4': '🟢 Зеленый',
             '5': '🔴 Красный',
             '6': '🟣 Фиолетовый',
             '7': '🎨 Кастомный'},
            "Выберите цветовую схему"
        )
        
        color_presets = {
            '1': ('#000000', '#FFFFFF'),
            '2': ('#FFFFFF', '#000000'),
            '3': ('#1E40AF', '#EFF6FF'),
            '4': ('#065F46', '#ECFDF5'),
            '5': ('#991B1B', '#FEF2F2'),
            '6': ('#5B21B6', '#FAF5FF'),
        }
        
        if color_choice == '7':
            fill_color = self.get_input("Цвет QR-кода (HEX)", required=False, default="#000000")
            bg_color = self.get_input("Цвет фона (HEX)", required=False, default="#FFFFFF")
        else:
            fill_color, bg_color = color_presets[color_choice]
        
        settings['fill_color'] = fill_color
        settings['bg_color'] = bg_color
        
        # Размер
        size_choice = self.get_user_choice(
            {'1': '🔲 Маленький',
             '2': '🔳 Средний',
             '3': '🔲 Большой',
             '4': '📏 Кастомный'},
            "Выберите размер"
        )
        
        size_presets = {'1': 8, '2': 12, '3': 16}
        if size_choice == '4':
            box_size = int(self.get_input("Размер квадрата (6-20)", required=False, default="12"))
        else:
            box_size = size_presets[size_choice]
        
        settings['box_size'] = box_size
        
        return settings
    
    def generate_qr_code(self, data, filename, settings):
        """Генерирует и сохраняет QR-код"""
        if data is None:
            return False
            
        try:
            # Создаем QR-код
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=settings['box_size'],
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Создаем изображение
            qr_img = qr.make_image(
                fill_color=settings['fill_color'],
                back_color=settings['bg_color']
            )
            
            # Сохраняем
            qr_img.save(filename)
            
            # Показываем информацию о файле
            file_size = os.path.getsize(filename) // 1024
            data_size = len(data) // 1024 if len(data) > 1024 else len(data)
            data_unit = "KB" if len(data) > 1024 else "bytes"
            
            print(f"\n✅ QR-код успешно создан!")
            print(f"📁 Файл: {filename}")
            print(f"📊 Размер файла: {file_size} KB")
            print(f"📈 Размер данных: {data_size} {data_unit}")
            print(f"🎨 Цвета: QR-код {settings['fill_color']}, фон {settings['bg_color']}")
            
            # Показываем превью в консоли (упрощенное)
            preview = data[:100] + "..." if len(data) > 100 else data
            print(f"\n👀 Превью данных: {preview}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при создании QR-кода: {e}")
            return False
    
    def main_menu(self):
        """Главное меню программы"""
        while True:
            self.clear_screen()
            self.print_header()
            
            print("Добро пожаловать в продвинутый генератор QR-кодов!")
            print("Выберите тип данных для кодирования:\n")
            
            choice = self.get_user_choice(
                {key: value['name'] for key, value in self.data_types.items()}
            )
            
            # Получаем данные от пользователя
            data, filename = self.data_types[choice]['handler']()
            
            if data is None:
                input("\n⏎ Нажмите Enter для продолжения...")
                continue
            
            # Получаем настройки
            settings = self.get_qr_settings()
            
            # Генерируем QR-код
            success = self.generate_qr_code(data, filename, settings)
            
            # Спрашиваем о продолжении
            if success:
                continue_choice = self.get_user_choice(
                    {'1': '🔄 Создать еще один QR-код',
                     '2': '🔓 Расшифровать QR-код',
                     '3': '🚪 Выйти из программы'},
                    "Что вы хотите сделать дальше?"
                )
                
                if continue_choice == '2':
                    self.decrypt_menu()
                elif continue_choice == '3':
                    print("\n👋 До свидания! Спасибо за использование программы!")
                    break
            else:
                input("\n⏎ Нажмите Enter для продолжения...")
    
    def decrypt_menu(self):
        """Меню для расшифровки QR-кодов"""
        print("\n🔓 РАСШИФРОВКА QR-КОДОВ")
        print("-" * 25)
        
        qr_image_path = self.get_input("Путь к QR-коду с зашифрованными данными", required=True)
        
        if not os.path.exists(qr_image_path):
            print("❌ Файл не найден!")
            return
        
        try:
            # Для реального использования нужно распознавать QR-код
            # Здесь просто демонстрация
            print("\n⚠️  Для расшифровки требуется:")
            print("   - Установить библиотеку для распознавания QR-кодов (pyzbar)")
            print("   - Иметь исходные зашифрованные данные")
            print("   - Знать пароль для расшифровки")
            
            password = self.get_input("Пароль для расшифровки", password=True)
            
            # Демонстрация работы с шифрованием
            test_data = "Тестовые данные для демонстрации"
            encrypted = self.encoder.encrypt_data(test_data, password)
            decrypted = self.encoder.decrypt_data(encrypted, password)
            
            print(f"\n🔐 Демонстрация шифрования:")
            print(f"📤 Исходные данные: {test_data}")
            print(f"📥 Расшифрованные данные: {decrypted}")
            print("✅ Алгоритм шифрования работает корректно!")
            
        except Exception as e:
            print(f"❌ Ошибка при расшифровке: {e}")
        
        input("\n⏎ Нажмите Enter для продолжения...")

def main():
    """Основная функция программы"""
    try:
        generator = QRCodeGenerator()
        generator.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем. До свидания!")
    except Exception as e:
        print(f"\n❌ Произошла непредвиденная ошибка: {e}")

if __name__ == "__main__":
    main()