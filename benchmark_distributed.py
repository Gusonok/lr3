import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import numpy as np

# Импортируем готовые функции из main_distributed.py
from main_distributed import (
    BOUNDS,
    _exec_local_task,
    _exec_remote_task,
    load_stations_data,
    generate_data
)


def run_single_test(tasks):
    """Тест: расчет ТОЛЬКО на 1 ПК (все ядра локально)."""
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        _ = list(executor.map(_exec_local_task, tasks))
    return time.perf_counter() - t0


def run_cluster_test(tasks, worker_url):
    """Тест: расчет на 2 ПК (50% локально + 50% по сети)."""
    split_idx = len(tasks) // 2
    tasks_local = tasks[:split_idx]
    tasks_remote = tasks[split_idx:]

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as local_pool, \
         ThreadPoolExecutor(max_workers=4) as net_pool:

        futures = []
        for t in tasks_local:
            futures.append(local_pool.submit(_exec_local_task, t))
        for t in tasks_remote:
            futures.append(net_pool.submit(_exec_remote_task, t, worker_url))

        for f in as_completed(futures):
            _ = f.result()

    return time.perf_counter() - t0


def main():
    print("=" * 65)
    print("БЕНЧМАРК: СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ 1 ПК vs 2 ПК (КЛАСТЕР)")
    print("=" * 65)

    worker_ip = input("Введите адрес Воркера (например, http://192.168.1.45:8000): ").strip()
    if not worker_ip.startswith("http"):
        worker_ip = f"http://{worker_ip}"

    csv_path = "stations.csv"
    if not os.path.exists(csv_path):
        generate_data(filename=csv_path, num_stations=50, bounds=BOUNDS)
    st_lons, st_lats, st_temps = load_stations_data(csv_path)

    # Тестируем рабочую сетку 400x800
    resolutions = [
        {"name": "Сетка 400x800", "h": 400, "w": 800, "batch": 50}
    ]

    single_times = []
    cluster_times = []
    labels = []

    for res in resolutions:
        h, w, b_size = res["h"], res["w"], res["batch"]
        labels.append(res["name"])

        # Формируем задачи
        tasks = []
        for start in range(0, h, b_size):
            end = min(start + b_size, h)
            tasks.append({
                "row_start": start, "row_end": end,
                "width": w, "height": h, "bounds": BOUNDS,
                "station_lons": st_lons, "station_lats": st_lats,
                "station_temps": st_temps, "power": 2.0
            })

        print(f"\n---> Тестирование: {res['name']} ({len(tasks)} батчей)...")

        # 1. Замер на 1 ПК
        print("  [1/2] Запуск на 1 ПК (локально)...", end="", flush=True)
        t_single = run_single_test(tasks)
        single_times.append(t_single)
        print(f" {t_single:.3f} с")

        # 2. Замер на кластере из 2 ПК
        print("  [2/2] Запуск на 2 ПК (Wi-Fi кластер)...", end="", flush=True)
        t_cluster = run_cluster_test(tasks, worker_ip)
        cluster_times.append(t_cluster)
        print(f" {t_cluster:.3f} с")

    # =====================================================================
    #                  ТАБЛИЦА РЕЗУЛЬТАТОВ ДЛЯ ОТЧЕТА
    # =====================================================================
    print("\n" + "=" * 70)
    print("ИТОГОВАЯ ТАБЛИЦА СРАВНЕНИЯ")
    print("=" * 70)
    print(f"{'Разрешение':^18} | {'1 ПК (сек)':^14} | {'2 ПК Кластер (сек)':^18} | {'Ускорение':^12}")
    print("-" * 70)
    for name, t_s, t_c in zip(labels, single_times, cluster_times):
        speedup = t_s / t_c
        print(f"{name:^18} | {t_s:^14.3f} | {t_c:^18.3f} | {speedup:^10.2f}x")
    print("=" * 70)

    # =====================================================================
    #             ПОСТРОЕНИЕ СРАВНИТЕЛЬНОГО ГРАФИКА (BAR CHART)
    # =====================================================================
    x = np.arange(len(labels))
    bar_width = 0.35

    plt.figure(figsize=(9, 5))
    bars1 = plt.bar(x - bar_width/2, single_times, bar_width, label='1 ПК (локально)', color='crimson')
    bars2 = plt.bar(x + bar_width/2, cluster_times, bar_width, label='2 ПК (кластер по Wi-Fi)', color='royalblue')

    # Добавляем подписи со временем и процентом ускорения
    for i, (b1, b2) in enumerate(zip(bars1, bars2)):
        h1 = b1.get_height()
        h2 = b2.get_height()
        speedup = h1 / h2

        plt.text(b1.get_x() + b1.get_width()/2, h1 + 0.1, f"{h1:.2f} с", ha='center', va='bottom', fontsize=9, fontweight='bold')
        plt.text(b2.get_x() + b2.get_width()/2, h2 + 0.1, f"{h2:.2f} с\n({speedup:.2f}x)", ha='center', va='bottom', fontsize=9, fontweight='bold', color='darkblue')

    plt.title('Сравнение производительности: 1 ПК vs Распределенный кластер (2 ПК)', fontsize=12, fontweight='bold')
    plt.ylabel('Время расчета (секунды)', fontsize=11)
    plt.xticks(x, labels, fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.legend(fontsize=11)

    output_fig = "cluster_vs_single_comparison.png"
    plt.savefig(output_fig, dpi=300, bbox_inches='tight')
    print(f"\nГрафик успешно сохранен в файл: {output_fig}")
    plt.show()


if __name__ == "__main__":
    main()