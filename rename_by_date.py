# запуск через команду "python3 rename_by_date.py" в терминале

import os
from datetime import datetime
import exifread
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

# Список поддерживаемых расширений файлов (в нижнем регистре)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".dng"}
VIDEO_EXTENSIONS = {".mov", ".mp4"}

# Получаем имя самого скрипта, чтобы его не переименовывать
script_name = os.path.basename(__file__)

# Обходим все файлы в текущей папке
for file_name in os.listdir("."):
    # Пропускаем папки и сам скрипт
    if not os.path.isfile(file_name) or file_name == script_name:
        continue

    # Получаем расширение файла в нижнем регистре
    _, ext = os.path.splitext(file_name)
    ext_lower = ext.lower()

    # Формируем новое имя по умолчанию (будет заполнено позже)
    new_name = None
    capture_datetime = None

    # Если файл является изображением (JPEG, PNG, HEIC, DNG и т.д.)
    if ext_lower in IMAGE_EXTENSIONS:
        with open(file_name, "rb") as f:
            tags = exifread.process_file(f, details=False)
        # Попытка получить дату съемки из тегов EXIF (DateTimeOriginal или DateTime)
        date_str = None
        for tag in ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"):
            if tag in tags:
                date_str = str(tags[tag])
                break
        if date_str:
            # EXIF формат даты: "YYYY:MM:DD HH:MM:SS"
            try:
                capture_datetime = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except Exception:
                capture_datetime = None

    # Если файл является видео (MOV, MP4 и др.)
    elif ext_lower in VIDEO_EXTENSIONS:
        parser = createParser(file_name)
        if parser:
            with parser:
                try:
                    metadata = extractMetadata(parser)
                except Exception:
                    metadata = None
        else:
            metadata = None

        if metadata:
            info = metadata.exportDictionary().get("Metadata", {})
            # Ищем поля даты в метаданных видео
            date_str = None
            # Предпочтительно взять дату создания (Creation date) из контейнера
            if "Creation date" in info:
                date_str = info["Creation date"]
            elif "Creation Date" in info:
                date_str = info["Creation Date"]
            elif "Modified date" in info:
                date_str = info["Modified date"]
            elif "Modified Date" in info:
                date_str = info["Modified Date"]
            if date_str:
                # Попытаемся распознать строку даты (обычно "YYYY-MM-DD hh:mm:ss" или похожий формат)
                try:
                    # Пытаться разные форматы времени
                    if date_str.count("-") >= 2:
                        # Формат типа "YYYY-MM-DD hh:mm:ss" или "YYYY-MM-DDTHH:MM:SS"
                        # Заменяем 'T' на ' ' если присутствует
                        date_str_clean = date_str.replace("T", " ")
                        # Обрезаем часовой пояс, если есть (+XX:XX)
                        date_str_clean = date_str_clean.split("+")[0].strip()
                        date_str_clean = date_str_clean.split("Z")[0].strip()
                        capture_datetime = datetime.strptime(date_str_clean, "%Y-%m-%d %H:%M:%S")
                    else:
                        # Формат типа "YYYY:MM:DD HH:MM:SS" (встречается реже в видео)
                        capture_datetime = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except Exception:
                    capture_datetime = None

    # Если дата съемки не получена из метаданных (capture_datetime все еще None)
    if capture_datetime is None:
        # Используем самую раннюю из доступных дат файловой системы (создание или изменение файла)
        stat = os.stat(file_name)
        if hasattr(stat, "st_birthtime"):
            # На macOS используем время создания файла (st_birthtime) и изменения (st_mtime)
            creation_ts = stat.st_birthtime
        else:
            # На Windows время создания хранится в st_ctime, на Linux реального времени создания нет
            creation_ts = getattr(stat, "st_ctime", None)
        modification_ts = stat.st_mtime
        # Берем более раннюю из известных дат
        timestamps = [ts for ts in (creation_ts, modification_ts) if ts is not None]
        if timestamps:
            earliest_ts = min(timestamps)
            capture_datetime = datetime.fromtimestamp(earliest_ts)
        else:
            # Если вообще нет данных, пропускаем файл
            print(f"Не удалось получить дату для файла {file_name}, пропуск...")
            continue

    # Формируем новое имя в требуемом формате
    formatted_date = capture_datetime.strftime("%Y.%m.%d.%H.%M.%S")
    new_name = formatted_date + ext  # используем исходное расширение файла

    # Проверяем, не совпадает ли новое имя со старым
    if new_name == file_name:
        # Уже правильно назван, пропускаем
        continue

    # Если файл с новым именем уже существует, чтобы не затереть, пропустим такой файл
    if os.path.exists(new_name):
        print(f"Файл с именем {new_name} уже существует. Пропуск переименования для {file_name}.")
        continue

    try:
        os.rename(file_name, new_name)
        print(f"Переименован: \"{file_name}\" -> \"{new_name}\"")
    except Exception as e:
        print(f"Ошибка переименования \"{file_name}\": {e}")
