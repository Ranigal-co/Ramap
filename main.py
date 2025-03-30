import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import requests


"""
    в терминале выполните:
    pip install -r requirements.txt (установка библиотек)
    
    Запустите main.py
"""


class MapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yandex Maps Viewer")
        self.setGeometry(100, 100, 800, 600)  # Размер окна

        self.apikey_static_map = "cd4da668-3cdc-44f9-8bf1-e280e40b2055"

        # Параметры карты (координаты Москвы по умолчанию)
        self.latitude = 55.757718  # Широта
        self.longitude = 37.677751  # Долгота
        self.zoom = 0.05  # Масштаб (spn)

        # Виджет для отображения карты
        self.map_label = QLabel(self)
        self.map_label.setAlignment(Qt.AlignCenter)

        # Загружаем карту при старте
        self.load_map()

        # Основной layout
        layout = QVBoxLayout()
        layout.addWidget(self.map_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_map(self):
        """Загружает карту по текущим координатам и масштабу."""
        # Формируем URL для запроса к API
        map_dict = {
            "address": f"https://static-maps.yandex.ru/v1?lang=ru_RU&",
            "coordinates": f"&ll={self.longitude},{self.latitude}",
            "zoom": f"&spn={self.zoom},{self.zoom}",
            "size": f"&size=650,450",
            "api_key": f"&apikey={self.apikey_static_map}",
        }
        map_url = "".join(map_dict.values())

        try:
            response = requests.get(map_url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.map_label.setPixmap(pixmap)
            else:
                print(f"Ошибка: {response.status_code}")
                self.map_label.setText("Не удалось загрузить карту.")
        except Exception as e:
            print(f"Ошибка при загрузке карты: {e}")
            self.map_label.setText("Ошибка соединения.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec_())