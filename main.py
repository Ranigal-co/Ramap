import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import requests

"""
    установите библиотеки

    Запустите main.py
    
    нажимайте/зажимайте кнопки + -
    нажимайте кнопки вверх, вниз, влево, вправо
"""


class MapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yandex Maps Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.apikey_static_map = "cd4da668-3cdc-44f9-8bf1-e280e40b2055"

        # Параметры карты
        self.latitude = 55.757718
        self.longitude = 37.677751
        self.zoom = 0.05
        self.scale = 1.0  # Коэффициент увеличения (1.0-4.0)
        self.zoom_step = 0.01  # Шаг изменения масштаба

        # Виджет для карты
        self.map_label = QLabel(self)
        self.map_label.setAlignment(Qt.AlignCenter)
        self.load_map()

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.map_label)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_map(self):
        """Загружает карту с текущими параметрами."""
        map_dict = {
            "address": "https://static-maps.yandex.ru/v1?lang=ru_RU&",
            "coordinates": f"&ll={self.longitude},{self.latitude}",
            "zoom": f"&spn={self.zoom},{self.zoom}",
            "size": "&size=650,450",
            "scale": f"&scale={self.scale}",
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
        except Exception as e:
            print(f"Ошибка: {e}")

    def keyPressEvent(self, event):
        """Обрабатывает нажатия клавиш."""
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom = max(0.0001, self.zoom - self.zoom_step)
            self.load_map()
        elif event.key() == Qt.Key_Minus:
            self.zoom = min(50.0, self.zoom + self.zoom_step)
            self.load_map()
        elif event.key() == Qt.Key_Up:
            self.latitude += self.zoom_step
            self.load_map()
        elif event.key() == Qt.Key_Down:
            self.latitude -= self.zoom_step
            self.load_map()
        elif event.key() == Qt.Key_Left:
            self.longitude -= self.zoom_step
            self.load_map()
        elif event.key() == Qt.Key_Right:
            self.longitude += self.zoom_step
            self.load_map()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec_())