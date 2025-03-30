import math
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel,
                             QVBoxLayout, QWidget, QPushButton,
                             QLineEdit, QHBoxLayout, QCheckBox)
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt, QEvent
import requests
import json


"""
    установите библиотеки

    Запустите main.py

    нажимайте/зажимайте кнопки + - (приблизить, отдалить) или колесико мыши
    нажимайте/зажимайте кнопки вверх, вниз, влево, вправо
    Переключайте тему кнопкой на окне
    Ищите место в поиске, чтобы сбросить метку, нажмите сбросить
    Переключайте отображение почтового индекса (не у всех объектов он есть)
    кликайте левой кнопкой мыши чтобы определить адрес места
    кликайте правой кнопкой мыши чтобы определить ближайшую организацию в радиусе 50 метров
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

        self.search_btn.setShortcut("Return")  # Поиск по Enter
        self.reset_btn.setShortcut("Esc")  # Сброс по Esc

        self.search_input.installEventFilter(self)
        self.setFocus()
        self.load_map()

    def map_click_handler(self, event):
        """Обрабатывает клики по карте"""
        if event.button() == Qt.LeftButton:
            # Левый клик - поиск адреса (существующий код)
            self._handle_left_click(event)
        elif event.button() == Qt.RightButton:
            # Правый клик - поиск организаций
            self._handle_right_click(event)

    def _handle_left_click(self, event):
        """Обработка левого клика (поиск адреса)"""
        # Переносим сюда существующий код из map_click_handler
        img_width, img_height = 650, 450
        click_x = event.pos().x() - (self.map_label.width() - img_width) // 2
        click_y = event.pos().y() - (self.map_label.height() - img_height) // 2

        if not (0 <= click_x < img_width and 0 <= click_y < img_height):
            return

        left, top = self._get_map_bounds()
        right = left + 2 * self.zoom * (img_width / img_height)
        bottom = top - 2 * self.zoom

        lon = left + (click_x / img_width) * (right - left)
        lat = top - (click_y / img_height) * (top - bottom)

        self.search_by_coordinates(lon, lat)

    def _handle_right_click(self, event):
        """Обработка правого клика (поиск организаций)"""
        img_width, img_height = 650, 450
        click_x = event.pos().x() - (self.map_label.width() - img_width) // 2
        click_y = event.pos().y() - (self.map_label.height() - img_height) // 2

        if not (0 <= click_x < img_width and 0 <= click_y < img_height):
            return

        left, top = self._get_map_bounds()
        right = left + 2 * self.zoom * (img_width / img_height)
        bottom = top - 2 * self.zoom

        lon = left + (click_x / img_width) * (right - left)
        lat = top - (click_y / img_height) * (top - bottom)

        self.search_organization(lon, lat)

    def search_organization(self, lon, lat):
        """Ищет организации в радиусе 50 метров от указанной точки"""
        # Сбрасываем предыдущие результаты
        self.reset_search()

        try:
            # Формируем запрос к геокодеру с параметром kind=org
            geocoder_url = (
                f"https://geocode-maps.yandex.ru/1.x/?format=json&apikey={self.apikey_geocoder}"
                f"&geocode={lon},{lat}&lang=ru_RU&results=1"
            )
            response = requests.get(geocoder_url, timeout=2)

            if response.status_code == 200:
                data = json.loads(response.text)
                feature_member = data["response"]["GeoObjectCollection"]["featureMember"]

                if not feature_member:
                    self.address_label.setText("Организации не найдены")
                    return

                geo_object = feature_member[0]["GeoObject"]
                pos = geo_object["Point"]["pos"]
                org_lon, org_lat = map(float, pos.split())

                # Проверяем расстояние до организации (50 метров)
                if self._calculate_distance(lon, lat, org_lon, org_lat) > 50:
                    self.address_label.setText("Близлежащие организации не найдены")
                    return

                # Устанавливаем метку
                self.marker = (org_lon, org_lat)

                # Получаем название и адрес организации
                meta_data = geo_object["metaDataProperty"]["GeocoderMetaData"]
                org_name = meta_data["name"] if "name" in meta_data else "Организация"
                address = meta_data["text"]

                self.current_address = f"{org_name}, {address}"
                self.postcode = ""
                if "Address" in meta_data and "postal_code" in meta_data["Address"]:
                    self.postcode = meta_data["Address"]["postal_code"]

                self.update_address_display()
                self.load_map()

            else:
                self.address_label.setText("Ошибка при поиске организаций")
                print(f"Ошибка геокодера: {response.status_code}")
        except Exception as e:
            self.address_label.setText("Ошибка соединения")
            print(f"Ошибка при поиске организаций: {e}")

    def _calculate_distance(self, lon1, lat1, lon2, lat2):
        """Вычисляет расстояние между точками в метрах (формула гаверсинусов)"""
        R = 6371000  # Радиус Земли в метрах
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

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
            response = requests.get(geocoder_url, timeout=2)

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
            response = requests.get(geocoder_url, timeout=2)

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
        """Переключает тему карты и всего приложения с кастомными стилями"""
        # Переключаем тему карты
        self.theme = "dark" if self.theme == "light" else "light"
        self.theme_btn.setText("Светлая тема" if self.theme == "dark" else "Тёмная тема")

        app = QApplication.instance()

        if self.theme == "dark":
            # Тёмная тема
            dark_palette = app.palette()
            # Основные цвета
            dark_palette.setColor(dark_palette.Window, QColor(53, 53, 53))
            dark_palette.setColor(dark_palette.WindowText, Qt.white)
            dark_palette.setColor(dark_palette.Base, QColor(35, 35, 35))
            dark_palette.setColor(dark_palette.AlternateBase, QColor(53, 53, 53))
            dark_palette.setColor(dark_palette.Text, Qt.white)
            dark_palette.setColor(dark_palette.Button, QColor(53, 53, 53))
            dark_palette.setColor(dark_palette.ButtonText, Qt.white)
            # Акцентные цвета
            dark_palette.setColor(dark_palette.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(dark_palette.HighlightedText, Qt.white)
            app.setPalette(dark_palette)

            # Дополнительные стили для тёмной темы
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #353535;
                }
                QLabel, QCheckBox {
                    color: white;
                }
                QLineEdit {
                    background: #353535;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton {
                    background: #454545;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #555;
                }
                QPushButton:pressed {
                    background: #656565;
                }
            """)
        else:
            # Светлая тема (кастомная)
            light_palette = app.palette()
            # Основные цвета
            light_palette.setColor(light_palette.Window, QColor(240, 240, 240))
            light_palette.setColor(light_palette.WindowText, Qt.black)
            light_palette.setColor(light_palette.Base, Qt.white)
            light_palette.setColor(light_palette.AlternateBase, QColor(240, 240, 240))
            light_palette.setColor(light_palette.Text, Qt.black)
            light_palette.setColor(light_palette.Button, QColor(240, 240, 240))
            light_palette.setColor(light_palette.ButtonText, Qt.black)
            # Акцентные цвета
            light_palette.setColor(light_palette.Highlight, QColor(100, 150, 220))
            light_palette.setColor(light_palette.HighlightedText, Qt.white)
            app.setPalette(light_palette)

            # Дополнительные стили для светлой темы
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                }
                QLabel, QCheckBox {
                    color: black;
                }
                QLineEdit {
                    background: white;
                    color: black;
                    border: 1px solid #ccc;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton {
                    background: #f5f5f5;
                    color: black;
                    border: 1px solid #ccc;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #e5e5e5;
                }
                QPushButton:pressed {
                    background: #d5d5d5;
                }
            """)

        self.load_map()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom = max(0.0001, self.zoom - self.zoom_step)
        else:
            self.zoom = min(50.0, self.zoom + self.zoom_step)
        self.load_map()

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
