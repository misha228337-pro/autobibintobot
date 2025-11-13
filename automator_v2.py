import pyautogui
import time
import random
import logging
import keyboard
import psutil
from typing import Optional, Tuple, List
import os
import config
from PIL import Image, ImageGrab
import sys

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
        self.telegram_windows_count = 0

    def find_telegram_window(self) -> bool:
        """Поиск окна Telegram среди запущенных процессов"""
        logging.info("Поиск окна Telegram...")
        
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and any(name in proc.info['name'].lower() for name in ['telegram', 'telegram desktop']):
                    logging.info(f"Найден процесс Telegram: {proc.info['name']}")
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logging.warning(f"Ошибка при поиске процессов: {e}")
        
        logging.error("Telegram не найден в запущенных процессах")
        return False
    
    def activate_telegram_window(self) -> bool:
        """Активация окна Telegram"""
        try:
            logging.info("Активация окна Telegram...")
            pyautogui.hotkey('alt', 'tab')
            time.sleep(0.1)
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

    def scroll_down(self) -> None:
        """Выполняет прокрутку вниз с помощью колеса мыши"""
        screen_width, screen_height = pyautogui.size()
        # Центр экрана для прокрутки
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Перемещаем курсор в центр экрана
        pyautogui.moveTo(center_x, center_y, duration=0.2)
        time.sleep(0.1)
        
        # Выполняем прокрутку вниз
        pyautogui.scroll(-800)  # Отрицательное значение для прокрутки вниз
        time.sleep(0.05)  # Пауза после прокрутки
        
        logging.info("Выполнена прокрутка вниз")

    def find_and_click_image_simple(self, image_path: str, timeout: int = 3, max_scrolls: int = 3) -> bool:
        """Поиск изображения с помощью PIL и клик по нему с возможностью прокрутки"""
        logging.info(f"Поиск изображения '{image_path}' в нижней части экрана...")
        
        screen_width, screen_height = pyautogui.size()
        
        scroll_attempts = 0
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            top = screen_height // 2
            height = screen_height - top - int(screen_height * 0.05) # Нижняя половина минус 5% от нижнего края
            search_region = (0, top, screen_width, height)
            
            location = self.find_image_pil(image_path, region=search_region)
            if location:
                logging.info(f"Изображение '{image_path}' найдено. Кликаю в {location}.")
                pyautogui.click(location[0], location[1])
                return True
            
            # Если изображение не найдено и еще не использовали все попытки прокрутки
            else:
                logging.info("Изображение не найдено, пробую снова через 1 секунду...")
                time.sleep(0.1)

        logging.warning(f"Изображение '{image_path}' не найдено за {timeout} секунд.")
        return False


    def type_search_command(self) -> None:
        """Вводит команду /search в чат"""
        try:
            logging.info("Ввожу команду /search в чат...")
            
            # Просто вводим команду /search без кликов
            pyautogui.typewrite('/search', interval=0.2)
            time.sleep(0.3)
            
            # Нажимаем Enter
            pyautogui.press('enter')
            time.sleep(0.3)
            
            logging.info("Команда /search отправлена")
            
        except Exception as e:
            logging.error(f"Ошибка при вводе команды /search: {e}")

    def switch_telegram_window(self):
        """
        Управляет переключением между окнами Telegram.
        Фаза настройки: определяет кол-во ТГ окон и перемещает терминал в конец.
        Рабочая фаза: циклическое переключение только между ТГ окнами.
        """
        try:
            # ФАЗА НАСТРОЙКИ: первый вызов
            if self.is_setup_phase:
                self.telegram_windows_count = self._count_telegram_windows()

                if self.telegram_windows_count <= 0:
                    logging.warning("❌ Telegram окна не найдены")
                    return False

                logging.info(f"📊 Обнаружено Telegram окон: {self.telegram_windows_count}")

                # Перемещаем терминал в конец списка Alt+Tab
                # Нажимаем Alt+Tab ровно столько раз, сколько окон Telegram
                pyautogui.keyDown('alt')
                time.sleep(0.15)

                for i in range(self.telegram_windows_count):
                    pyautogui.press('tab')
                    time.sleep(0.1)

                pyautogui.keyUp('alt')
                time.sleep(0.2)

                self.is_setup_phase = False
                logging.info("✅ Фаза настройки завершена. Терминал в конце списка.")
                return True

            # РАБОЧАЯ ФАЗА: циклическое переключение между ТГ окнами
            else:
                # Нажимаем Alt+Tab количество раз = количеству Telegram окон
                pyautogui.keyDown('alt')
                time.sleep(0.15)

                for _ in range(self.telegram_windows_count):
                    pyautogui.press('tab')
                    time.sleep(0.08)

                pyautogui.keyUp('alt')
                time.sleep(0.3)

                logging.debug(f"➡️ Переключение на следующее окно (из {self.telegram_windows_count})")
                return True

        except Exception as e:
            logging.error(f"❌ Ошибка при переключении окна: {e}")
            return False

    def _count_telegram_windows(self):
        """
        Подсчитывает количество открытых окон Telegram.
        Поддержка Windows, Linux, macOS.
        """
        try:
            if sys.platform == 'win32':
                import win32gui

                telegram_count = 0

                def enum_window_callback(hwnd, extra):
                    nonlocal telegram_count
                    try:
                        if win32gui.IsWindowVisible(hwnd):
                            window_title = win32gui.GetWindowText(hwnd)
                            # Ищем окна с "Telegram" в названии
                            if 'Telegram' in window_title:
                                telegram_count += 1
                                logging.debug(f"🔍 Найдено ТГ окно: {window_title}")
                    except:
                        pass
                    return True

                win32gui.EnumWindows(enum_window_callback, None)
                return telegram_count

            elif sys.platform == 'linux':
                import subprocess
                result = subprocess.run(
                    ['wmctrl', '-l'],
                    capture_output=True,
                    text=True
                )
                return result.stdout.count('Telegram')

            else:
                logging.warning("⚠️ Автоподсчет окон не поддерживается на этой ОС")
                return 1

        except Exception as e:
            logging.error(f"❌ Ошибка при подсчете окон: {e}")
            return 1


    def alt_tab_sequence(self, tab_count: int) -> None:
        """
        Выполняет последовательность Alt+Tab указанное количество раз
        """
        if tab_count <= 0:
            return
            
        pyautogui.keyDown('alt')
        time.sleep(0.15)
        
        for _ in range(tab_count):
            pyautogui.press('tab')
            time.sleep(0.08)
        
        pyautogui.keyUp('alt')
        time.sleep(0.2)
        
        logging.debug(f"Выполнено {tab_count} переключений Alt+Tab")

    def process_window_actions(self) -> None:
        """
        Выполняет действия в текущем окне: поиск сердца и ввод /search если не найдено
        """
        # Ищем и кликаем на сердце
        if self.find_and_click_image_simple('heart_button.png', timeout=3):
            logging.info("Успешно кликнули на сердце.")
            time.sleep(random.uniform(config.MIN_RATING_INTERVAL, config.MAX_RATING_INTERVAL))
            # Перемещаем курсор в центр экрана
            screen_width, screen_height = pyautogui.size()
            pyautogui.moveTo(screen_width // 2, screen_height // 2, duration=0.2)
            # Скроллим вниз на 500 пикселей
            pyautogui.scroll(-500)
            time.sleep(0.1)
        
        else:
            logging.warning("Кнопка с сердцем не найдена. Ввожу команду /search.")
            self.type_search_command()
            time.sleep(1)
            # Перемещаем курсор в центр экрана
            screen_width, screen_height = pyautogui.size()
            pyautogui.moveTo(screen_width // 2, screen_height // 2, duration=0.2)
            # Скроллим вниз на 500 пикселей
            pyautogui.scroll(-500)
            time.sleep(0.1)

    def main_automation_loop(self) -> None:
        """Основной цикл автоматизации с новым алгоритмом переключения окон"""
        logging.info("Запуск основной программы автоматизации (новая версия)...")
        
        if not self.find_telegram_window():
            logging.error("Telegram не найден. Пожалуйста, запустите Telegram.")
            return
        logging.info(f"Нажмите '{config.STOP_KEY}' для остановки.")
        self.alt_tab_sequence(1)
        self.process_window_actions()
        for outer_tabs in range(2, self.num_windows+1):
                if not self.running:
                    break
                logging.info(f"Внешний цикл: {outer_tabs} Alt+Tab")
                self.alt_tab_sequence(outer_tabs)
                time.sleep(0.2)
                self.scroll_down()
                time.sleep(0.1)
                self.process_window_actions()

        while self.running:
            if keyboard.is_pressed(config.STOP_KEY):
                logging.info("Программа остановлена пользователем.")
                self.running = False
                break
            if self.num_windows == 1:
                if not self.running:
                        break
                self.process_window_actions()
                time.sleep(0.1)
            for inner_tabs in range(1, self.num_windows):
                    if not self.running:
                        break
                        
                    logging.info(f"Внутренний цикл: {inner_tabs} Alt+Tab")
                    self.alt_tab_sequence(inner_tabs)
                    time.sleep(0.1)
                    self.scroll_down()
                    time.sleep(0.1)
                    self.process_window_actions()
                
            
            logging.info("Завершение полного цикла, начинаем заново...")

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