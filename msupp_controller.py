import json
import os
import shutil
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal, Property
from PySide6.QtWidgets import QFileDialog
from typing import Any
from PySide6.QtWidgets import QFileDialog

from app_paths import user_data_dir

from msup_tunnels_extractor import MsupTunnelsWatcher

class MSuppController(QObject):
    basesChanged = Signal()
    tunnelsExtracted = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bases = []
        self._save_path = user_data_dir() / "msupp_bases.json"
        self._img_dir = user_data_dir() / "msupp_images"
        self._img_dir.mkdir(parents=True, exist_ok=True)
        self.load_bases()
        
        self.tunnelsExtracted.connect(self.on_tunnels_extracted)
        self._watcher = MsupTunnelsWatcher(
            tunnels_callback=lambda tunnels: self.tunnelsExtracted.emit(tunnels)
        )
        self._watcher.start()

    def load_bases(self):
        if self._save_path.exists():
            try:
                with open(self._save_path, "r", encoding="utf-8") as f:
                    self._bases = json.load(f)
            except Exception:
                self._bases = []
        else:
            self._bases = []
        self.basesChanged.emit()

    def save_bases(self):
        try:
            with open(self._save_path, "w", encoding="utf-8") as f:
                json.dump(self._bases, f, indent=2)
        except Exception as e:
            print("Failed to save msupp bases:", e)

    @Slot(str, int, int, str)
    def add_base(self, name: str, hourly_rate: int, current_stock: int, image_path: str):
        saved_image_path = ""
        if image_path and image_path.startswith("file:///"):
            image_path = image_path[8:]
        if image_path and os.path.exists(image_path):
            filename = os.path.basename(image_path)
            dest_path = self._img_dir / f"{len(self._bases)}_{filename}"
            try:
                shutil.copy2(image_path, dest_path)
                saved_image_path = "file:///" + str(dest_path).replace("\\", "/")
            except Exception:
                pass

        self._bases.append({
            "name": name,
            "hourly_rate": hourly_rate,
            "current_stock": current_stock,
            "image_path": saved_image_path
        })
        self.save_bases()
        self.basesChanged.emit()

    @Slot(int)
    def remove_base(self, index: int):
        if 0 <= index < len(self._bases):
            self._bases.pop(index)
            self.save_bases()
            self.basesChanged.emit()

    @Slot(result=str)
    def pick_image(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Selecione a foto do mapa",
            "",
            "Images (*.png *.xpm *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            return "file:///" + file_path.replace("\\", "/")
        return ""

    @Property("QVariantList", notify=basesChanged)
    def bases(self):
        return self._bases

    @Slot(object)
    def on_tunnels_extracted(self, tunnels: list[dict[str, Any]]):
        changed = False
        for tunnel in tunnels:
            map_id = tunnel.get("map_id")
            msupps = tunnel.get("msupps", 0)
            if not map_id:
                continue
            
            for base in self._bases:
                if base.get("name") == map_id:
                    if base.get("current_stock") != msupps:
                        base["current_stock"] = msupps
                        changed = True
        if changed:
            self.save_bases()
            self.basesChanged.emit()

    def shutdown(self):
        if hasattr(self, '_watcher') and self._watcher:
            self._watcher.stop()

