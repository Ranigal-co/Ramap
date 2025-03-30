import math
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel,
                             QVBoxLayout, QWidget, QPushButton,
                             QLineEdit, QHBoxLayout, QCheckBox)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QEvent
import requests
import json


"""
    установите библиотеки

    Запустите main.py

    нажимайте/зажимайте кнопки + - (приблизить, отдалить)
    нажимайте/зажимайте кнопки вверх, вниз, влево, вправо
    Переключайте тему кнопкой на окне
    Ищите место в поиске, чтобы сбросить метку, нажмите сбросить
    Переключайте отображение почтового индекса (не у всех объектов он есть)
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
        self.marker = None
        self.current_address = ""
        self.postcode = ""  # Для хранения почтового индекса
        self.show_postcode = False  # Флаг отображения индекса

        # Виджеты
        self.map_label = QLabel(self)
        self.map_label.setAlignment(Qt.AlignCenter)
        self.map_label.setCursor(Qt.CrossCursor)  # Изменяем курсор при наведении
        self.map_label.mousePressEvent = self.map_click_handler  # Обработчик кликов

        # Поле вывода адреса
        self.address_label = QLabel("Адрес не указан", self)
        self.address_label.setStyleSheet("font-size: 14px; padding: 5px;")
        self.address_label.setAlignment(Qt.AlignCenter)

        # Чекбокс для почтового индекса
        self.postcode_check = QCheckBox("Показывать почтовый индекс", self)
        self.postcode_check.setFocusPolicy(Qt.NoFocus)
        self.postcode_check.stateChanged.connect(self.toggle_postcode)

        # Поле поиска и кнопки
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
        main_layout.addWidget(self.postcode_check)  # Добавляем чекбокс
        main_layout.addWidget(self.address_label)
        main_layout.addWidget(self.map_label)
        main_layout.addWidget(self.theme_btn)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.search_input.installEventFilter(self)
        self.setFocus()
        self.load_map()

    def map_click_handler(self, event):
        """Преобразует координаты клика в географические с учетом текущего вида карты"""
        if event.button() == Qt.LeftButton:
            # Размеры изображения карты (как в API запросе)
            img_width, img_height = 650, 450

            # Координаты клика относительно изображения (не виджета!)
            click_x = event.pos().x() - (self.map_label.width() - img_width) // 2
            click_y = event.pos().y() - (self.map_label.height() - img_height) // 2

            # Проверяем, что клик внутри изображения карты
            if not (0 <= click_x < img_width and 0 <= click_y < img_height):
                return

            # Получаем границы текущего отображаемого участка карты
            left, top = self._get_map_bounds()
            right = left + 2 * self.zoom * (img_width / img_height)
            bottom = top - 2 * self.zoom

            # Линейное преобразование координат
            lon = left + (click_x / img_width) * (right - left)
            lat = top - (click_y / img_height) * (top - bottom)
            # Небольшая поправка для широты

            # Ищем объект по координатам
            self.search_by_coordinates(lon, lat)

    def _get_map_bounds(self):
        """Возвращает координаты левого верхнего угла текущего вида карты"""
        # Соотношение сторон карты
        aspect_ratio = 650 / 450

        # Рассчитываем границы
        left = self.longitude - self.zoom * aspect_ratio
        top = self.latitude + self.zoom
        return left, top

    def search_by_coordinates(self, lon, lat):
        """Ищет объект по координатам и обновляет интерфейс"""
        # Сбрасываем предыдущие результаты
        self.reset_search()

        try:
            # Формируем запрос к геокодеру
            geocoder_url = (
                f"https://geocode-maps.yandex.ru/1.x/?format=json&apikey={self.apikey_geocoder}"
                f"&geocode={lon},{lat}"
            )
            response = requests.get(geocoder_url)

            if response.status_code == 200:
                data = json.loads(response.text)
                feature_member = data["response"]["GeoObjectCollection"]["featureMember"]

                if not feature_member:
                    self.address_label.setText("Ничего не найдено по этим координатам")
                    return

                geo_object = feature_member[0]["GeoObject"]
                pos = geo_object["Point"]["pos"]
                found_lon, found_lat = map(float, pos.split())

                # Устанавливаем метку (но не меняем центр карты)
                self.marker = (found_lon, found_lat)

                # Получаем адрес и почтовый индекс
                meta_data = geo_object["metaDataProperty"]["GeocoderMetaData"]
                self.current_address = meta_data["text"]
                self.postcode = ""
                if "Address" in meta_data and "postal_code" in meta_data["Address"]:
                    self.postcode = meta_data["Address"]["postal_code"]

                self.update_address_display()
                self.load_map()  # Перезагружаем карту с новой меткой

            else:
                self.address_label.setText("Ошибка при поиске по координатам")
                print(f"Ошибка геокодера: {response.status_code}")
        except Exception as e:
            self.address_label.setText("Ошибка соединения")
            print(f"Ошибка при поиске по координатам: {e}")

    def toggle_postcode(self, state):
        """Переключает отображение почтового индекса"""
        self.show_postcode = state == Qt.Checked
        self.update_address_display()

    def update_address_display(self):
        """Обновляет отображение адреса с учетом почтового индекса"""
        if not self.current_address:
            self.address_label.setText("Адрес не указан")
            return

        if self.show_postcode and self.postcode:
            self.address_label.setText(f"Найденный адрес: {self.current_address} ({self.postcode})")
        else:
            self.address_label.setText(f"Найденный адрес: {self.current_address}")

    def eventFilter(self, obj, event):
        """Обработчик событий для возврата фокуса"""
        if event.type() == QEvent.FocusOut and obj is self.search_input:
            self.setFocus()
            return True
        return super().eventFilter(obj, event)

    def load_map(self):
        """Загружает карту с текущими параметрами и сохраняет метку."""
        map_dict = {
            "address": "https://static-maps.yandex.ru/v1?lang=ru_RU&",
            "coordinates": f"&ll={self.longitude},{self.latitude}",
            "zoom": f"&spn={self.zoom},{self.zoom}",
            "size": "&size=650,450",
            "scale": f"&scale={self.scale}",
            "theme": f"&theme={self.theme}",
            "api_key": f"&apikey={self.apikey_static_map}",
        }

        # Метка сохраняется при любых изменениях карты
        if self.marker:
            map_dict["marker"] = f"&pt={self.marker[0]},{self.marker[1]},pm2rdl"

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
        """Ищет объект по введённому адресу и отображает его адрес."""
        query = self.search_input.text().strip()
        if not query:
            return

        try:
            geocoder_url = (
                f"https://geocode-maps.yandex.ru/1.x/?format=json&apikey={self.apikey_geocoder}"
                f"&geocode={query}"
            )
            response = requests.get(geocoder_url)

            if response.status_code == 200:
                data = json.loads(response.text)
                feature_member = data["response"]["GeoObjectCollection"]["featureMember"]

                if not feature_member:
                    self.address_label.setText("Ничего не найдено")
                    return

                geo_object = feature_member[0]["GeoObject"]
                pos = geo_object["Point"]["pos"]
                self.longitude, self.latitude = map(float, pos.split())
                self.marker = (self.longitude, self.latitude)

                # Получаем полный адрес и почтовый индекс
                meta_data = geo_object["metaDataProperty"]["GeocoderMetaData"]
                self.current_address = meta_data["text"]

                # Извлекаем почтовый индекс, если есть
                self.postcode = ""
                if "Address" in meta_data and "postal_code" in meta_data["Address"]:
                    self.postcode = meta_data["Address"]["postal_code"]

                self.update_address_display()
                self.zoom = 0.005
                self.load_map()
            else:
                self.address_label.setText("Ошибка при поиске")
                print(f"Ошибка геокодера: {response.status_code}")
        except Exception as e:
            self.address_label.setText("Ошибка соединения")
            print(f"Ошибка при поиске: {e}")

    def reset_search(self):
        """Сбрасывает результаты поиска, включая адрес и индекс."""
        self.marker = None
        self.current_address = ""
        self.postcode = ""
        self.address_label.setText("Адрес не указан")
        self.load_map()

    def toggle_theme(self):
        """Переключает тему с сохранением метки."""
        self.theme = "dark" if self.theme == "light" else "light"
        self.theme_btn.setText("Светлая тема" if self.theme == "dark" else "Тёмная тема")
        self.load_map()  # Метка сохранится при переключении темы

    def keyPressEvent(self, event):
        """Обрабатывает нажатия клавиш с сохранением метки."""
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom = max(0.0001, self.zoom - self.zoom_step)
            self.load_map()  # Метка сохранится автоматически в load_map
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