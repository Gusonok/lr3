import argparse
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import rasterio
from rasterio.transform import from_origin

# Импортируем функцию расчета одного батча из нашего файла
from interpolation_core import interpolate_batch
from stats_calculator import calculate_csv_summary


# Границы Крыма (WGS84)
BOUNDS = {"west": 32.4, "east": 36.6, "south": 44.3, "north": 46.2}


def parse_arguments():
    """Настройка интерфейса командной строки (CLI)."""
    parser = argparse.ArgumentParser(
        description="Высокопроизводительная IDW-интерполяция температуры воздуха (Крым)"
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default="stations.csv",
        help="Путь к входному CSV-файлу с данными станций"
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="crimea_temp",
        help="Префикс для сохранения итоговых файлов GeoTIFF"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count(),
        help="Количество параллельных процессов (по умолчанию все доступные ядра)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Ширина итогового растра в пикселях"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=400,
        help="Высота итогового растра в пикселях"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Размер батча (количество строк растра на одну задачу)"
    )
    parser.add_argument(
        "--power",
        type=float,
        default=2.0,
        help="Степень затухания расстояния в формуле IDW"
    )
    return parser.parse_args()


def load_stations_data(csv_path):
    """
    Считывает CSV и преобразует его в массивы NumPy:
    - station_lons: долготы станций (длина K)
    - station_lats: широты станций (длина K)
    - station_temps: матрица температур размером (K, 365)
    """
    station_coords = {}   # station_name -> (lat, lon)
    station_daily_temp = {}  # station_name -> [temp_day_1, temp_day_2, ...]

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            st = row["station"]
            if st not in station_coords:
                station_coords[st] = (float(row["latitude"]), float(row["longitude"]))
                station_daily_temp[st] = {}
            
            day = int(row["day"])
            station_daily_temp[st][day] = float(row["temperature"])

    # Сортируем названия станций для строгого порядка строк
    stations_list = sorted(list(station_coords.keys()))
    num_stations = len(stations_list)

    station_lats = np.array([station_coords[st][0] for st in stations_list], dtype=np.float64)
    station_lons = np.array([station_coords[st][1] for st in stations_list], dtype=np.float64)

    # Заполняем матрицу температур (число станций x 365 дней)
    station_temps = np.zeros((num_stations, 365), dtype=np.float32)
    for i, st in enumerate(stations_list):
        for day in range(1, 366):
            station_temps[i, day - 1] = station_daily_temp[st][day]

    return station_lons, station_lats, station_temps


def create_batch_ranges(total_height, batch_size):
    """
    Разбивает высоту матрицы на интервалы (row_start, row_end).
    Например: [(0, 50), (50, 100), ..., (350, 400)]
    """
    ranges = []
    for start in range(0, total_height, batch_size):
        end = min(start + batch_size, total_height)
        ranges.append((start, end))
    return ranges


def _worker_wrapper(args_tuple):
    """Вспомогательная функция для безопасного запуска в ProcessPoolExecutor на Windows."""
    return interpolate_batch(*args_tuple)


def save_as_geotiff(filename, raster_data, bounds, width, height):
    """Сохраняет 2D-матрицу в файл GeoTIFF с географической привязкой и сжатием."""
    # Размер одного пикселя в градусах
    pixel_size_x = (bounds["east"] - bounds["west"]) / width
    pixel_size_y = (bounds["north"] - bounds["south"]) / height

    # Геодезическая привязка (северо-западный угол и размеры пикселя)
    transform = from_origin(
        bounds["west"],
        bounds["north"],
        pixel_size_x,
        pixel_size_y
    )

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": raster_data.dtype,
        "crs": "EPSG:4326",  # Система координат WGS84 (градусы широты и долготы)
        "transform": transform,
        "compress": "lzw"     # Сжатие без потерь по методичке
    }

    with rasterio.open(filename, "w", **profile) as dst:
        dst.write(raster_data, 1)


if __name__ == "__main__":
    args = parse_arguments()

    print("=" * 60)
    print("ВЫСОКОПРОИЗВОДИТЕЛЬНАЯ ГЕОПРОСТРАНСТВЕННАЯ ИНТЕРПОЛЯЦИЯ")
    print(f"Регион: Крым {BOUNDS}")
    print(f"Сетка: {args.height} строк x {args.width} столбцов")
    print(f"Процессов: {args.workers} | Размер батча: {args.batch_size} строк")
    print("=" * 60)

    # 1. Проверяем наличие CSV-файла, если нет — генерируем на лету
    if not os.path.exists(args.csv_path):
        print(f"Файл {args.csv_path} не найден! Генерируем тестовые данные...")
        from data_generator import generate_data
        generate_data(filename=args.csv_path, num_stations=50, bounds=BOUNDS)

    # 2. Загружаем данные станций
    print("Чтение данных станций из CSV...")
    st_lons, st_lats, st_temps = load_stations_data(args.csv_path)
    print(f"Загружено станций: {len(st_lons)}, временной ряд: {st_temps.shape[1]} дней.")

    csv_min, csv_max, csv_mean = calculate_csv_summary(args.csv_path)
    print(f"Статистика сырых данных станций:")
    print(f"  • Мин. темп.: {csv_min:.1f} °C")
    print(f"  • Макс. темп.: {csv_max:.1f} °C")
    print(f"  • Средняя:     {csv_mean:.1f} °C")

    # 3. Нарезаем строки на батчи
    batch_ranges = create_batch_ranges(args.height, args.batch_size)
    print(f"Всего подготовлено батчей: {len(batch_ranges)}")

    # Подготавливаем кортежи аргументов для каждого рабочего процесса
    tasks = [
        (
            r_start,
            r_end,
            args.width,
            args.height,
            BOUNDS,
            st_lons,
            st_lats,
            st_temps,
            args.power
        )
        for r_start, r_end in batch_ranges
    ]

    # 4. Выделяем пустые 2D-матрицы под итоговую карту
    final_min = np.empty((args.height, args.width), dtype=np.float32)
    final_max = np.empty((args.height, args.width), dtype=np.float32)
    final_mean = np.empty((args.height, args.width), dtype=np.float32)

    # 5. Параллельный расчет (Пул процессов)
    print("\nЗапуск параллельных вычислений...")
    start_time = time.perf_counter()

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        results = executor.map(_worker_wrapper, tasks)

        # Собираем готовые полосы и вставляем их на свои места в общую карту
        for r_start, r_end, b_min, b_max, b_mean in results:
            final_min[r_start:r_end, :] = b_min
            final_max[r_start:r_end, :] = b_max
            final_mean[r_start:r_end, :] = b_mean

    total_time = time.perf_counter() - start_time
    print(f"Интерполяция успешно завершена за: {total_time:.3f} сек!")

    # 6. Сохранение трех карт статистики в GeoTIFF
    print("\nСохранение результатов в GeoTIFF...")
    save_as_geotiff(f"{args.output_prefix}_min.tif", final_min, BOUNDS, args.width, args.height)
    save_as_geotiff(f"{args.output_prefix}_max.tif", final_max, BOUNDS, args.width, args.height)
    save_as_geotiff(f"{args.output_prefix}_mean.tif", final_mean, BOUNDS, args.width, args.height)

    print(f"1. Минимальная годовая температура: {args.output_prefix}_min.tif")
    print(f"2. Максимальная годовая температура: {args.output_prefix}_max.tif")
    print(f"3. Среднегодовая температура:      {args.output_prefix}_mean.tif")
    print("\nГотово! Файлы можно открыть в QGIS или визуализировать через matplotlib.")