import os
import time
from concurrent.futures import ProcessPoolExecutor
import matplotlib.pyplot as plt
import numpy as np

# Импортируем готовые функции из нашего main.py
from main import (
    BOUNDS,
    _worker_wrapper,
    create_batch_ranges,
    load_stations_data,
)
from data_generator import generate_data


def run_benchmark():
    csv_path = "stations.csv"
    if not os.path.exists(csv_path):
        print("Генерация тестовых данных...")
        generate_data(filename=csv_path, num_stations=50, bounds=BOUNDS)

    # Загружаем данные станций один раз заранее
    print("Загрузка данных станций в память...")
    st_lons, st_lats, st_temps = load_stations_data(csv_path)

    width = 800
    height = 400
    batch_size = 50

    # Нарезаем батчи
    batch_ranges = create_batch_ranges(height, batch_size)
    tasks = [
        (
            r_start,
            r_end,
            width,
            height,
            BOUNDS,
            st_lons,
            st_lats,
            st_temps,
            2.0,  # power
        )
        for r_start, r_end in batch_ranges
    ]

    # Формируем список процессов для теста (без дубликатов)
    cpu_max = os.cpu_count() or 4
    workers_list = sorted(list(set([1, 2, 4, 8, cpu_max])))
    times = []

    print("\n" + "=" * 65)
    print("ЗАПУСК АВТОМАТИЧЕСКОГО БЕНЧМАРКА (ЛАБОРАТОРНАЯ РАБОТА №3)")
    print(f"Сетка: {height}x{width} | Батчей: {len(tasks)} по {batch_size} строк")
    print(f"Тестируемые конфигурации воркеров: {workers_list}")
    print("=" * 65 + "\n")

    for w in workers_list:
        print(f"Тест: запуск на {w} процессах...", end="", flush=True)

        start_time = time.perf_counter()
        with ProcessPoolExecutor(max_workers=w) as executor:
            # Выполняем расчет всех батчей
            _ = list(executor.map(_worker_wrapper, tasks))

        elapsed = time.perf_counter() - start_time
        times.append(elapsed)
        print(f" Завершено за {elapsed:.3f} сек!")

    # 1. Вывод готовой таблицы для отчета
    base_time = times[0]
    print("\n" + "=" * 65)
    print("РЕЗУЛЬТАТЫ ДЛЯ ОТЧЕТА (ТАБЛИЦА)")
    print("=" * 65)
    print(
        f"{'Процессы':^12} | {'Время (сек)':^18} | {'Ускорение (Speedup)':^22}"
    )
    print("-" * 65)
    for w, t in zip(workers_list, times):
        speedup = base_time / t
        print(f"{w:^12} | {t:^18.3f} | {speedup:^20.2f}x")
    print("=" * 65)

    # 2. Построение и сохранение графика
    plt.figure(figsize=(9, 5))
    plt.plot(
        workers_list,
        times,
        marker="o",
        color="crimson",
        linewidth=2,
        markersize=6,
        label="IDW-интерполяция (WGS84)",
    )

    # Подписываем точные секунды над точками
    for w, t in zip(workers_list, times):
        plt.text(
            w,
            t + (max(times) * 0.02),
            f"{t:.2f} с",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    plt.title(
        "Зависимость времени интерполяции от количества процессов",
        fontsize=13,
        fontweight="bold",
    )
    plt.xlabel("Количество рабочих процессов (CPU Cores)", fontsize=11)
    plt.ylabel("Время выполнения (секунды)", fontsize=11)
    plt.xticks(workers_list)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)

    output_plot = "lab3_benchmark_graph.png"
    plt.savefig(output_plot, dpi=300, bbox_inches="tight")
    print(f"\nГрафик успешно сохранен в файл: {output_plot}")
    plt.show()


if __name__ == "__main__":
    run_benchmark()