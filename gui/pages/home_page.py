#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyQt5 + VisPy GUI
– Screen / CAD / Segmentation / Matching pencereleri
– Eşleştir butonu: ICP-tabanlı segment hizalama ve görselleştirme
"""

import sys, os, json, copy
from pathlib import Path

import numpy as np
import open3d as o3d

from PyQt5 import QtWidgets, QtCore
from vispy import scene
from vispy.scene import visuals
from matplotlib import cm

# ------------------------------------------------------
# 0) Ayarlar
# ------------------------------------------------------
settings_path = Path("config/settings.json")
if settings_path.exists():
    with open(settings_path, "r") as sf:
        settings = json.load(sf)
    cad_point_count = settings.get("cad_point_count", 10000)
else:
    cad_point_count = 10000

CACHE_DIR = Path("dataset/STLtoPoint")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def ensure_point_cloud(path: Path, n_pts: int) -> o3d.geometry.PointCloud:
    cache_file = CACHE_DIR / f"{path.stem}_{n_pts}pts.ply"
    if cache_file.exists():
        return o3d.io.read_point_cloud(str(cache_file))

    if path.suffix.lower() == ".ply":
        pcd = o3d.io.read_point_cloud(str(path))
    elif path.suffix.lower() == ".stl":
        mesh = o3d.io.read_triangle_mesh(str(path))
        if not mesh.has_vertex_normals():
            mesh.compute_vertex_normals()
        pcd = mesh.sample_points_poisson_disk(n_pts)
        o3d.io.write_point_cloud(str(cache_file), pcd)
    else:
        raise ValueError(f"Desteklenmeyen uzantı: {path.suffix}")
    return pcd

# ------------------------------------------------------
# 1) VisPyCanvas
# ------------------------------------------------------
class VisPyCanvas(scene.SceneCanvas):
    def __init__(self, parent=None):
        super().__init__(keys=None, parent=parent, bgcolor="black")
        self.unfreeze()
        self.view = self.central_widget.add_view()
        self.view.camera = scene.cameras.ArcballCamera(fov=60.0)
        self.markers = visuals.Markers()
        self.view.add(self.markers)
        self.freeze()

    def set_points(self, pts: np.ndarray, colors=None, size=3.0):
        if pts.size == 0:
            return
        if colors is None:
            colors = np.tile([0.3, 0.6, 1.0, 1.0], (pts.shape[0], 1))
        self.markers.set_data(pts, edge_width=0.0, face_color=colors, size=size)
        self.view.camera.set_range(
            x=(pts[:, 0].min(), pts[:, 0].max()),
            y=(pts[:, 1].min(), pts[:, 1].max()),
            z=(pts[:, 2].min(), pts[:, 2].max()),
        )

# ------------------------------------------------------
# 2) Yardımcı hizalama fonksiyonları
# ------------------------------------------------------
def diagonal(pc: o3d.geometry.PointCloud) -> float:
    aabb = pc.get_axis_aligned_bounding_box()
    return np.linalg.norm(aabb.get_max_bound() - aabb.get_min_bound())

def preprocess(pc: o3d.geometry.PointCloud, voxel: float):
    down = pc.voxel_down_sample(voxel)
    down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=4 * voxel, max_nn=50)
    )
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=6 * voxel, max_nn=200),
    )
    return down, fpfh

def global_reg(src_d, tgt_d, src_f, tgt_f, dist):
    return o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        src_d,
        tgt_d,
        src_f,
        tgt_f,
        mutual_filter=False,
        max_correspondence_distance=dist,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        ransac_n=4,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(dist),
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(50000, 1000),
    )

# Segmentasyon parametreleri (gerekirse düzenleyin)
VOXEL_SZ  = 0.002
PLANE_EPS = 0.422
DB_EPS_1, DB_PTS_1 = 0.025, 120
DB_EPS_2, DB_PTS_2 = 0.015, 20
FACTOR = 0.00068                 # ← parça ölçek faktörü

def segment_cloud(pcd: o3d.geometry.PointCloud):
    pcd_ds = pcd.voxel_down_sample(VOXEL_SZ)
    pcd_ds, _ = pcd_ds.remove_statistical_outlier(nb_neighbors=30, std_ratio=2.0)

    _, inliers = pcd_ds.segment_plane(
        distance_threshold=PLANE_EPS, ransac_n=3, num_iterations=5000
    )
    ground  = pcd_ds.select_by_index(inliers)
    objects = pcd_ds.select_by_index(inliers, invert=True)

    lbl1 = np.array(objects.cluster_dbscan(
        eps=DB_EPS_1, min_points=DB_PTS_1, print_progress=False))
    cmap = cm.get_cmap("tab20", max(20, lbl1.max() + 1))

    raw_parts, colored_parts = [], []
    for l1 in range(lbl1.max() + 1):
        sub = objects.select_by_index(np.where(lbl1 == l1)[0])

        lbl2 = np.array(sub.cluster_dbscan(
            eps=DB_EPS_2, min_points=DB_PTS_2, print_progress=False))

        for l2 in range(lbl2.max() + 1):
            part_raw = sub.select_by_index(np.where(lbl2 == l2)[0])
            raw_parts.append(part_raw)

            color = cmap(len(colored_parts))[:3]
            colored_parts.append(copy.deepcopy(part_raw).paint_uniform_color(color))

    ground.paint_uniform_color([0.6, 0.6, 0.6])
    return ground, raw_parts, colored_parts

def align_part_to_segment(part_orig: o3d.geometry.PointCloud,
                          segment:   o3d.geometry.PointCloud):
    seg_diag = diagonal(segment)
    if seg_diag == 0:
        return None, 0, np.inf

    part = copy.deepcopy(part_orig)
    part.translate(segment.get_center() - part.get_center(), relative=True)

    voxel = 0.01 * seg_diag
    src_d, src_f = preprocess(part, voxel)
    tgt_d, tgt_f = preprocess(segment, voxel)

    r = global_reg(src_d, tgt_d, src_f, tgt_f, 1.5 * voxel)
    icp = o3d.pipelines.registration.registration_icp(
        part,
        segment,
        max_correspondence_distance=voxel,
        init=r.transformation,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        criteria=o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=50),
    )

    part_aligned = copy.deepcopy(part)
    part_aligned.transform(icp.transformation)
    return part_aligned, icp.fitness, icp.inlier_rmse

# ------------------------------------------------------
# 3) HomePage
# ------------------------------------------------------
COLORS = {
    "Screen 3D Point Cloud":    "#868686",
    "CAD → Point Cloud":        "#4654d9",
    "Segmentation Point Cloud": "#3aa650",
    "Eşleştirme Point Cloud":   "#a3862d",
}

class HomePage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Point Cloud Viewer")
        self.resize(1200, 800)

        mainLayout = QtWidgets.QHBoxLayout(self)

        # ── 2×2 kutular
        leftWidget = QtWidgets.QWidget()
        leftGrid   = QtWidgets.QGridLayout(leftWidget)
        leftGrid.setSpacing(6)
        for i in range(2):
            leftGrid.setColumnStretch(i, 1)
            leftGrid.setRowStretch(i, 1)

        titles = list(COLORS.keys())
        self.screenFrame, self.screenBody = self.box(titles[0])
        self.cadFrame,    self.cadBody    = self.box(titles[1])
        self.segFrame,    self.segBody    = self.box(titles[2])
        self.matchFrame,  self.matchBody  = self.box(titles[3])

        leftGrid.addWidget(self.screenFrame, 0, 0)
        leftGrid.addWidget(self.cadFrame,    0, 1)
        leftGrid.addWidget(self.segFrame,    1, 0)
        leftGrid.addWidget(self.matchFrame,  1, 1)
        mainLayout.addWidget(leftWidget, 6)

        # ── Sağ panel
        rightWidget = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(rightWidget)
        vbox.setContentsMargins(5, 5, 5, 5)
        vbox.setSpacing(10)

        self.cameraButton = QtWidgets.QPushButton("Offline")
        self.cameraButton.setStyleSheet(
            "background-color: red; color: white; font-weight: bold;"
        )
        self.cameraButton.clicked.connect(self.handleCameraConnection)
        vbox.addWidget(self.cameraButton)

        self.segmentButton = QtWidgets.QPushButton("Segmentasyon")
        self.segmentButton.clicked.connect(self.handleSegmentation)
        vbox.addWidget(self.segmentButton)

        self.eslestirButton = QtWidgets.QPushButton("Eşleştir")
        self.eslestirButton.clicked.connect(self.handleMatching)
        vbox.addWidget(self.eslestirButton)

        self.cadLabel = QtWidgets.QLabel("CAD Dosyaları")
        self.cadLabel.setStyleSheet("font-weight: bold;")
        vbox.addWidget(self.cadLabel)

        self.cadList = QtWidgets.QListWidget()
        self.loadStlFiles("dataset/part")
        self.cadList.itemClicked.connect(self.handleCadSelection)
        vbox.addWidget(self.cadList, 1)

        mainLayout.addWidget(rightWidget, 1)

        # ── Canvas'lar
        self.screenCanvas = VisPyCanvas(self)
        self.screenBody.addWidget(self.screenCanvas.native)

        self.cadCanvas = VisPyCanvas(self)
        self.cadBody.addWidget(self.cadCanvas.native)

        self.segCanvas = VisPyCanvas(self)
        self.segBody.addWidget(self.segCanvas.native)

        self.matchCanvas = VisPyCanvas(self)
        self.matchBody.addWidget(self.matchCanvas.native)

    # ───────────────────────── UI yardımcıları ──────────────────
    def box(self, title: str):
        frame = QtWidgets.QFrame()
        vbox  = QtWidgets.QVBoxLayout(frame)
        vbox.setContentsMargins(0, 0, 0, 0)

        header = QtWidgets.QLabel(title)
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setStyleSheet(
            f"background:{COLORS[title]}; color:white; padding:2px; "
            "font-weight:bold; border-top-left-radius:4px; border-top-right-radius:4px;"
        )
        body = QtWidgets.QWidget()
        body.setStyleSheet(
            "border:2px solid #666; border-top:none; "
            "border-bottom-left-radius:4px; border-bottom-right-radius:4px;"
        )
        bodyLayout = QtWidgets.QVBoxLayout(body)
        bodyLayout.setContentsMargins(5, 5, 5, 5)

        vbox.addWidget(header)
        vbox.addWidget(body, 1)
        return frame, bodyLayout

    # ───────────────────────── Olaylar ──────────────────────────
    def handleCameraConnection(self):
        QtWidgets.QMessageBox.warning(
            self,
            "Kamera Bağlantısı",
            "Kameraya bağlanılamadı, lütfen .ply dosyası seçin.",
        )
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Ply dosyası seç", "", "PLY Files (*.ply)"
        )
        if fn:
            self.load_ply_and_display(fn)

    def loadStlFiles(self, directory):
        if os.path.isdir(directory):
            for fn in os.listdir(directory):
                if fn.lower().endswith(".stl"):
                    self.cadList.addItem(fn)

    def load_ply_and_display(self, ply_path):
        pcd = o3d.io.read_point_cloud(str(ply_path))
        self.current_pcd = pcd
        pts = np.asarray(pcd.points)
        cols = (
            np.hstack([np.asarray(pcd.colors), np.ones((len(pcd.points), 1))])
            if pcd.colors
            else None
        )
        self.screenCanvas.set_points(pts, cols)

    def handleCadSelection(self, item: QtWidgets.QListWidgetItem):
        stl_path = Path("dataset/part") / item.text()
        pcd = ensure_point_cloud(stl_path, cad_point_count)
        self.current_cad_pcd = pcd
        pts = np.asarray(pcd.points)
        cols = (
            np.hstack([np.asarray(pcd.colors), np.ones((len(pcd.points), 1))])
            if pcd.colors
            else None
        )
        self.cadCanvas.set_points(pts, cols)

    # ───────────────────── Segmentasyon Butonu ──────────────────
    def handleSegmentation(self):
        if not hasattr(self, "current_pcd"):
            QtWidgets.QMessageBox.warning(self, "Segmentasyon", "Önce .ply yükleyin.")
            return

        ground, raw_parts, colored_parts = segment_cloud(self.current_pcd)

        pts  = np.concatenate(
            [np.asarray(ground.points)] + [np.asarray(p.points) for p in colored_parts]
        )
        cols = np.concatenate(
            [np.tile([0.5, 0.5, 0.5, 1.0], (len(ground.points), 1))]
            + [
                np.tile(list(p.colors[0]) + [1.0], (len(p.points), 1))
                for p in colored_parts
            ]
        )
        self.segCanvas.set_points(pts, cols)

    # ───────────────────── Eşleştir Butonu ──────────────────────
    def handleMatching(self):
        if not hasattr(self, "current_pcd") or not hasattr(self, "current_cad_pcd"):
            QtWidgets.QMessageBox.warning(
                self, "Eşleştirme", "Önce hem Screen hem de CAD verisi yükleyin."
            )
            return

        # 1) Kopyalar & ölçek
        ref_pc = copy.deepcopy(self.current_pcd)
        tgt_pc = copy.deepcopy(self.current_cad_pcd)
        tgt_pc.scale(FACTOR, center=tgt_pc.get_center())

        # 2) Segmentasyon
        _, raw_parts, _ = segment_cloud(ref_pc)
        if not raw_parts:
            QtWidgets.QMessageBox.warning(self, "Eşleştirme", "Parça bulunamadı.")
            return

        # 3) Her segmente hizala, en iyisini seç
        best_fit, best_rmse, best_aligned = -1, np.inf, None
        for seg in raw_parts:
            aligned, fit, rmse = align_part_to_segment(tgt_pc, seg)
            if aligned is None:
                continue
            if fit > best_fit or (fit == best_fit and rmse < best_rmse):
                best_fit, best_rmse, best_aligned = fit, rmse, aligned

        if best_aligned is None:
            QtWidgets.QMessageBox.warning(self, "Eşleştirme", "Hizalama başarısız.")
            return

        # 4) Ekranda göster (ref gri, hizalanan kırmızı)
        ref_pts  = np.asarray(ref_pc.points)
        ref_cols = np.tile([0.4, 0.4, 0.4, 1.0], (len(ref_pts), 1))
        best_aligned.paint_uniform_color([1.0, 0.0, 0.0])
        tgt_pts  = np.asarray(best_aligned.points)
        tgt_cols = np.tile([1.0, 0.0, 0.0, 1.0], (len(tgt_pts), 1))

        self.matchCanvas.set_points(
            np.vstack([ref_pts, tgt_pts]), np.vstack([ref_cols, tgt_cols])
        )

        QtWidgets.QMessageBox.information(
            self,
            "Eşleştirme Tamam",
            f"En iyi fitness: {best_fit:.3f}   RMSE: {best_rmse:.6f}",
        )

# ------------------------------------------------------
# 4) Uygulama
# ------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = HomePage()
    win.show()
    sys.exit(app.exec_())
