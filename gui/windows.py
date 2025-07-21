# windows.py
import sys
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore

# Yerel modüller (tema, config, sayfalar vb.)
from gui.style import apply            # tema paletini uygular
from gui.config.config_util import load, save

from gui.pages.home_page          import HomePage
from gui.pages.segmentation_page  import SegmentationPage
from gui.pages.calibration_page   import CalibrationPage
from gui.pages.settings_page      import SettingsPage     # tema seçicisi
from gui.pages.account_page       import AccountPage

# sidebar’da sırasıyla görünecek ikon isimleri
ICON_NAMES   = ["home", "segment", "calibration", "settings", "account"]
TOP_ICONS    = ["home", "segment", "calibration"]   # üst tarafta
BOTTOM_ICONS = ["settings", "account"]              # alt tarafta


def icon_path(theme: str, name: str) -> str:
    """
    icons/<light|dark>/<name>.png döner.
    Bu proje diziliminde __file__ konumuna göre path oluşturuyoruz.
    """
    base = Path(__file__).resolve().parent / "icons" / theme
    return str(base / f"{name}.png")


class SideButton(QtWidgets.QToolButton):
    """Sol kenar çubuğundaki ikon butonları."""

    def __init__(self, name: str, page_idx: int, change_cb, theme: str):
        super().__init__()
        self._name  = name
        self._idx   = page_idx
        self._theme = theme
        self.setIconSize(QtCore.QSize(40, 40))
        self.setCheckable(True)
        self.clicked.connect(lambda: change_cb(self._idx))

        self.setStyleSheet("""
            QToolButton{
                border:none; background:transparent; padding:6px;
            }
            QToolButton:hover{
                background:#4b4b4b;
                border-radius:4px;
            }
            QToolButton:checked{
                background:#6a6a6a;
                border-radius:4px;
            }
        """)
        self._refresh_icon()

    def set_theme(self, theme: str):
        self._theme = theme
        self._refresh_icon()

    def _refresh_icon(self):
        self.setIcon(QtGui.QIcon(icon_path(self._theme, self._name)))


class MainWindow(QtWidgets.QWidget):
    """Ana uygulama penceresi, sol kenar menü + sayfa yığını."""

    def __init__(self):
        super().__init__()

        # 1) Kalıcı ayarları oku
        self._settings = load()          # {"theme": "...", ...}
        self._theme    = self._settings.get("theme", "dark")

        # 2) Pencere temel özellikleri
        self.setWindowTitle("3D Point-Cloud Studio")
        self.resize(1400, 800)

        # 3) Ana yerleşim
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Sol kenar çubuğu
        sidebar = QtWidgets.QVBoxLayout()
        sidebar.setAlignment(QtCore.Qt.AlignTop)
        sidebar.setSpacing(0)
        sidebar.setContentsMargins(4, 4, 4, 4)
        root.addLayout(sidebar, 0)

        # Sayfa yığını
        self._stack = QtWidgets.QStackedWidget()
        root.addWidget(self._stack, 1)

        # 4) Sayfaları oluştur
        self._settings_page = SettingsPage()    # tema sinyali
        self._settings_page.theme_changed.connect(self._update_theme)

        # Burada segmentation_page'i de değişkende tutuyoruz
        self.seg_page = SegmentationPage()

        pages = [
            HomePage(),
            self.seg_page,
            CalibrationPage(),
            self._settings_page,
            AccountPage()
        ]
        for page in pages:
            self._stack.addWidget(page)

        # 5) Kenar çubuğu butonları
        self._buttons = []
        top_box = QtWidgets.QVBoxLayout()
        top_box.setAlignment(QtCore.Qt.AlignHCenter)
        for idx, name in enumerate(TOP_ICONS):
            btn = SideButton(name, idx, self._switch_page, self._theme)
            btn.setToolTip(name.capitalize())
            top_box.addWidget(btn)
            self._buttons.append(btn)
        sidebar.addLayout(top_box)

        sidebar.addStretch(1)  # Ayırıcı

        # alt grup
        bottom_box = QtWidgets.QVBoxLayout()
        bottom_box.setAlignment(QtCore.Qt.AlignHCenter)
        for i, name in enumerate(BOTTOM_ICONS, start=len(TOP_ICONS)):
            btn = SideButton(name, i, self._switch_page, self._theme)
            btn.setToolTip(name.capitalize())
            bottom_box.addWidget(btn)
            self._buttons.append(btn)
        sidebar.addLayout(bottom_box)

        # 6) Varsayılan sayfa
        self._buttons[0].setChecked(True)
        self._stack.setCurrentIndex(0)

        # 7) Uygulama paletini uygula (tema)
        apply(QtWidgets.QApplication.instance(), self._theme)

    def _switch_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, b in enumerate(self._buttons):
            b.setChecked(i == idx)

    def _update_theme(self, new_theme: str):
        """SettingsPage'in theme_changed(str) sinyalinden gelir."""
        if new_theme == self._theme:
            return
        self._theme = new_theme
        apply(QtWidgets.QApplication.instance(), self._theme)

        for b in self._buttons:
            b.set_theme(self._theme)

        # diske kaydet
        self._settings["theme"] = self._theme
        save(self._settings)

    def closeEvent(self, event: QtGui.QCloseEvent):
        """
        Pencere kapanırken eğer SegmentationPage üzerinde bir thread çalışıyorsa
        durdurup bekleyelim. Aksi halde "QThread: Destroyed while thread is still running"
        hatası alırız.
        """
        # seg_page içinde thread var mı?
        if self.seg_page._segment_thread and self.seg_page._segment_thread.isRunning():
            self.seg_page._segment_thread.stop()
            self.seg_page._segment_thread.wait()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
