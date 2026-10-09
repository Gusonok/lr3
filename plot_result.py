import matplotlib.pyplot as plt
import rasterio

# Открываем получившуюся карту средней температуры
with rasterio.open("crimea_temp_mean.tif") as src:
    temp_map = src.read(1)

plt.figure(figsize=(10, 5))
# Отрисовываем тепловую карту (цветовая схема 'coolwarm': синий - холод, красный - тепло)
img = plt.imshow(temp_map, cmap="coolwarm")
plt.colorbar(img, label="Среднегодовая температура, °C")
plt.title("Среднегодовая температура воздуха в Крыму (IDW-интерполяция)", fontsize=12)
plt.xlabel("X (пиксели)")
plt.ylabel("Y (пиксели)")

plt.savefig("crimea_map_mean.png", dpi=300)
plt.show()