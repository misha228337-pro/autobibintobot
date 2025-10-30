import pyautogui
import time
import random
import logging
import pytesseract
import keyboard
import psutil
import re
from typing import Optional, Tuple, List
import os
import config
from PIL import Image, ImageGrab

# Настройка пути к Tesseract если указан в конфиге
if config.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

class TelegramBotAutomatorSimple:
    def __init__(self, num_windows: int):
        self.running = True
        self.confidence = 0.7
        pyautogui.PAUSE = 0.5
        pyautogui.FAILSAFE = True
        self.num_windows = num_windows
        self.is_setup_phase = True  # Флаг для фазы настройки
        self.current_window_index = 0  # Индекс текущего окна (от 0 до num_windows-1)

    def find_telegram_window(self) -> bool:
        """Поиск окна Telegram среди запущенных процессов"""
        logging.info("Поиск окна Telegram...")
        
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and any(name in proc.info['name'].lower() for name in ['telegram', 'telegram desktop']):
                    logging.info(f"Найден процесс Telegram: {proc.info['name']}")
                    return True
        except (psutil.NoSuchPr ocess, psutil.AccessDenied) as e:
            logging.warning(f"Ошибка при поиске процессов: {e}")
        
        logging.error("Telegram не найден в запущенных процессах")
        return False
    
    def activate_telegram_window(self) -> bool:
        """Активация окна Telegram"""
        try:
            logging.info("Активация окна Telegram...")
            pyautogui.hotkey('alt', 'tab')
            time.sleep(1)
            logging.info("Окно Telegram должно быть активно.")
            return True
        except Exception as e:
            logging.error(f"Ошибка при активации Telegram: {e}")
            return False

    def find_image_pil(self, image_path: str, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int]]:
        """
        Ищет изображение на экране, сравнивая пиксели (метод PIL).
        Очень медленно, но не требует OpenCV.
        region: (left, top, width, height)
        """
        try:
            # Загружаем изображение для поиска
            needle = Image.open(image_path)
            needle_width, needle_height = needle.size
            
            # Делаем скриншот нужной области или всего экрана
            if region:
                # Конвертируем region (left, top, width, height) в bbox (left, top, right, bottom)
                left, top, width, height = region
                # Проверяем, что координаты корректны
                if width <= 0 or height <= 0:
                    logging.error(f"Неверный размер области поиска: width={width}, height={height}")
                    return None
                bbox = (left, top, left + width, top + height)
                screenshot = ImageGrab.grab(bbox=bbox)
            else:
                screenshot = pyautogui.screenshot()
            
            screen_width, screen_height = screenshot.size
            
            # Конвертируем в формат, удобный для сравнения
            screenshot_pixels = screenshot.load()
            needle_pixels = needle.load()
            
            logging.info(f"Начинаю поиск изображения {image_path}... Это может занять время.")

            # Ищем совпадение
            for sx in range(screen_width - needle_width + 1):
                for sy in range(screen_height - needle_height + 1):
                    match = True
                    
                    for nx in range(needle_width):
                        for ny in range(needle_height):
                            # Получаем пиксели
                            screen_pixel = screenshot_pixels[sx + nx, sy + ny]
                            needle_pixel = needle_pixels[nx, ny]
                            
                            # Сравнение RGB с допуском
                            r_diff = abs(screen_pixel[0] - needle_pixel[0])
                            g_diff = abs(screen_pixel[1] - needle_pixel[1])
                            b_diff = abs(screen_pixel[2] - needle_pixel[2])
                            
                            if r_diff + g_diff + b_diff > config.PIXEL_TOLERANCE:
                                match = False
                                break
                        if not match:
                            break
                    
                    if match:
                        # Нашли совпадение, возвращаем центр
                        click_x = sx + needle_width // 2
                        click_y = sy + needle_height // 2
                        
                        # Корректируем координаты, если была задана область поиска
                        if region:
                            click_x += region[0]
                            click_y += region[1]
                            
                        logging.info(f"Изображение найдено в ({click_x}, {click_y})")
                        return (click_x, click_y)

        except FileNotFoundError:
            logging.error(f"Файл не найден: {image_path}")
        except Exception as e:
            logging.error(f"Ошибка при поиске изображения: {e}")
            
        return None

    def find_and_click_image_simple(self, image_path: str, timeout: int = 10) -> bool:
        """Поиск изображения с помощью PIL и клик по нему"""
        logging.info(f"Поиск изображения '{image_path}' в нижней части экрана...")
        
        screen_width, screen_height = pyautogui.size()
        # Определяем область поиска: нижняя половина экрана (формат: left, top, width, height)
        top = screen_height // 2
        height = screen_height - top - int(screen_height * 0.05) # Нижняя половина минус 5% от нижнего края
        search_region = (0, top, screen_width, height)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            location = self.find_image_pil(image_path, region=search_region)
            if location:
                logging.info(f"Изображение '{image_path}' найдено. Кликаю в {location}.")
                pyautogui.click(location[0], location[1])
                return True
            
            logging.info("Изображение не найдено, пробую снова через 1 секунду...")
            time.sleep(1)

        logging.warning(f"Изображение '{image_path}' не найдено за {timeout} секунд.")
        return False


    def handle_ad(self) -> bool:
        """Обнаружение и обработка рекламы"""
        logging.info("Проверка на наличие рекламы...")
        
        # Список возможных текстов на кнопках для пропуска рекламы
        skip_buttons = ["Пропустить", "Ладно", "Далее"]
        screenshot = pyautogui.screenshot()
        
        try:
            # Используем OCR для поиска текста на скриншоте
            data = pytesseract.image_to_data(screenshot, lang=config.OCR_LANGUAGES, output_type=pytesseract.Output.DICT)
            
            found_skip_button = False
            for i in range(len(data['text'])):
                for button_text in skip_buttons:
                    if button_text.lower() in data['text'][i].lower():
                        if int(data['conf'][i]) > 60:
                            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                            click_x, click_y = x + w // 2, y + h // 2
                            logging.info(f"Найдена кнопка пропуска рекламы '{data['text'][i]}' в ({click_x}, {click_y}). Кликаю.")
                            pyautogui.click(click_x, click_y)
                            found_skip_button = True
                            time.sleep(2)
                            return True

            if not found_skip_button:
                logging.info("Реклама не обнаружена.")
                return False

        except Exception as e:
            logging.error(f"Ошибка при обработке рекламы: {e}")
            return False
        
        return False

    def switch_telegram_window(self):
        try:
            if self.is_setup_phase:
                # Фаза настройки: переместить терминал в конец
                logging.info("Фаза настройки: перемещение терминала в конец...")
                pyautogui.keyDown('alt')
                time.sleep(0.1)

                # Нажимаем Tab на количество всех окон, чтобы "протолкнуть" терминал в конец
                for _ in range(self.num_windows):
                    pyautogui.press('tab')
                    time.sleep(0.05)

                pyautogui.keyUp('alt')
                time.sleep(0.1)

                logging.info("Фаза настройки завершена. Терминал в конце.")
                self.is_setup_phase = False
                self.current_window_index = 0  # Начинаем с первого ТГ

            else:
                # Рабочая фаза: циклическое переключение между ТГ окнами
                # Каждый раз нажимаем на 1 больше: ТГ1→ТГ2 (1 раз), ТГ2→ТГ3 (2 раза), и т.д.
                pyautogui.keyDown('alt')
                time.sleep(0.1)

                num_tabs = self.current_window_index + 1
                logging.info(f"Переключение на ТГ окно (нажатие Tab {num_tabs} раз)...")

                for _ in range(num_tabs):
                    pyautogui.press('tab')
                    time.sleep(0.05)

                pyautogui.keyUp('alt')
                time.sleep(0.1)

                # Переходим к следующему ТГ окну
                self.current_window_index = (self.current_window_index + 1) % self.num_windows
                logging.info(f"Текущее окно: {self.current_window_index + 1}/{self.num_windows}")

        except Exception as e:
            logging.error(f"Ошибка при переключении окон: {e}")


    def main_automation_loop(self) -> None:
        """Основной цикл автоматизации"""
        logging.info("Запуск основной программы автоматизации (простая версия)...")
        
        if not self.find_telegram_window():
            logging.error("Telegram не найден. Пожалуйста, запустите Telegram.")
            return
        
        # Первое, самое первое переключение из терминала в ТГ1
        if not self.activate_telegram_window():
            logging.error("Не удалось активировать окно Telegram.")
            return
            
        logging.info(f"Нажмите '{config.STOP_KEY}' для остановки.")
        
        while self.running:
            if keyboard.is_pressed(config.STOP_KEY):
                logging.info("Программа остановлена пользователем.")
                self.running = False
                break

            logging.info(f"Работа в окне #{self.current_window_index + 1}")

            # 1. Проверяем и закрываем рекламу
            if self.handle_ad():
                logging.info("Реклама обработана.")
                
            # 2. Ищем и кликаем на сердце
            elif self.find_and_click_image_simple('heart_button.png', timeout=10):
                logging.info("Успешно кликнули на сердце.")
                time.sleep(random.uniform(config.MIN_RATING_INTERVAL, config.MAX_RATING_INTERVAL))
            
            else:
                logging.warning("Кнопка с сердцем не найдена.")
                time.sleep(3)
            
            # 3. Переключаемся на следующее окно, только если их больше одного
            if self.num_windows > 1:
                self.switch_telegram_window()
                time.sleep(0.5) # Пауза после переключения

    def stop_automation(self) -> None:
        """Остановка автоматизации"""
        self.running = False

