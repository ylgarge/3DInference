# ─── viewer.py ────────────────────────────────────────────────────────────────
import numpy as np
from PyQt5 import QtCore
from pyqtgraph.opengl import GLViewWidget, GLScatterPlotItem

class PointCloudViewer(GLViewWidget):
    """Tiny wrapper that shows a coloured 3-D point cloud."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor('#333333')
        self.opts['distance'] = 2           # initial zoom-out
        self._scatter = None

    def set_points(self, pts: np.ndarray, colors=None, size=3.0):
        """pts -> (N,3) float32 array in **metres**, colours -> (N,4) 0-255 uint8."""
        if self._scatter:
            self.removeItem(self._scatter)
        if colors is None:
            colors = np.tile(np.array([0, 170, 255, 100], dtype=np.ubyte), (pts.shape[0], 1))
        self._scatter = GLScatterPlotItem(pos=pts, color=colors, size=size, pxMode=False)
        self.addItem(self._scatter)
        self._auto_scale(pts)

    def _auto_scale(self, pts):
        """Centre the view and fit zoom to data extents."""
        center = pts.mean(axis=0)
        self.opts['center'] = QtCore.QVector3D(*center)
        mx = (pts.max(axis=0) - pts.min(axis=0)).max()
        self.opts['distance'] = mx * 2 if mx > 0 else 1
