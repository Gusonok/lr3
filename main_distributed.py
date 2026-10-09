import argparse
import csv
import os
import pickle
import socket
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import asyncio

import numpy as np
import rasterio
from rasterio.transform import from_origin
import requests
from fastapi import FastAPI, Request, Response
import uvicorn

from data_generator import generate_data
from interpolation_core import interpolate_batch

BOUNDS = {"west": 32.4, "east": 36.6, "south": 44.3, "north": 46.2}

#             ВОРКЕР (ВЫЧИСЛИТЕЛЬНЫЙ УЗЕЛ НА ВСЕ ЯДРА)
worker_app = FastAPI()

@worker_app.get("/")
def health():
    return {"status": "worker ready"}

def _worker_multiprocess_solve(r_start, r_end, width, height, bounds, st_lons, st_lats, st_temps, power, batch_size=50):
    """Считает большой диапазон строк, параллеля его по ВСЕМ ядрам этого ПК!"""
    # Разбиваем диапазон строк на батчи
    ranges = []
    for s in range(r_start, r_end, batch_size):
        e = min(s + batch_size, r_end)
        ranges.append((s, e))
    # Создаем список задач для каждого батча
    tasks = [
        (s, e, width, height, bounds, st_lons, st_lats, st_temps, power)
        for s, e in ranges
    ]
    # Создаем массивы для хранения результатов
    h_sub = r_end - r_start
    sub_min = np.empty((h_sub, width), dtype=np.float32)
    sub_max = np.empty((h_sub, width), dtype=np.float32)
    sub_mean = np.empty((h_sub, width), dtype=np.float32)

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
        for s, e, b_min, b_max, b_mean in pool.map(_worker_subtask, tasks):
            offset_s = s - r_start
            offset_e = e - r_start
            sub_min[offset_s:offset_e, :] = b_min
            sub_max[offset_s:offset_e, :] = b_max
            sub_mean[offset_s:offset_e, :] = b_mean

    return r_start, r_end, sub_min, sub_max, sub_mean

def _worker_subtask(args):
    return interpolate_batch(*args)

@worker_app.post("/compute_batch")
async def compute_batch_api(request: Request):
    """Принимает один батч строк и возвращает посчитанный результат."""
    body = await request.body()
    task = pickle.loads(body)
    result = interpolate_batch(
        row_start=task["row_start"],
        row_end=task["row_end"],
        width=task["width"],
        height=task["height"],
        bounds=task["bounds"],
        station_lons=task["station_lons"],
        station_lats=task["station_lats"],
        station_temps=task["station_temps"],
        power=task.get("power", 2.0),
    )
    return Response(
        content=pickle.dumps(result), media_type="application/octet-stream"
    )

@worker_app.post("/compute_half")
async def compute_half_api(request: Request):
    """Принимает половину карты и считает её на ВСЕХ ядрах ПК!"""
    # 1. Читаем байты по сети
    body = await request.body()
    p = pickle.loads(body)

    print(
        f"--> [ПК-ВОРКЕР] Приняты строки {p['row_start']}–{p['row_end']}! Врубаю ВСЕ ядра ({os.cpu_count()} шт)..."
    )
    t0 = time.perf_counter()

    # 2. Запускаем тяжелый расчет на ядрах ПК в отдельном потоке
    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(
        None,
        _worker_multiprocess_solve,
        p["row_start"],
        p["row_end"],
        p["width"],
        p["height"],
        p["bounds"],
        p["station_lons"],
        p["station_lats"],
        p["station_temps"],
        p.get("power", 2.0),
        50,
    )

    calc_time = time.perf_counter() - t0
    print(
        f"<-- [ПК-ВОРКЕР] Вычисления завершены за {calc_time:.3f} с! Отправляю ответ назад."
    )

    return Response(
        content=pickle.dumps(res), media_type="application/octet-stream"
    )

def start_worker_service(port=8000):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    print("=" * 60)
    print("ВЫЧИСЛИТЕЛЬНЫЙ УЗЕЛ (ВОРКЕР) ЗАПУЩЕН")
    print(f"Ваш локальный IP: {local_ip}")
    print(f"Адрес для подключения: http://{local_ip}:{port}")
    print(f"Доступно ядер на этом ПК: {os.cpu_count()}")
    print("=" * 60)
    uvicorn.run(worker_app, host="0.0.0.0", port=port, log_level="warning")


#             КООРДИНАТОР (ГЛАВНЫЙ ПК)
def load_stations_data(csv_path):
    station_coords = {}
    station_daily_temp = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            st = row["station"]
            if st not in station_coords:
                station_coords[st] = (float(row["latitude"]), float(row["longitude"]))
                station_daily_temp[st] = {}
            day = int(row["day"])
            station_daily_temp[st][day] = float(row["temperature"])

    st_list = sorted(list(station_coords.keys()))
    lats = np.array([station_coords[s][0] for s in st_list], dtype=np.float64)
    lons = np.array([station_coords[s][1] for s in st_list], dtype=np.float64)
    temps = np.zeros((len(st_list), 365), dtype=np.float32)
    for i, s in enumerate(st_list):
        for d in range(1, 366):
            temps[i, d - 1] = station_daily_temp[s][d]
    return lons, lats, temps

def save_as_geotiff(filename, raster_data, bounds, width, height):
    px = (bounds["east"] - bounds["west"]) / width
    py = (bounds["north"] - bounds["south"]) / height
    transform = from_origin(bounds["west"], bounds["north"], px, py)
    profile = {
        "driver": "GTiff", "height": height, "width": width, "count": 1,
        "dtype": raster_data.dtype, "crs": "EPSG:4326", "transform": transform, "compress": "lzw"
    }
    with rasterio.open(filename, "w", **profile) as dst:
        dst.write(raster_data, 1)

