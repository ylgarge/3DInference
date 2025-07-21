from PyQt5 import QtGui
from gui.config.config_util import save, load

def apply(app, theme: str):
    if theme == "dark":
        _apply_dark(app)
    else:
        _apply_light(app)
    # ▶ evrensel font rengi ayarı (light’ta Qt varsayılanı iyi çalışıyor)
    app.setStyleSheet("""
        QLabel{ color: %s; }
    """ % ("#e6e6e6" if theme=="dark" else "#000000"))

def _apply_dark(app):
    pal = QtGui.QPalette()
    pal.setColor(pal.Window,          QtGui.QColor(45,45,45))
    pal.setColor(pal.WindowText,      QtGui.QColor(230,230,230))
    pal.setColor(pal.Base,            QtGui.QColor(30,30,30))
    pal.setColor(pal.ToolTipBase,     QtGui.QColor(255,255,255))
    pal.setColor(pal.ToolTipText,     QtGui.QColor(0,0,0))
    pal.setColor(pal.Text,            QtGui.QColor(230,230,230))
    pal.setColor(pal.Button,          QtGui.QColor(60,60,60))
    pal.setColor(pal.ButtonText,      QtGui.QColor(230,230,230))
    pal.setColor(pal.Highlight,       QtGui.QColor(38,79,120))
    pal.setColor(pal.HighlightedText, QtGui.QColor(255,255,255))
    app.setPalette(pal)

def _apply_light(app):
    app.setPalette(app.style().standardPalette())
