from PyQt5 import QtWidgets, QtCore
class AccountPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Hesap bilgileri (TODO)",
                                       alignment=QtCore.Qt.AlignCenter))
