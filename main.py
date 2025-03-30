import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel,
                             QVBoxLayout, QWidget, QPushButton,
                             QLineEdit, QHBoxLayout)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QEvent
import requests
import json


"""
    установите библиотеки

    Запустите main.py

    нажимайте/зажимайте кнопки + -
    нажимайте/зажимайте кнопки вверх, вниз, влево, вправо
    Переключайте тему кнопкой на окне
    Ищите место в поиске, чтобы сбросить метку, нажмите сбросить
"""


class MapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yandex Maps Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.apikey_static_map = "cd4da668-3cdc-44f9-8bf1-e280e40b2055"
        self.apikey_geocoder = "03c33d0f-cfbf-4dd6-aeb7-993c8e001017"

        # Параметры карты
        self.latitude = 55.757718
        self.longitude = 37.677751
        self.zoom = 0.05
        self.scale = 1.0
        self.zoom_step = 0.005
        self.theme = "light"
        self.marker = None  # Координаты метки (долгота, широта)

        # Виджеты
        self.map_label = QLabel(self)
        self.map_label.setAlignment(Qt.AlignCenter)

        # Поле поиска и кнопка
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Введите адрес для поиска")
        self.search_input.returnPressed.connect(self.search_location)

        self.search_btn = QPushButton("Искать", self)
        self.search_btn.setFocusPolicy(Qt.NoFocus)
        self.search_btn.clicked.connect(self.search_location)

        self.reset_btn = QPushButton("Сбросить", self)
        self.reset_btn.setFocusPolicy(Qt.NoFocus)
        self.reset_btn.clicked.connect(self.reset_search)

        # Кнопка переключения темы
        self.theme_btn = QPushButton("Тёмная тема", self)
        self.theme_btn.setFocusPolicy(Qt.NoFocus)
        self.theme_btn.clicked.connect(self.toggle_theme)

        # Layout
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.reset_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.map_label)
        main_layout.addWidget(self.theme_btn)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Устанавливаем обработчик событий для поля ввода
        self.search_input.installEventFilter(self)
        self.setFocus()
        self.load_map()

    def eventFilter(self, obj, event):
        """Обработчик событий для возврата фокуса"""
        if event.type() == QEvent.FocusOut and obj is self.search_input:
            self.setFocus()
            return True
        return super().eventFilter(obj, event)

    def load_map(self):
        """Загружает карту с текущими параметрами."""
        map_dict = {
            "address": "https://static-maps.yandex.ru/v1?lang=ru_RU&",
            "coordinates": f"&ll={self.longitude},{self.latitude}",
            "zoom": f"&spn={self.zoom},{self.zoom}",
            "size": "&size=650,450",
            "scale": f"&scale={self.scale}",
            "theme": f"&theme={self.theme}",
            "api_key": f"&apikey={self.apikey_static_map}",
        }

        # Добавляем метку, если она есть
        if self.marker:
            map_dict["marker"] = f"&pt={self.marker[0]},{self.marker[1]},pm2rdl"  # Красная метка

        map_url = "".join(map_dict.values())

        try:
            response = requests.get(map_url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.map_label.setPixmap(pixmap)
                self.setFocus()  # Возвращаем фокус после загрузки карты
            else:
                print(f"Ошибка: {response.status_code}")
        except Exception as e:
            print(f"Ошибка: {e}")

    def search_location(self):
        """Ищет объект по введённому адресу."""
        query = self.search_input.text().strip()
        if not query:
            return

        try:
            # Запрос к геокодеру
            geocoder_url = (
                f"https://geocode-maps.yandex.ru/1.x/?format=json&apikey={self.apikey_geocoder}"
                f"&geocode={query}"
            )
            response = requests.get(geocoder_url)

            if response.status_code == 200:
                data = json.loads(response.text)
                # Получаем координаты первого результата
                pos = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["Point"]["pos"]
                self.longitude, self.latitude = map(float, pos.split())
                self.marker = (self.longitude, self.latitude)  # Устанавливаем метку
                self.zoom = 0.005  # Увеличиваем масштаб для найденного объекта
                self.load_map()
            else:
                print(f"Ошибка геокодера: {response.status_code}")
        except Exception as e:
            print(f"Ошибка при поиске: {e}")

    def reset_search(self):
        """Сбрасывает результаты поиска."""
        self.marker = None
        self.load_map()

    def toggle_theme(self):
        """Переключает тему между light и dark."""
        self.theme = "dark" if self.theme == "light" else "light"
        self.theme_btn.setText("Светлая тема" if self.theme == "dark" else "Тёмная тема")
        self.load_map()

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