def run_remote_post(payload, worker_url):
    """Шлёт половину карты на второй ПК одним запросом."""
    url = f"{worker_url.rstrip('/')}/compute_half"
    resp = requests.post(url, data=pickle.dumps(payload), timeout=120)
    return pickle.loads(resp.content)

def _exec_local_task(task_dict):
    """Вычисление одного батча на локальном процессоре."""
    return interpolate_batch(
        row_start=task_dict["row_start"],
        row_end=task_dict["row_end"],
        width=task_dict["width"],
        height=task_dict["height"],
        bounds=task_dict["bounds"],
        station_lons=task_dict["station_lons"],
        station_lats=task_dict["station_lats"],
        station_temps=task_dict["station_temps"],
        power=task_dict.get("power", 2.0),
    )

def _exec_remote_task(task_dict, worker_url):
    """Отправка одного батча по сети на второй компьютер."""
    url = f"{worker_url.rstrip('/')}/compute_batch"
    resp = requests.post(url, data=pickle.dumps(task_dict), timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Ошибка удаленного воркера: {resp.text}")
    return pickle.loads(resp.content)

def run_coordinator(mode="single", worker_url=None, width=800, height=400):
    print("=" * 60)
    if mode == "single":
        print(f"РЕЖИМ: Одиночный расчет на 1 ПК ({os.cpu_count()} ядер)")
    else:
        print(f"РЕЖИМ: НАСТОЯЩИЙ ДВУХУЗЛОВОЙ КЛАСТЕР!")
        print(f"Этот ПК ({os.cpu_count()} ядер) + Удаленный узел ({worker_url})")
    print(f"Сетка: {height}x{width}")
    print("=" * 60)

    csv_path = "stations.csv"
    if not os.path.exists(csv_path):
        generate_data(filename=csv_path, num_stations=50, bounds=BOUNDS)
    st_lons, st_lats, st_temps = load_stations_data(csv_path)

    final_min = np.empty((height, width), dtype=np.float32)
    final_max = np.empty((height, width), dtype=np.float32)
    final_mean = np.empty((height, width), dtype=np.float32)

    start_time = time.perf_counter()

    if mode == "single":
        # Считаем всё на этом ПК
        _, _, b_min, b_max, b_mean = _worker_multiprocess_solve(
            0, height, width, height, BOUNDS, st_lons, st_lats, st_temps, 2.0
        )
        final_min[:] = b_min
        final_max[:] = b_max
        final_mean[:] = b_mean

    else:
        mid = height // 2
        print(f"Делим задачу пополам:")
        print(f"  • Ноутбук считает строки с 0 по {mid} на всех своих ядрах")
        print(f"  • ПК считает строки с {mid} по {height} на всех своих ядрах")

        remote_payload = {
            "row_start": mid, "row_end": height, "width": width, "height": height,
            "bounds": BOUNDS, "station_lons": st_lons, "station_lats": st_lats,
            "station_temps": st_temps, "power": 2.0
        }

        # ЗАПУСКАЕМ ОДНОВРЕМЕННО: Ноут на локальных процессах, ПК через сетевой поток!
        with ThreadPoolExecutor(max_workers=2) as net_thread:
            # 1. Отправляем в фоне задачу на второй ПК
            remote_future = net_thread.submit(run_remote_post, remote_payload, worker_url)

            # 2. Сами не ждём, а сразу считаем свою половину на всех своих ядрах!
            print("Ноутбук начал параллельные вычисления...")
            _, _, local_min, local_max, local_mean = _worker_multiprocess_solve(
                0, mid, width, height, BOUNDS, st_lons, st_lats, st_temps, 2.0
            )
            print("Ноутбук закончил свою половину!")

            # 3. Забираем готовую половину со второго ПК
            _, _, rem_min, rem_max, rem_mean = remote_future.result()
            print("Ответ от второго ПК получен!")

        # Склеиваем две половины карты
        final_min[0:mid, :] = local_min
        final_min[mid:height, :] = rem_min

        final_max[0:mid, :] = local_max
        final_max[mid:height, :] = rem_max

        final_mean[0:mid, :] = local_mean
        final_mean[mid:height, :] = rem_mean

    total_time = time.perf_counter() - start_time
    print(f"\nПОЛНЫЙ РАСЧЕТ ЗАВЕРШЕН ЗА: {total_time:.3f} СЕКУНД!")

    prefix = "crimea_cluster" if mode == "distributed" else "crimea_single"
    save_as_geotiff(f"{prefix}_mean.tif", final_mean, BOUNDS, width, height)
    print(f"Итоговая карта сохранена: {prefix}_mean.tif")


if __name__ == "__main__":
    print("=" * 60)
    print("1 - Одиночный режим (только этот ПК)")
    print("2 - Сервер / Координатор (делят пополам со вторым ПК)")
    print("3 - Клиент / Воркер (вычислительный узел на все свои ядра)")
    print("=" * 60)
    choice = input("Выберите режим (1, 2, 3): ").strip()

    if choice == "1":
        run_coordinator(mode="single")
    elif choice == "2":
        url = input("Введите адрес Воркера (http://192.168.0.209:8000): ").strip()
        if not url:
            url = "http://192.168.0.209:8000"
        elif not url.startswith("http"):
            url = f"http://{url}"
        run_coordinator(mode="distributed", worker_url=url)
    elif choice == "3":
        start_worker_service(port=8000)