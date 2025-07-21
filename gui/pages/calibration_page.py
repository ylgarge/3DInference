from PyQt5 import QtWidgets, QtCore
class CalibrationPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Calibration settings (TODO)",
                                       alignment=QtCore.Qt.AlignCenter))
