import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt5.QtWidgets import QApplication
from ui.hologram import JarvisUI

app = QApplication(sys.argv)
ui = JarvisUI()
ui.show()
sys.exit(app.exec_())
