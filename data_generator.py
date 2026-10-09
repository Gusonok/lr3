import random
import csv

def generate_data(filename="stations.csv", num_stations=50, bounds=None):
    if bounds is None:
        bounds = {"west": 32.4, "east": 36.6, "south": 44.3, "north": 46.2}

    latitude = [bounds["south"], bounds["north"]]
    longitude = [bounds["west"], bounds["east"]]
    # генерируем список станций с координатами в пределах указанных границ
    stations = {}

    for i in range(num_stations):
        latitude_val = random.uniform(latitude[0], latitude[1]) #случайное число в пределах от южной до северной границы
        longitude_val = random.uniform(longitude[0], longitude[1]) #случайное число в пределах от западной до восточной границы
        stations[f"station_{i}"] = {"latitude": latitude_val, "longitude": longitude_val} # добавление в словарь станций с ключом station_i и значением словаря с координатами

    # для каждой станции для каждого дня получаем случайную температуру в пределах от -50 до 50 градусов
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["station", "latitude", "longitude", "day", "temperature"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for station, coords in stations.items():
            for day in range(1, 366):
                temperature = random.uniform(-50, 50)
                writer.writerow({
                    "station": station,
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "day": day,
                    "temperature": temperature
                })
if __name__ == "__main__":
    generate_data()