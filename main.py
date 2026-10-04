import io
import math
import os
import runpy
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import hid
from PIL import Image
from PySide6.QtCore import QLocale, QProcess, QSettings, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "ALIENTEK T90 Logo Tool"
APP_VERSION = "2.0.0"

VID = 0x19F5
PID = 0x3245

WIDTH = 160
HEIGHT = 40

WINDOW_WIDTH = 1080
WINDOW_HEIGHT = 820

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"

FLASHER = BASE / "t90_flash.py"

APP_LOGO = ASSETS / "app-icon.png"
T90_IMAGE = ASSETS / "t90.png"

GUIDE_UK = ASSETS / "upgrade-uk.jpeg"
GUIDE_EN = ASSETS / "upgrade-en.jpeg"
GUIDE_RU = ASSETS / "upgrade-ru.jpeg"


TEXT = {
    "uk": {
        "title": "ALIENTEK T90 Logo Tool",
        "subtitle": "Завантаження власного логотипа на T90",

        "ready": "● Готово",
        "connected": "● T90 підключений",
        "writing": "● Записую...",
        "success": "● Успішно",
        "error": "● Помилка",

        "drop_title": "Перетягніть зображення сюди",
        "drop_subtitle": "або натисніть, щоб вибрати файл",

        "open": "Відкрити файл",
        "guide": "Інструкція",
        "flash": "Записати на T90",

        "resize": "Режим зображення",
        "fit": "Розмір",
"quality": "Якість",
"stretch": "Розтягнути",
        "contain": "Вписати",
        "sharp": "Чіткіше",
        "smooth": "Згладжено",

        "file_none": "Файл не вибрано",
        "preview": "Попередній перегляд",
        "result": "Результат 160 × 40 px",

        "tip": "Оригінал не змінюється • тимчасовий PNG видаляється після запису",

        "log": "Журнал",

        "loaded": "Завантажено",
        "loaded_success": "Зображення завантажено успішно",
        "flash_success": "✓ УСПІШНО ПРОШИТО T90",
        "flash_result_error": "✕ НЕ ВДАЛОСЯ ПРОШИТИ T90",
        "selected": "Обрано",
        "starting": "Запускаю запис...",
        "done": "Запис завершено успішно.",
        "failed": "Запис завершився з помилкою.",

        "no_device": "T90 не підключений",
        "connect_device": "Переведіть T90 у Upgrade Mode та підключіть USB.",

        "bad_image": "Не вдалося відкрити зображення.",
        "clear": "Очистити",

        "guide_title": "Як увійти в Upgrade Mode",
    },

    "en": {
        "title": "ALIENTEK T90 Logo Tool",
        "subtitle": "Upload your own logo to the T90",

        "ready": "● Ready",
        "connected": "● T90 connected",
        "writing": "● Writing...",
        "success": "● Success",
        "error": "● Error",

        "drop_title": "Drag an image here",
        "drop_subtitle": "or click to choose a file",

        "open": "Open file",
        "guide": "Instructions",
        "flash": "Write to T90",

        "resize": "Image mode",
        "fit": "Size",
        "quality": "Quality",
        "stretch": "Stretch",
        "contain": "Fit",
        "sharp": "Sharper",
        "smooth": "Smoothed",

        "file_none": "No file selected",
        "preview": "Preview",
        "result": "Result 160 × 40 px",

        "tip": "Original stays untouched • temporary PNG is deleted after writing",

        "log": "Log",

        "loaded": "Loaded",
        "loaded_success": "Image loaded successfully",
        "flash_success": "✓ T90 FLASHED SUCCESSFULLY",
        "flash_result_error": "✕ T90 FLASH FAILED",
        "selected": "Selected",
        "starting": "Starting write...",
        "done": "Write completed successfully.",
        "failed": "Write finished with an error.",

        "no_device": "T90 is not connected",
        "connect_device": "Enter Upgrade Mode and connect the USB cable.",

        "bad_image": "Could not open the image.",
        "clear": "Clear",

        "guide_title": "How to enter Upgrade Mode",
    },

    "ru": {
        "title": "ALIENTEK T90 Logo Tool",
        "subtitle": "Загрузка собственного логотипа на T90",

        "ready": "● Готово",
        "connected": "● T90 подключён",
        "writing": "● Записываю...",
        "success": "● Успешно",
        "error": "● Ошибка",

        "drop_title": "Перетащите изображение сюда",
        "drop_subtitle": "или нажмите, чтобы выбрать файл",

        "open": "Открыть файл",
        "guide": "Инструкция",
        "flash": "Записать на T90",

        "resize": "Режим изображения",
        "fit": "Размер",
        "quality": "Качество",
        "stretch": "Растянуть",
        "contain": "Вписать",
        "sharp": "Чётче",
        "smooth": "Сглажено",

        "file_none": "Файл не выбран",
        "preview": "Предпросмотр",
        "result": "Результат 160 × 40 px",

        "tip": "Оригинал не изменяется • временный PNG удаляется после записи",

        "log": "Журнал",

        "loaded": "Загружено",
        "loaded_success": "Изображение загружено успешно",
        "flash_success": "✓ T90 УСПЕШНО ПРОШИТ",
        "flash_result_error": "✕ НЕ УДАЛОСЬ ПРОШИТЬ T90",
        "selected": "Выбран",
        "starting": "Запускаю запись...",
        "done": "Запись успешно завершена.",
        "failed": "Запись завершилась с ошибкой.",

        "no_device": "T90 не подключён",
        "connect_device": "Переведите T90 в Upgrade Mode и подключите USB.",

        "bad_image": "Не удалось открыть изображение.",
        "clear": "Очистить",

        "guide_title": "Как войти в Upgrade Mode",
    },
}


