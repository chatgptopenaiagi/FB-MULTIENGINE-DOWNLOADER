"""Exercise source GUI widgets and save a screenshot without a global desktop capture."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtWidgets import QApplication
from fbmd.gui import Window, STYLE

root = Path(__file__).resolve().parents[1]
app = QApplication([])
app.setStyleSheet(STYLE)
window = Window(root / ".private/gui-probe", root / ".private/gui-media")
window.show()
app.processEvents()
for i in range(10):
    window.nav.setCurrentRow(i)
    app.processEvents()
window.nav.setCurrentRow(0)
window.urls.setPlainText(
    "https://www.facebook.com/profile.php?id=61595152335606&sk=reels_tab"
)
app.processEvents()
window.grab().save(str(root / "evidence/windows-source-ui.png"))
print("GUI_10_SCREENS_RENDERED")
window.close()
