from PyQt5 import QtWidgets, QtCore
from gui.config.config_util import load, save       

class SettingsPage(QtWidgets.QWidget):
    """
    • Dark / Light seçicisi bu sayfada.
    • "Algoritma Ayarları" altında CAD point sayısı girilebilir.
    • "Kaydet" butonuna basılınca tüm ayarlar config/settings.json içine kaydedilir.
    • theme_changed(str) ve cad_point_count_changed(int) sinyalleri güncel değerlerle yayınlanır.
    """
    theme_changed = QtCore.pyqtSignal(str)
    cad_point_count_changed = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()

        # Mevcut ayarları yükle
        self._cfg = load()  # örn: {"theme": "dark", "cad_point_count": 10000}
        current_theme = self._cfg.get("theme", "dark")
        current_cad_count = self._cfg.get("cad_point_count", 10000)

        # Form düzeni
        form = QtWidgets.QFormLayout(self)

        # ── Tema Seçimi
        grp_theme = QtWidgets.QGroupBox("Tema")
        hbox_theme = QtWidgets.QHBoxLayout(grp_theme)
        self.rb_dark = QtWidgets.QRadioButton("Dark")
        self.rb_light = QtWidgets.QRadioButton("Light")
        hbox_theme.addWidget(self.rb_dark)
        hbox_theme.addWidget(self.rb_light)
        self.rb_dark.setChecked(current_theme == "dark")
        self.rb_light.setChecked(current_theme == "light")
        self.rb_dark.toggled.connect(self._on_theme_toggle)
        form.addRow(grp_theme)

        # ── Algoritma Ayarları
        grp_algo = QtWidgets.QGroupBox("Algoritma Ayarları")
        vbox_algo = QtWidgets.QVBoxLayout(grp_algo)
        # CAD Point Sayısı
        self.spin_cad_count = QtWidgets.QSpinBox()
        self.spin_cad_count.setRange(1, 10_000_000)
        self.spin_cad_count.setValue(current_cad_count)
        self.spin_cad_count.valueChanged.connect(self._on_cad_count_changed)
        vbox_algo.addWidget(QtWidgets.QLabel("CAD point sayısı:"))
        vbox_algo.addWidget(self.spin_cad_count)
        form.addRow(grp_algo)

        # ── Kaydet Butonu
        self.btn_save = QtWidgets.QPushButton("Kaydet")
        self.btn_save.clicked.connect(self._on_save_clicked)
        form.addRow(self.btn_save)

    # ───────────────────────── internal
    def _on_theme_toggle(self):
        # Geçici olarak config güncelle
        theme = "dark" if self.rb_dark.isChecked() else "light"
        self._cfg["theme"] = theme
        self.theme_changed.emit(theme)

    def _on_cad_count_changed(self, value: int):
        # Geçici olarak config güncelle
        self._cfg["cad_point_count"] = value
        self.cad_point_count_changed.emit(value)

    def _on_save_clicked(self):
        # Tüm ayarları kaydet
        save(self._cfg)
        QtWidgets.QMessageBox.information(self, "Kaydedildi", "Ayarlar başarıyla kaydedildi.")