def detect_language():
    settings = QSettings(
        "ALIENTEK",
        "T90LogoTool",
    )

    saved = settings.value(
        "language",
        "",
        str,
    ).strip().lower()

    if saved in TEXT:
        return saved

    system = QLocale.system().name().lower()

    if system.startswith("uk"):
        return "uk"

    if system.startswith("ru"):
        return "ru"

    return "en"


def t90_connected():
    try:
        return bool(
            hid.enumerate(
                VID,
                PID,
            )
        )
    except Exception:
        return False


def resize_filter(quality):
    return {
        "sharp": Image.Resampling.LANCZOS,
        "smooth": Image.Resampling.BILINEAR,
    }[quality]


def run_flash_mode():
    if "--t90-flash" not in sys.argv:
        return False

    index = sys.argv.index(
        "--t90-flash"
    )

    args = sys.argv[index + 1:]

    try:
        sys.argv = [
            str(FLASHER)
        ] + args

        runpy.run_path(
            str(FLASHER),
            run_name="__main__",
        )

    except SystemExit:
        raise

    except Exception as exc:
        print(
            f"FLASH ERROR: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)

    return True


class DropArea(QFrame):
    """
    Stable drop area.

    The X button is positioned manually in the corner instead
    of being part of the layout. Therefore adding/removing it
    can NEVER move the centered drop text.
    """

    def __init__(
        self,
        open_callback,
        clear_callback,
    ):
        super().__init__()

        self.open_callback = open_callback
        self.clear_callback = clear_callback

        self.setObjectName(
            "dropArea"
        )

        self.setAcceptDrops(
            True
        )

        # Fixed height prevents all vertical jumping.
        self.setFixedHeight(
            132
        )

        self.clear_button = QPushButton(
            "×",
            self,
        )

        self.clear_button.setObjectName(
            "clearButton"
        )

        self.clear_button.setFixedSize(
            34,
            34,
        )

        self.clear_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.clear_button.clicked.connect(
            self.clear_callback
        )

        self.clear_button.hide()

        # Central content.
        content = QVBoxLayout(
            self
        )

        content.setContentsMargins(
            30,
            22,
            30,
            14,
        )

        content.setSpacing(
            2
        )

        content.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.icon = QLabel(
            "＋"
        )

        self.icon.setObjectName(
            "dropIcon"
        )

        self.icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.icon.setFixedHeight(
            30
        )

        content.addWidget(
            self.icon
        )

        self.title = QLabel()

        self.title.setObjectName(
            "dropTitle"
        )

        self.title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        content.addWidget(
            self.title
        )

        self.subtitle = QLabel()

        self.subtitle.setObjectName(
            "dropSubtitle"
        )

        self.subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        content.addWidget(
            self.subtitle
        )

    def resizeEvent(
        self,
        event,
    ):
        super().resizeEvent(
            event
        )

        # X is anchored to the corner and does not affect layout.
        self.clear_button.move(
            self.width() - 46,
            10,
        )

    def set_text(
        self,
        title,
        subtitle,
    ):
        self.title.setText(
            title
        )

        self.subtitle.setText(
            subtitle
        )

    def show_clear(
        self,
        visible,
    ):
        self.clear_button.setVisible(
            visible
        )

    def mousePressEvent(
        self,
        event,
    ):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.open_callback()

        super().mousePressEvent(
            event
        )

    def dragEnterEvent(
        self,
        event,
    ):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    event.acceptProposedAction()
                    return

        event.ignore()

    def dragMoveEvent(
        self,
        event,
    ):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(
        self,
        event,
    ):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_callback(
                    url.toLocalFile()
                )
                event.acceptProposedAction()
                return

        event.ignore()


class GuideDialog(QDialog):
    """
    Guide window: smaller, wide rectangle.

    The window is sized from the guide image itself, so the image fills
    the WHOLE window - no stretching, no bars, no cropping.
    """

    MAX_WIDTH = 1000
    MAX_HEIGHT = 620
    FALLBACK_RATIO = 1.7

    def __init__(
        self,
        image_path,
        text,
        parent=None,
    ):
        super().__init__(
            parent
        )

        from PySide6.QtGui import QGuiApplication

        self.setWindowTitle(
            text["guide_title"]
        )

        if APP_LOGO.exists():
            self.setWindowIcon(
                QIcon(
                    str(APP_LOGO)
                )
            )

        pixmap = QPixmap(
            str(image_path)
        )

        max_w = self.MAX_WIDTH
        max_h = self.MAX_HEIGHT

        screen = (
            self.screen()
            or QGuiApplication.primaryScreen()
        )

        if screen is not None:
            area = screen.availableGeometry()
            max_w = min(max_w, int(area.width() * 0.92))
            max_h = min(max_h, int(area.height() * 0.88))

        if pixmap.isNull() or pixmap.height() <= 0:
            ratio = self.FALLBACK_RATIO
        else:
            ratio = pixmap.width() / pixmap.height()

        width = max_w
        height = round(width / ratio)

        if height > max_h:
            height = max_h
            width = round(height * ratio)

        self.setFixedSize(
            width,
            height,
        )

        image = QLabel()

        image.setFixedSize(
            width,
            height,
        )

        image.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        if not pixmap.isNull():
            dpr = self.devicePixelRatioF()

            scaled = pixmap.scaled(
                int(width * dpr),
                int(height * dpr),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            scaled.setDevicePixelRatio(
                dpr
            )

            image.setPixmap(
                scaled
            )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(
            0
        )

        layout.addWidget(
            image
        )

        self.setStyleSheet(
            """
            QDialog {
                background: #070f1a;
            }

            QLabel {
                background: #070f1a;
            }
            """
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings(
            "ALIENTEK",
            "T90LogoTool",
        )

        self.lang = detect_language()

        self.source_path = None
        self.source_image = None

        # Image fitting and scaling quality are independent choices.
        self.fit_mode = "contain"
        self.resize_quality = "sharp"
        self._load_status_hold = False
        self._flash_status_hold = False

        self.temp_image_path = None
        self.flash_process = None
        self.flash_running = False

        # Resizable application geometry.
        self.resize(
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
        )
        self.setMinimumSize(
            900,
            680,
        )

        self.setWindowTitle(
            f"{APP_NAME} • v{APP_VERSION}"
        )

        if APP_LOGO.exists():
            self.setWindowIcon(
                QIcon(
                    str(APP_LOGO)
                )
            )

        self.build_ui()
        self.apply_style()
        self.update_texts()

        self.device_timer = QTimer(
            self
        )

        self.device_timer.setInterval(
            1000
        )

        self.device_timer.timeout.connect(
            self.refresh_device
        )

        self.device_timer.start()

        # Safe timer-based status breathing.
        # Deliberately no  / Qt animations.
        self.status_breath_phase = 0.0
        self.status_breath_timer = QTimer(self)
        self.status_breath_timer.setInterval(80)
        self.status_breath_timer.timeout.connect(
            self.update_status_breathing
        )
        self.status_breath_timer.start()

        self.log(
            f"Application started • v{APP_VERSION}"
        )

        self.log(
            f"Language: {self.lang}"
        )

    def tr(
        self,
        key,
    ):
        return TEXT[
            self.lang
        ][key]

    def log(
        self,
        message,
    ):
        stamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        line = (
            f"[{stamp}] {message}"
        )

        print(
            line,
            flush=True,
        )

        if hasattr(
            self,
            "log_view",
        ):
            self.log_view.append(
                line
            )

            scroll = (
                self.log_view
                .verticalScrollBar()
            )

            scroll.setValue(
                scroll.maximum()
            )

    def build_ui(self):
        root = QWidget()

        root.setObjectName(
            "root"
        )

        self.setCentralWidget(
            root
        )

        main = QVBoxLayout(
            root
        )

        main.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        main.setSpacing(
            8
        )

        # =====================================================
        # HEADER
        # =====================================================

        header = QFrame()

        header.setObjectName(
            "header"
        )

        header.setFixedHeight(
            84
        )

        header_layout = QHBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            16,
            10,
            16,
            10,
        )

        header_layout.setSpacing(
            14
        )

        if T90_IMAGE.exists():
            device = QLabel()

            device.setFixedSize(
                120,
                62,
            )

            device.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            pix = QPixmap(
                str(T90_IMAGE)
            )

            pix = pix.scaled(
                114,
                60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            device.setPixmap(
                pix
            )

            header_layout.addWidget(
                device
            )

        title_box = QVBoxLayout()

        title_box.setSpacing(
            2
        )

        self.title = QLabel()

        self.title.setObjectName(
            "title"
        )

        self.subtitle = QLabel()

        self.subtitle.setObjectName(
            "subtitle"
        )

        title_box.addStretch()

        title_box.addWidget(
            self.title
        )

        title_box.addWidget(
            self.subtitle
        )

        title_box.addStretch()

        header_layout.addLayout(
            title_box,
            1,
        )

        # =====================================================
        # LANGUAGE SWITCH
        # =====================================================

        language_frame = QFrame()

        language_frame.setObjectName(
            "languageFrame"
        )

        language_frame.setFixedHeight(
            50
        )

        language_layout = QHBoxLayout(
            language_frame
        )

        language_layout.setContentsMargins(
            5,
            5,
            5,
            5,
        )

        language_layout.setSpacing(
            4
        )

        self.language_group = QButtonGroup(
            self
        )

        self.language_group.setExclusive(
            True
        )

        self.language_buttons = {}

        for code, label in [
            (
                "uk",
                "Українська",
            ),
            (
                "en",
                "English",
            ),
            (
                "ru",
                "Русский",
            ),
        ]:
            button = QPushButton(
                label
            )

            button.setCheckable(
                True
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            self.language_group.addButton(
                button
            )

            self.language_buttons[
                code
            ] = button

            button.clicked.connect(
                lambda checked=False,
                c=code:
                self.change_language(c)
            )

            language_layout.addWidget(
                button
            )

        header_layout.addWidget(
            language_frame
        )

        main.addWidget(
            header
        )

        # =====================================================
        # STATUS
        # =====================================================

        status_row = QHBoxLayout()

        self.status = QLabel()

        self.status.setObjectName(
            "status"
        )

        status_row.addWidget(
            self.status
        )

        status_row.addStretch()

        # Compact status badge. Fixed-height container: extra window height
        # (fullscreen) can never be handed to this row.
        from PySide6.QtWidgets import QSizePolicy as _SP
        status_row.setContentsMargins(0, 0, 0, 0)
        self.status.setSizePolicy(_SP.Policy.Maximum, _SP.Policy.Fixed)
        status_container = QWidget()
        status_container.setObjectName("statusRow")
        status_container.setFixedHeight(32)
        status_container.setStyleSheet("QWidget#statusRow { background: transparent; }")
        status_container.setLayout(status_row)
        main.addWidget(status_container)

        # =====================================================
        # UPLOAD
        # =====================================================

        upload = QFrame()

        upload.setObjectName(
            "card"
        )

        upload.setFixedHeight(
            190
        )

        upload_layout = QVBoxLayout(
            upload
        )

        upload_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        upload_layout.setSpacing(
            10
        )

        self.drop = DropArea(
            self.choose_file,
            self.clear_image,
        )

        upload_layout.addWidget(
            self.drop
        )

        upload_layout.addSpacing(4)

        self.filename = QLabel()

        self.filename.setObjectName(
            "filename"
        )

        self.filename.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.filename.setFixedHeight(
            20
        )

        upload_layout.addWidget(
            self.filename
        )

        main.addWidget(
            upload
        )

        # =====================================================
        # PREVIEW
        # =====================================================

        preview = QFrame()

        preview.setObjectName(
            "card"
        )

        preview.setFixedHeight(
            182
        )

        preview_layout = QVBoxLayout(
            preview
        )

        preview_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )

        preview_layout.setSpacing(
            6
        )

        self.preview_title = QLabel()

        self.preview_title.setObjectName(
            "previewTitle"
        )

        self.preview_title.setFixedHeight(
            20
        )

        preview_layout.addWidget(
            self.preview_title
        )

        self.preview_box = QFrame()

        self.preview_box.setObjectName(
            "previewBox"
        )

        self.preview_image = QLabel()

        self.preview_image.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        preview_inner = QVBoxLayout(
            self.preview_box
        )

        preview_inner.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        preview_inner.addWidget(
            self.preview_image
        )

        preview_layout.addWidget(
            self.preview_box,
            1,
        )

        main.addWidget(
            preview
        )

        # =====================================================
        # CONTROLS
        # =====================================================

        controls = QFrame()

        controls.setObjectName(
            "card"
        )

        controls.setFixedHeight(
            168
        )

        controls_layout = QVBoxLayout(
            controls
        )

        controls_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )

        controls_layout.setSpacing(
            7
        )

        self.resize_title = QLabel()

        self.resize_title.setObjectName(
            "controlTitle"
        )

        controls_layout.addWidget(
            self.resize_title
        )

        resize_frame = QFrame()
        resize_frame.setObjectName(
            "resizeFrame"
        )
        resize_frame.setFixedHeight(
            76
        )

        resize_layout = QHBoxLayout(
            resize_frame
        )

        resize_layout.setContentsMargins(
            10,
            7,
            10,
            7,
        )

        resize_layout.setSpacing(
            10
        )

        # ---------- FIT ----------
        fit_column = QVBoxLayout()
        fit_column.setSpacing(4)

        fit_label = QLabel(
            self.tr("fit")
        )
        fit_label.setObjectName(
            "optionLabel"
        )

        fit_column.addWidget(
            fit_label
        )

        fit_row = QHBoxLayout()
        fit_row.setSpacing(5)

        self.fit_group = QButtonGroup(
            self
        )
        self.fit_group.setExclusive(
            True
        )

        self.fit_buttons = {}

        for code in (
            "stretch",
            "contain",
        ):
            button = QPushButton(
                self.tr(code)
            )

            button.setCheckable(
                True
            )

            button.setObjectName(
                "optionButton"
            )

            button.setMinimumHeight(
                29
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            self.fit_group.addButton(
                button
            )

            self.fit_buttons[
                code
            ] = button

            button.clicked.connect(
                lambda checked=False,
                c=code:
                self.choose_fit(c)
            )

            fit_row.addWidget(
                button,
                1,
            )

        fit_column.addLayout(
            fit_row
        )

        resize_layout.addLayout(
            fit_column,
            1,
        )

        # ---------- SEPARATOR ----------
        separator = QFrame()

        separator.setFrameShape(
            QFrame.Shape.VLine
        )

        separator.setFrameShadow(
            QFrame.Shadow.Plain
        )

        separator.setObjectName(
            "resizeSeparator"
        )

        resize_layout.addWidget(
            separator
        )

        # ---------- QUALITY ----------
        quality_column = QVBoxLayout()
        quality_column.setSpacing(4)

        quality_label = QLabel(
            self.tr("quality")
        )
        quality_label.setObjectName(
            "optionLabel"
        )

        quality_column.addWidget(
            quality_label
        )

        quality_row = QHBoxLayout()
        quality_row.setSpacing(5)

        self.quality_group = QButtonGroup(
            self
        )
        self.quality_group.setExclusive(
            True
        )

        self.quality_buttons = {}

        for code in (
            "sharp",
            "smooth",
        ):
            button = QPushButton(
                self.tr(code)
            )

            button.setCheckable(
                True
            )

            button.setObjectName(
                "optionButton"
            )

            button.setMinimumHeight(
                29
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            self.quality_group.addButton(
                button
            )

            self.quality_buttons[
                code
            ] = button

            button.clicked.connect(
                lambda checked=False,
                c=code:
                self.choose_quality(c)
            )

            quality_row.addWidget(
                button,
                1,
            )

        quality_column.addLayout(
            quality_row
        )

        resize_layout.addLayout(
            quality_column,
            1,
        )

        controls_layout.addWidget(
            resize_frame
        )

        action_row = QHBoxLayout()

        action_row.setSpacing(
            8
        )

        self.open_button = QPushButton()

        self.open_button.clicked.connect(
            self.choose_file
        )

        action_row.addWidget(
            self.open_button
        )

        self.guide_button = QPushButton()

        self.guide_button.clicked.connect(
            self.show_guide
        )

        action_row.addWidget(
            self.guide_button
        )

        action_row.addStretch()

        self.tip = QLabel()

        self.tip.setObjectName(
            "tip"
        )

        action_row.addWidget(
            self.tip
        )

        self.flash_button = QPushButton()

        self.flash_button.setObjectName(
            "flashButton"
        )

        self.flash_button.setFixedSize(
            220,
            39,
        )

        self.flash_button.clicked.connect(
            self.start_flash
        )

        action_row.addWidget(
            self.flash_button
        )

        controls_layout.addLayout(
            action_row
        )

        main.addWidget(
            controls
        )

        # =====================================================
        # LOG
        # =====================================================

        log_card = QFrame()

        log_card.setObjectName(
            "card"
        )

        log_card.setFixedHeight(
            112
        )

        log_layout = QVBoxLayout(
            log_card
        )

        log_layout.setContentsMargins(
            12,
            8,
            12,
            8,
        )

        log_layout.setSpacing(
            4
        )

        self.log_title = QLabel()

        self.log_title.setObjectName(
            "logTitle"
        )

        log_layout.addWidget(
            self.log_title
        )

        self.log_view = QTextEdit()

        self.log_view.setObjectName(
            "logView"
        )

        self.log_view.setReadOnly(
            True
        )

        log_layout.addWidget(
            self.log_view
        )

        main.addWidget(
            log_card
        )

    def apply_style(self):
        self.setStyleSheet(
            """
            QWidget#root {
                background: #09111e;
                color: #eaf1f8;
            }

            QFrame#card,
            QFrame#header {
                background: #111c2d;
                border: 1px solid #263b57;
                border-radius: 16px;
            }

            QLabel#title {
                color: #f6f9fd;
                font-size: 27px;
                font-weight: 800;
            }

            QLabel#subtitle {
                color: #91a5be;
                font-size: 13px;
            }

            QFrame#languageFrame,
            QFrame#resizeFrame {
                background: #0a1423;
                border: 1px solid #263b56;
                border-radius: 14px;
            }

            QFrame#languageFrame QPushButton,
            QFrame#resizeFrame QPushButton {
                border: none;
                border-radius: 10px;
                background: transparent;
                color: #8fa5bd;
                font-size: 12px;
                font-weight: 700;
            }

            QFrame#languageFrame QPushButton:hover,
            QFrame#resizeFrame QPushButton:hover {
                background: #182a42;
                color: #e4edf7;
            }

            QFrame#languageFrame QPushButton:checked,
            QFrame#resizeFrame QPushButton:checked {
                background: #2563eb;
                color: white;
            }

            QLabel#status {
                padding: 6px 13px;
                border-radius: 10px;
                background: #3c3209;
                color: #facc15;
                font-size: 12px;
                font-weight: 800;
            }

            QLabel#status[connected="true"] {
                background: #0d3824;
                color: #4ade80;
            }

            QLabel#status[writing="true"] {
                background: #102f54;
                color: #60a5fa;
            }

            QLabel#status[success="true"] {
                background: #0d3824;
                color: #4ade80;
            }

            QLabel#status[error="true"] {
                background: #461b1b;
                color: #f87171;
            }

            QFrame#dropArea {
                background: #0d1727;
                border: 2px dashed #3b5879;
                border-radius: 14px;
            }

            QFrame#dropArea:hover {
                background: #101d30;
                border-color: #5b86ba;
            }

            QLabel#dropIcon {
                color: #62a7ff;
                font-size: 35px;
            }

            QLabel#dropTitle {
                color: #eef5fd;
                font-size: 16px;
                font-weight: 800;
            }

            QLabel#dropSubtitle {
                color: #8096af;
                font-size: 11px;
            }

            QPushButton#clearButton {
                background: #16263b;
                border: 1px solid #39506b;
                border-radius: 10px;
                color: #d5e1ee;
                font-size: 22px;
                font-weight: 400;
                padding: 0;
            }

            QPushButton#clearButton:hover {
                background: #412028;
                border-color: #87404d;
                color: #ff8a98;
            }

            QLabel#filename {
                color: #91a7c0;
                font-size: 11px;
                font-weight: 700;
            }

            QLabel#previewTitle {
                color: #8ea5bd;
                font-size: 11px;
                font-weight: 800;
            }

            QFrame#previewBox {
                background: #070f1a;
                border: 1px solid #1f344c;
                border-radius: 11px;
            }

            QPushButton#optionButton {
                border-radius: 7px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }

            QPushButton#optionButton:checked {
                font-weight: 700;
            }

            QFrame#resizeSeparator {
                margin-top: 4px;
                margin-bottom: 4px;
            }

            QLabel#optionLabel {
                color: #7f95ad;
                font-size: 9px;
                font-weight: 700;
            }

            QLabel#controlTitle {
                color: #b8c9da;
                font-size: 12px;
                font-weight: 800;
            }

            QLabel#tip {
                color: #7188a2;
                font-size: 10px;
            }

            QLabel#logTitle {
                color: #b9c9db;
                font-size: 12px;
                font-weight: 800;
            }

            QPushButton {
                min-height: 39px;
                border: 1px solid #2d4765;
                border-radius: 11px;
                background: #16273c;
                color: #e8eff7;
                padding: 0 15px;
                font-size: 12px;
                font-weight: 700;
            }




            QPushButton:hover {
                background: #1d3450;
                border-color: #4d739e;
            }

            QPushButton:disabled {
                background: #101a29;
                color: #556983;
                border-color: #1e3047;
            }

            QPushButton#flashButton {
                border: none;
                border-radius: 11px;
                background: #2563eb;
                color: white;
                font-size: 13px;
                font-weight: 800;
            }

            QPushButton#flashButton:hover {
                background: #3b82f6;
            }

            QPushButton#flashButton:disabled {
                background: #1d3154;
                color: #7185a0;
            }

            QTextEdit#logView {
                background: #070f1a;
                border: 1px solid #1d3148;
                border-radius: 9px;
                color: #aebed0;
                padding: 5px;
                font-family: monospace;
                font-size: 10px;
            }
            """
        )

    def set_status(
        self,
        status,
    ):
        previous = getattr(
            self,
            "_last_status",
            None,
        )

        self._last_status = status

        self.status.setText(
            self.tr(status)
        )

        self.status.setProperty(
            "connected",
            status == "connected",
        )
        self.status.setProperty(
            "writing",
            status == "writing",
        )
        self.status.setProperty(
            "success",
            status == "success",
        )
        self.status.setProperty(
            "error",
            status == "error",
        )

        self.status.style().unpolish(
            self.status
        )
        self.status.style().polish(
            self.status
        )

        if previous != status:
            self.status_breath_phase = 0.0

        self.update_status_breathing()


    def update_status_breathing(
        self,
    ):
        if not hasattr(self, "status"):
            return

        status = getattr(
            self,
            "_last_status",
            "ready",
        )

        # 0.01 / 80 ms -> approximately 8 seconds per cycle.
        self.status_breath_phase = (
            getattr(
                self,
                "status_breath_phase",
                0.0,
            )
            + 0.01
        ) % (2.0 * math.pi)

        wave = (
            math.sin(self.status_breath_phase)
            + 1.0
        ) * 0.5

        colors = {
            "ready": (
                "#facc15",
                "#3c3209",
            ),
            "connected": (
                "#4ade80",
                "#0d3824",
            ),
            "writing": (
                "#60a5fa",
                "#102f54",
            ),
            "success": (
                "#4ade80",
                "#0d3824",
            ),
            "error": (
                "#f87171",
                "#461b1b",
            ),
        }

        foreground, background = colors.get(
            status,
            colors["ready"],
        )

        # Very subtle smooth breathing.
        border_alpha = (
            0.18
            + (wave * 0.24)
        )

        self.status.setStyleSheet(
            f"""
            QLabel#status {{
                padding: 6px 13px;
                border-radius: 10px;
                background: {background};
                color: {foreground};
                font-size: 12px;
                font-weight: 800;
                border: 1px solid rgba(
                    255,
                    255,
                    255,
                    {border_alpha:.3f}
                );
            }}
            """
        )




    def update_texts(self):
        self.setWindowTitle(
            f"{APP_NAME} • v{APP_VERSION}"
        )

        self.title.setText(
            self.tr("title")
        )

        self.subtitle.setText(
            self.tr("subtitle")
        )

        self.drop.set_text(
            self.tr("drop_title"),
            self.tr("drop_subtitle"),
        )

        self.open_button.setText(
            self.tr("open")
        )

        self.guide_button.setText(
            self.tr("guide")
        )

        self.flash_button.setText(
            self.tr("flash")
        )

        self.resize_title.setText(
            self.tr("resize")
        )

        self.preview_title.setText(
            (
                self.tr("result")
                if self.source_image
                else self.tr("preview")
            )
        )

        self.tip.setText(
            self.tr("tip")
        )

        self.log_title.setText(
            self.tr("log")
        )

        self.filename.setText(
            self.source_path.name
            if self.source_path
            else self.tr("file_none")
        )

        for code, button in self.language_buttons.items():
            button.setChecked(
                code == self.lang
            )

        for code, button in list(self.fit_buttons.items()) + list(self.quality_buttons.items()):
            button.setText(
                self.tr(code)
            )

            if code in ("stretch", "contain"):
                button.setChecked(
                    code == self.fit_mode
                )
            else:
                button.setChecked(
                    code == self.resize_quality
                )

        self.drop.show_clear(
            self.source_image is not None
        )

        self.refresh_device()

        if self.source_image:
            self.update_preview()

    def change_language(
        self,
        language,
    ):
        if language not in TEXT:
            return

        if language == self.lang:
            return

        self.lang = language

        self.settings.setValue(
            "language",
            language,
        )

        self.update_texts()

        self.log(
            f"Language changed to {language}"
        )

    def choose_fit(self, mode):
        self.fit_mode = mode

        for code, button in self.fit_buttons.items():
            button.setChecked(
                code == mode
            )

        self.update_preview()

    def choose_quality(self, quality):
        self.resize_quality = quality

        for code, button in self.quality_buttons.items():
            button.setChecked(
                code == quality
            )

        self.update_preview()


    def refresh_device(self):
        if getattr(self, "_flash_status_hold", False):
            return

        if self.flash_running:
            return

        if self._load_status_hold:
            self.update_buttons()
            return

        if t90_connected():
            self.set_status(
                "connected"
            )
        else:
            self.set_status(
                "ready"
            )

        self.update_buttons()

    def update_buttons(self):
        active = (
            self.source_image is not None
            and t90_connected()
            and not self.flash_running
        )

        self.flash_button.setEnabled(
            active
        )

        self.open_button.setEnabled(
            not self.flash_running
        )

        self.guide_button.setEnabled(
            not self.flash_running
        )

        self.drop.setEnabled(
            not self.flash_running
        )

        self.drop.show_clear(
            self.source_image is not None
            and not self.flash_running
        )

        for button in list(self.fit_buttons.values()) + list(self.quality_buttons.values()):
            button.setEnabled(
                not self.flash_running
            )

    def choose_file(
        self,
        dropped_path=None,
    ):
        if dropped_path:
            self.load_image(
                dropped_path
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("open"),
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All files (*)",
        )

        if path:
            self.load_image(
                path
            )

    def load_image(
        self,
        path,
    ):
        try:
            image = Image.open(
                path
            )

            image.load()

            if image.mode not in (
                "RGB",
                "RGBA",
            ):
                image = image.convert(
                    "RGBA"
                )

            self.source_image = image.copy()

            self.source_path = Path(
                path
            )

            # Only text changes.
            # The drop area itself does NOT change layout.
            self.filename.setText(
                self.source_path.name
            )

            self.drop.show_clear(
                True
            )

            self.update_preview()
            self.update_buttons()

            self.log(
                f"{self.tr('loaded')}: "
                f"{self.source_path.name} "
                f"({image.width}×{image.height})"
            )

            self._load_status_hold = True
            self.set_status("success")
            self.log(
                self.tr("loaded_success")
            )
            QTimer.singleShot(
                2500,
                self.release_load_status,
            )

        except Exception as exc:
            self.clear_image(
                quiet=True
            )

            self.log(
                f"IMAGE ERROR: {exc}"
            )

            QMessageBox.critical(
                self,
                self.tr("bad_image"),
                str(exc),
            )

    def release_load_status(self):
        self._load_status_hold = False
        if not self.flash_running:
            self.refresh_device()

    def clear_image(
        self,
        quiet=False,
    ):
        self.source_image = None
        self.source_path = None

        self.filename.setText(
            self.tr("file_none")
        )

        self.drop.show_clear(
            False
        )

        self.preview_title.setText(
            self.tr("preview")
        )

        self.preview_image.clear()

        self.update_buttons()

        if not quiet:
            self.log(
                "Image cleared."
            )

    def processed_image(self):
        if self.source_image is None:
            return None

        image = self.source_image.convert(
            "RGBA"
        )

        resample = resize_filter(
            self.resize_quality
        )

        if self.fit_mode == "stretch":
            return image.resize(
                (
                    WIDTH,
                    HEIGHT,
                ),
                resample=resample,
            )

        # Keep the original aspect ratio and fill the remaining area
        # with the same dark background used by the preview.
        scale = min(
            WIDTH / image.width,
            HEIGHT / image.height,
        )

        new_width = max(
            1,
            round(image.width * scale),
        )
        new_height = max(
            1,
            round(image.height * scale),
        )

        resized = image.resize(
            (
                new_width,
                new_height,
            ),
            resample=resample,
        )

        canvas = Image.new(
            "RGBA",
            (
                WIDTH,
                HEIGHT,
            ),
            (7, 15, 26, 255),
        )

        x = (WIDTH - new_width) // 2
        y = (HEIGHT - new_height) // 2

        canvas.alpha_composite(
            resized,
            (
                x,
                y,
            ),
        )

        return canvas

    def update_preview(self):
        image = self.processed_image()

        if image is None:
            self.preview_image.clear()
            self.preview_title.setText(
                self.tr("preview")
            )
            return

        data = io.BytesIO()

        image.save(
            data,
            format="PNG",
        )

        pixmap = QPixmap()

        if not pixmap.loadFromData(
            data.getvalue(),
            "PNG",
        ):
            self.preview_image.clear()
            return

        # Keep the real 160×40 (4:1) aspect ratio in the preview.
        box = self.preview_box.size()

        scaled = pixmap.scaled(
            max(1, box.width() - 16),
            max(1, box.height() - 16),
            Qt.AspectRatioMode.KeepAspectRatio,
            (
                Qt.TransformationMode.FastTransformation
                if self.resize_quality == "sharp"
                else Qt.TransformationMode.SmoothTransformation
            ),
        )

        self.preview_image.setPixmap(
            scaled
        )

        self.preview_title.setText(
            f"{self.tr('result')} • "
            f"{self.tr(self.fit_mode)} • "
            f"{self.tr(self.resize_quality)}"
        )

    def show_guide(self):
        guide = (
            GUIDE_UK
            if self.lang == "uk"
            else GUIDE_RU
            if self.lang == "ru"
            else GUIDE_EN
        )

        if not guide.exists():
            QMessageBox.warning(
                self,
                self.tr("guide"),
                str(guide),
            )
            return

        dialog = GuideDialog(
            guide,
            TEXT[self.lang],
            self,
        )

        dialog.exec()

    def cleanup_temp(self):
        if not self.temp_image_path:
            return

        path = Path(
            self.temp_image_path
        )

        try:
            if path.exists():
                path.unlink()

                self.log(
                    f"Temporary PNG deleted: {path}"
                )

        except Exception as exc:
            self.log(
                f"Temporary PNG cleanup error: {exc}"
            )

        finally:
            self.temp_image_path = None

    def prepare_temp_logo(self):
        image = self.processed_image()

        if image is None:
            return None

        self.cleanup_temp()

        fd, path = tempfile.mkstemp(
            prefix="t90_logo_",
            suffix=".png",
        )

        os.close(
            fd
        )

        image.save(
            path,
            format="PNG",
        )

        self.temp_image_path = path

        self.log(
            f"Temporary 160×40 PNG created: {path}"
        )

        return Path(
            path
        )

    def start_flash(self):
        if self.flash_running:
            return

        if not t90_connected():
            self.log(
                self.tr("no_device")
            )

            QMessageBox.warning(
                self,
                self.tr("no_device"),
                self.tr("connect_device"),
            )

            return

        temp = self.prepare_temp_logo()

        if temp is None:
            return

        executable = Path(
            sys.executable
        )

        script = Path(
            __file__
        ).resolve()

        # When running from an AppImage, sys.executable points
        # inside /tmp/.mount_... . That path may be mounted noexec,
        # so pkexec cannot launch the internal binary directly.
        # APPIMAGE points to the original executable AppImage file.
        appimage = os.environ.get("APPIMAGE")

        if getattr(
            sys,
            "frozen",
            False,
        ):
            flash_executable = (
                Path(appimage)
                if appimage
                else executable
            )

            command = [
                str(flash_executable),
                "--t90-flash",
                "logo",
                str(temp),
                "--yes",
            ]
        else:
            command = [
                str(executable),
                str(script),
                "--t90-flash",
                "logo",
                str(temp),
                "--yes",
            ]

        if shutil.which(
            "pkexec"
        ):
            command.insert(
                0,
                "pkexec"
            )

        self.flash_process = QProcess(
            self
        )

        self.flash_process.setProgram(
            command[0]
        )

        self.flash_process.setArguments(
            command[1:]
        )

        self.flash_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )

        self.flash_process.readyReadStandardOutput.connect(
            self.read_flash_output
        )

        self.flash_process.finished.connect(
            self.flash_finished
        )

        self.flash_process.errorOccurred.connect(
            self.flash_error
        )

        self.flash_running = True

        self.set_status(
            "writing"
        )

        self.update_buttons()

        self.log(
            self.tr("starting")
        )

        self.log(
            "Command: "
            + " ".join(command)
        )

        self.flash_process.start()

        if not self.flash_process.waitForStarted(
            3000
        ):
            self.flash_running = False

            self.set_status(
                "error"
            )

            self.update_buttons()

            self.log(
                "Could not start flash process."
            )

            self.cleanup_temp()

    def read_flash_output(self):
        if not self.flash_process:
            return

        data = bytes(
            self.flash_process
            .readAllStandardOutput()
        )

        text = data.decode(
            "utf-8",
            errors="replace",
        )

        for line in text.splitlines():
            line = line.strip()

            if line:
                self.log(
                    line
                )

    def flash_error(
        self,
        error,
    ):
        self.log(
            f"QProcess error: {error}"
        )

    def flash_finished(
        self,
        exit_code,
        exit_status,
    ):
        self.read_flash_output()

        self.flash_running = False
        self._flash_status_hold = True

        if (
            exit_code == 0
            and exit_status
            == QProcess.ExitStatus.NormalExit
        ):
            self.set_status(
                "success"
            )

            self.status.setText(
                self.tr("flash_success")
            )

            self.log(
                self.tr("flash_success")
            )

        else:
            self.set_status(
                "error"
            )

            self.status.setText(
                self.tr("flash_result_error")
            )

            self.log(
                self.tr("flash_result_error")
                + f" Exit code: {exit_code}"
            )

        # Generated PNG is always removed.
        # Original image stays untouched.
        self.cleanup_temp()

        self.update_buttons()

        QTimer.singleShot(
            5000,
            self._release_flash_status,
        )

    def _release_flash_status(self):
        self._flash_status_hold = False
        self.refresh_device()

    def closeEvent(
        self,
        event,
    ):
        self.cleanup_temp()
        event.accept()


def main():
    if run_flash_mode():
        return

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        APP_NAME
    )

    app.setOrganizationName(
        "ALIENTEK"
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()
