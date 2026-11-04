# Converts logo.png (any size) into logo.ico (256x256, square) using PySide6.
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter

root = Path(__file__).resolve().parent.parent
src = root / "logo.png"
dst = root / "logo.ico"

app = QGuiApplication([])
image = QImage(str(src))
if image.isNull():
    print("make_icon: cannot read logo.png")
    sys.exit(1)

size = 256
scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
canvas = QImage(size, size, QImage.Format_ARGB32)
canvas.fill(Qt.transparent)
painter = QPainter(canvas)
painter.drawImage((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
painter.end()

if not canvas.save(str(dst), "ICO"):
    print("make_icon: cannot write logo.ico")
    sys.exit(1)
print("make_icon: logo.ico created")
