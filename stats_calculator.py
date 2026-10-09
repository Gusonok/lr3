import csv
import numpy as np


def calculate_csv_summary(csv_path):
    """
    Предварительный статистический анализ данных из CSV (по методичке, стр. 3).
    Читает файл построчно без внешних библиотек (минимальное потребление RAM).
    Возвращает: min_val, max_val, mean_val
    """
    min_val = float('inf')
    max_val = float('-inf')
    total_sum = 0.0
    count = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = float(row['temperature'])
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val
            total_sum += val
            count += 1

    mean_val = total_sum / count if count > 0 else 0.0
    return min_val, max_val, mean_val


def compute_batch_stats(batch_temps, batch_height, width):
    """
    Вход: batch_temps формы (num_pixels, 365)
    Выход: b_min, b_max, b_mean размером (batch_height, width)
    """
    # Схлопываем 365 дней (axis=1) для каждого пикселя
    b_min = np.nanmin(batch_temps, axis=1).reshape(batch_height, width)
    b_max = np.nanmax(batch_temps, axis=1).reshape(batch_height, width)
    b_mean = np.nanmean(batch_temps, axis=1).reshape(batch_height, width)

    return (
        b_min.astype(np.float32),
        b_max.astype(np.float32),
        b_mean.astype(np.float32)
    )