def main():
    """Главная функция"""
    print("=" * 60)
    print("🤖 Автоматизация бота для знакомств v2.2 (поддержка нескольких окон)")
    print("=" * 60)
    
    while True:
        try:
            num_windows_str = input("Введите количество окон Telegram для автоматизации: ")
            num_windows = int(num_windows_str)
            if num_windows > 0:
                break
            else:
                print("Пожалуйста, введите положительное число.")
        except ValueError:
            print("Некорректный ввод. Пожалуйста, введите число.")

    print("=" * 60)
    print("📋 Инструкция:")
    print(f"1. ✅ Убедитесь, что у вас открыто ровно {num_windows} окон Telegram.")
    print("2. ✅ Расположите их в списке Alt+Tab СРАЗУ ПОСЛЕ ОКНА ТЕРМИНАЛА.")
    print("   (Пример: Терминал -> ТГ1 -> ТГ2 -> ...)")
    print("3. ✅ Убедитесь, что 'heart_button.png' - это идеальный скриншот.")
    print(f"4. 🚀 Запустите программу. Для остановки нажмите '{config.STOP_KEY}'.")
    print("=" * 60)
    
    input("Нажмите Enter для начала работы...")
    
    automator = TelegramBotAutomatorSimple(num_windows)
    automator.main_automation_loop()
    
    logging.info("Работа программы завершена.")
    print("Программа завершена.")

if __name__ == "__main__":
    main()