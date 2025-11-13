"""
Конфигурационный файл для автоматаизации бота
"""

# Настройки временных интервалов (в секундах)
MIN_RATING_INTERVAL = 0.3
MAX_RATING_INTERVAL = 1.1

# Настройки оценки
HIGH_RATING_MIN = 6
HIGH_RATING_MAX = 10
LOW_RATING_MIN = 1
LOW_RATING_MAX = 5
HIGH_RATING_PROBABILITY = 0.8  # 80% вероятность высокой оценки

# Настройки распознавания изображений
IMAGE_CONFIDENCE = 0.9
SEARCH_TIMEOUT = 10

# Настройки печати
MIN_CHAR_DELAY = 0.05
MAX_CHAR_DELAY = 0.15



# Настройки логирования
LOG_LEVEL = "INFO"
LOG_FILE = "bot_automator.log"

# Горячие клавиши
STOP_KEY = 'q'

# Настройки экрана
SCREENSHOT_QUALITY = 95

# Настройки для простого поиска изображений (без OpenCV)
PIXEL_TOLERANCE = 30 # Допустимое отклонение в цвете пикселя (сумма разниц по RGB). Чем выше, тем менее точный поиск.