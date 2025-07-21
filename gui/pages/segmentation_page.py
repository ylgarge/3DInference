import os
import sys
import numpy as np

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

import open3d as o3d
import matplotlib.cm as cm

from vispy import scene
from vispy.scene import visuals

from gui.config.segmetation_config import (
    load_segmentation_config,
    save_segmentation_config,
)

# ------------------------------------------------------------
#  Worker Thread for Segmentation
# ------------------------------------------------------------
class SegmentationWorker(QThread):
    result_ready = pyqtSignal(np.ndarray, np.ndarray, int)
    error = pyqtSignal(str)

    def __init__(self, pcd, dist_thresh, num_iter, eps, min_pts):
        super().__init__()
        self.pcd = pcd
        self.dist_thresh = dist_thresh
        self.num_iter = num_iter
        self.eps = eps
        self.min_pts = min_pts

    def run(self):
        try:
            # 1) RANSAC Plane Segmentation
            plane_model, inliers = self.pcd.segment_plane(
                distance_threshold=self.dist_thresh,
                ransac_n=3,
                num_iterations=self.num_iter
            )
            ground = self.pcd.select_by_index(inliers)
            objects = self.pcd.select_by_index(inliers, invert=True)

            # 2) DBSCAN Clustering
            labels = np.array(objects.cluster_dbscan(
                eps=self.eps,
                min_points=self.min_pts,
                print_progress=False
            ))
            

            max_label = labels.max()

            if max_label < 0:
                objects.paint_uniform_color([1, 0, 0])
            else:
                cmap = cm.get_cmap("tab20", max(20, max_label + 1))
                colors = np.zeros((labels.shape[0], 3))
                for i in range(max_label + 1):
                    colors[labels == i] = cmap(i)[:3]
                objects.colors = o3d.utility.Vector3dVector(colors)

            ground.paint_uniform_color([0.5, 0.5, 0.5])
            combined = ground + objects

            # Prepare data for visualization
            pts_comb = np.asarray(combined.points, dtype=np.float32)
            cols_comb = None
            if combined.has_colors():
                cols = np.asarray(combined.colors, dtype=np.float32)
                if cols.shape[1] == 3:
                    alpha = np.ones((cols.shape[0], 1), dtype=np.float32)
                    cols = np.hstack([cols, alpha])
                cols_comb = cols

            self.result_ready.emit(pts_comb, cols_comb, len(pts_comb))
        except Exception as e:
            self.error.emit(str(e))


# ------------------------------------------------------------
#  VisPyCanvas
# ------------------------------------------------------------
class VisPyCanvas(scene.SceneCanvas):
    def __init__(self, parent=None):
        super().__init__(keys=None, parent=parent, bgcolor="black")
        self.unfreeze()
        self.view = self.central_widget.add_view()
        self.view.camera = scene.cameras.ArcballCamera(fov=60.0)
        self.markers = visuals.Markers()
        self.view.add(self.markers)
        self.freeze()

    def set_points(self, points: np.ndarray, colors: np.ndarray = None):
        if colors is None:
            colors = (0.3, 0.6, 1.0, 1.0)
        self.markers.set_data(
            points,
            edge_width=0.0,
            face_color=colors,
            size=2.0
        )
        if points.size > 0:
            self.view.camera.set_range(
                x=(points[:, 0].min(), points[:, 0].max()),
                y=(points[:, 1].min(), points[:, 1].max()),
                z=(points[:, 2].min(), points[:, 2].max()),
            )


# ------------------------------------------------------------
#  VisPyWidget
# ------------------------------------------------------------
class VisPyWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = VisPyCanvas(parent=self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas.native)

    def set_points(self, points: np.ndarray, colors: np.ndarray = None):
        self.canvas.set_points(points, colors)


