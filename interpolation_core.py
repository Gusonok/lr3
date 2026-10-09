import numpy as np
import pyproj
from stats_calculator import compute_batch_stats

# Инициализируем объект геодезических расчетов по эллипсоиду WGS84
geod = pyproj.Geod(ellps="WGS84")


def interpolate_batch(
    row_start,
    row_end,
    width,
    height,
    bounds,
    station_lons,
    station_lats,
    station_temps,
    power=2
):
    """
    Обрабатывает один батч строк растра:
    1. Строит сетку координат для строк от row_start до row_end.
    2. Считает расстояния в метрах через pyproj до всех станций.
    3. Считает веса IDW и интерполирует температуру на 365 дней.
    4. Сразу сворачивает временную шкалу в статистику: Min, Max, Mean.
    """
    # 1. Шаг сетки по координатам (широта/долгота) одного пикселя в градусах 
    d_lon = (bounds["east"] - bounds["west"]) / width
    d_lat = (bounds["north"] - bounds["south"]) / height

    # Координаты столбцов (все) и строк (только наш батч)
    cols = np.arange(width)
    rows = np.arange(row_start, row_end)
    batch_height = len(rows)

    # 2. Вычисляем координаты пикселей текущего батча
    lons = bounds["west"] + (cols + 0.5) * d_lon
    lats = bounds["north"] - (rows + 0.5) * d_lat

    grid_lons, grid_lats = np.meshgrid(lons, lats) # в каждой точке сетки (широта, долгота) пикселя

    # Вытягиваем сетку в плоские массивы точек
    target_lons = grid_lons.ravel()
    target_lats = grid_lats.ravel()
    num_targets = len(target_lons) # сколько пикселей в батче (batch_height * width)
    num_stations = len(station_lons)

    # 3. Векторный расчет расстояний через pyproj
    # комбинируем все пиксели с каждой станцией, чтобы получить массив расстояний
    all_targets_lon = np.repeat(target_lons, num_stations)
    all_targets_lat = np.repeat(target_lats, num_stations)
    all_stations_lon = np.tile(station_lons, num_targets)
    all_stations_lat = np.tile(station_lats, num_targets)

    _, _, distances = geod.inv(
        all_targets_lon,
        all_targets_lat,
        all_stations_lon,
        all_stations_lat
    )

    # Превращаем расстояния в матрицу (кол-во пикселей, кол-во станций)
    dist_matrix = distances.reshape(num_targets, num_stations)

    # 4. Вычисление весов IDW
    weights = 1.0 / (dist_matrix**power + 1e-12) # Добавляем маленькое число, чтобы избежать деления на ноль

    # Нормализуем веса (чтобы сумма весов для каждого пикселя была равна 1)
    sum_weights = np.sum(weights, axis=1, keepdims=True)
    norm_weights = weights / sum_weights

    # 5. Интерполяция температур на 365 дней через матричное умножение
    # station_temps имеет форму (50, 365)
    # batch_temps получит форму (num_targets, 365)
    # @ матричное умножение
    batch_temps = norm_weights @ station_temps

    # 6. Оптимизация памяти (сразу считаем статистику за год по строкам)
    # Используем nan-безопасные функции по рекомендации методички
    b_min, b_max, b_mean = compute_batch_stats(batch_temps, batch_height, width)

    # Возвращаем диапазон строк и посчитанные пласты статистики для этого куска
    return row_start, row_end, b_min, b_max, b_mean