# ------------------------------------------------------------
#  SegmentationPage with QThread support
# ------------------------------------------------------------
class SegmentationPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Load config
        self._config = load_segmentation_config()
        self._worker = None

        # Main layout
        main_lay = QtWidgets.QHBoxLayout(self)
        self.setLayout(main_lay)

        # Left: Viewers
        left_vlayout = QtWidgets.QVBoxLayout()
        main_lay.addLayout(left_vlayout, stretch=1)

        # Original point cloud
        self._viewer_original = VisPyWidget()
        self._viewer_original.setMinimumSize(600, 300)
        left_vlayout.addWidget(QtWidgets.QLabel("Orijinal Nokta Bulutu:"))
        left_vlayout.addWidget(self._viewer_original, stretch=1)

        # Segmented result
        self._viewer_segmented = VisPyWidget()
        self._viewer_segmented.setMinimumSize(600, 300)
        left_vlayout.addWidget(QtWidgets.QLabel("Segmentasyon Sonucu:"))
        left_vlayout.addWidget(self._viewer_segmented, stretch=1)

        # Right: Controls
        side_panel = QtWidgets.QVBoxLayout()
        side_panel.setSpacing(10)
        main_lay.addLayout(side_panel, stretch=0)

        # Mode button
        initial_mode = self._config.get("source_mode", "offline")
        self._btn_mode = QtWidgets.QPushButton()
        self._btn_mode.setFixedHeight(40)
        self._btn_mode.clicked.connect(self._on_mode_button_clicked)
        side_panel.addWidget(self._btn_mode)
        self._set_mode(initial_mode)

        # Algorithm selection
        alg_box = QtWidgets.QHBoxLayout()
        alg_label = QtWidgets.QLabel("Algoritma:")
        self._alg_combo = QtWidgets.QComboBox()
        self._alg_combo.addItems(["RANSAC", "SAM3D"])
        self._alg_combo.setCurrentText(self._config.get("algorithm", "RANSAC"))
        alg_box.addWidget(alg_label)
        alg_box.addWidget(self._alg_combo)
        side_panel.addLayout(alg_box)

        # RANSAC/DBSCAN parameters
        self._ransac_group = QtWidgets.QGroupBox("RANSAC Parametreleri")
        form = QtWidgets.QFormLayout(self._ransac_group)

        self._dist_threshold = QtWidgets.QDoubleSpinBox()
        self._dist_threshold.setRange(0.0, 9999.0)
        self._dist_threshold.setSingleStep(0.01)
        self._dist_threshold.setValue(
            self._config["ransac_params"].get("distance_threshold", 0.1)
        )

        self._num_iter = QtWidgets.QSpinBox()
        self._num_iter.setRange(1, 999999)
        self._num_iter.setValue(
            self._config["ransac_params"].get("num_iterations", 1000)
        )

        self._eps = QtWidgets.QDoubleSpinBox()
        self._eps.setRange(0.0, 9999.0)
        self._eps.setSingleStep(0.01)
        self._eps.setValue(
            self._config["ransac_params"].get("eps", 0.02)
        )

        self._min_points = QtWidgets.QSpinBox()
        self._min_points.setRange(1, 999999)
        self._min_points.setValue(
            self._config["ransac_params"].get("min_points", 40)
        )

        form.addRow("RANSAC distance_threshold:", self._dist_threshold)
        form.addRow("RANSAC num_iterations:", self._num_iter)
        form.addRow("DBSCAN eps:", self._eps)
        form.addRow("DBSCAN min_points:", self._min_points)
        side_panel.addWidget(self._ransac_group)

        self._alg_combo.currentTextChanged.connect(self._on_algorithm_changed)
        self._on_algorithm_changed(self._alg_combo.currentText())

        # Segment button
        self._btn_segment = QtWidgets.QPushButton("Segmentasyon Başlat")
        self._btn_segment.setStyleSheet("background-color: #2e7d32; color: white;")
        self._btn_segment.clicked.connect(self._on_segment_button_clicked)
        side_panel.addWidget(self._btn_segment)

        # Save config
        save_btn = QtWidgets.QPushButton("Ayarları Kaydet")
        save_btn.clicked.connect(self._save_config)
        side_panel.addWidget(save_btn)
        side_panel.addStretch()

        # State
        self._segment_in_progress = False
        self._current_pcd = None

    # ------------------- Offline/Online toggle
    def _on_mode_button_clicked(self):
        current_mode = self._config.get("source_mode", "offline")
        if current_mode == "online":
            QMessageBox.information(self, "Zaten Online", "Kamera bağlı.")
            return

        if self._connect_camera():
            self._set_mode("online")
        else:
            QMessageBox.warning(self, "Kamera Hatası", "Kamera bağlanamadı, offline modda kaldı.")
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "PLY Dosyası Seç", os.getcwd(), "PLY Files (*.ply)"
            )
            if file_path:
                self._config["ply_file_path"] = file_path
                self._load_ply_in_viewer(file_path)

    def _set_mode(self, mode: str):
        self._config["source_mode"] = mode
        if mode == "offline":
            self._btn_mode.setText("Offline")
            self._btn_mode.setStyleSheet("background-color:#c62828; color:white;")
        else:
            self._btn_mode.setText("Online")
            self._btn_mode.setStyleSheet("background-color:#2e7d32; color:white;")

    def _connect_camera(self) -> bool:
        return False

    # ------------------- PLY yükle
    def _load_ply_in_viewer(self, file_path: str):
        pc = o3d.io.read_point_cloud(file_path)
        pts = np.asarray(pc.points, dtype=np.float32)

        cols = None
        if pc.has_colors():
            cols = np.asarray(pc.colors, dtype=np.float32)
            if cols.shape[1] == 3:
                alpha_col = np.ones((cols.shape[0], 1), dtype=np.float32)
                cols = np.hstack([cols, alpha_col])

        self._viewer_original.set_points(pts, colors=cols)
        self._viewer_segmented.set_points(np.zeros((0, 3), dtype=np.float32))
        self._current_pcd = pc

    # ------------------- Segment button handler
    def _on_segment_button_clicked(self):
        if self._worker is None or not self._worker.isRunning():
            # Start segmentation
            if not self._current_pcd:
                QMessageBox.warning(self, "Hata", "Önce bir nokta bulutu yüklemelisiniz.")
                return

            dt = self._dist_threshold.value()
            ni = self._num_iter.value()
            eps = self._eps.value()
            mp = self._min_points.value()

            self._worker = SegmentationWorker(self._current_pcd, dt, ni, eps, mp)
            self._worker.result_ready.connect(self._on_segmentation_finished)
            self._worker.error.connect(self._on_segmentation_error)
            self._worker.finished.connect(self._cleanup_after_seg)

            QApplication.setOverrideCursor(Qt.WaitCursor)
            self._btn_segment.setText("İptal Et")
            self._btn_segment.setStyleSheet("background-color:#c62828;color:white;")

            self._worker.start()
        else:
            # Cancel ongoing segmentation
            reply = QMessageBox.question(
                self, "İptal?", "Segmentasyonu iptal etmek istiyor musunuz?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._worker.terminate()

    def _on_segmentation_finished(self, pts, cols, count):
        self._viewer_segmented.set_points(pts, colors=cols)
        QMessageBox.information(self, "Tamamlandı",
                                f"Segmentasyon tamamlandı. {count} nokta!")

    def _on_segmentation_error(self, msg):
        QMessageBox.warning(self, "Hata", f"Segmentasyon sırasında hata: {msg}")

    def _cleanup_after_seg(self):
        QApplication.restoreOverrideCursor()
        self._btn_segment.setText("Segmentasyon Başlat")
        self._btn_segment.setStyleSheet("background-color:#2e7d32;color:white;")
        self._worker = None

    def _on_algorithm_changed(self, alg: str):
        self._ransac_group.setVisible(alg == "RANSAC")

    def _save_config(self):
        self._config["algorithm"] = self._alg_combo.currentText()
        self._config["ransac_params"]["distance_threshold"] = self._dist_threshold.value()
        self._config["ransac_params"]["num_iterations"] = self._num_iter.value()
        self._config["ransac_params"]["eps"] = self._eps.value()
        self._config["ransac_params"]["min_points"] = self._min_points.value()

        save_segmentation_config(self._config)
        QMessageBox.information(self, "Kaydedildi", "Segmentation ayarları kaydedildi.")

# ------------------------------------------------------------
#  Test
# ------------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = SegmentationPage()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec_())
