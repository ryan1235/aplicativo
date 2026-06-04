from __future__ import annotations

import ctypes
from datetime import datetime
from pathlib import Path
import traceback
import tkinter as tk
from tkinter import filedialog, ttk

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover
    ctk = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

from i18n import Translator

try:
    from PIL import Image, ImageEnhance, ImageGrab, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageEnhance = None
    ImageGrab = None
    ImageTk = None


COLORS = {
    "bg": "#070b16",
    "card": "#111c31",
    "soft": "#0e1a2d",
    "line": "#2d496f",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
}


def widget_color(widget, fallback: str) -> str:
    if ctk is not None:
        try:
            color = widget.cget("fg_color")
            if isinstance(color, tuple): return color[-1]
            return color
        except Exception: return fallback
    return widget.cget("bg")

def modern_frame(parent, color: str, radius: int = 16, border: int = 0, border_color: str | None = None):
    if ctk is not None:
        return ctk.CTkFrame(parent, fg_color=color, corner_radius=radius, border_width=border, border_color=border_color or color)
    return tk.Frame(parent, bg=color, highlightthickness=border, highlightbackground=border_color or color)

def modern_option_menu(parent, variable, values: list[str], width: int = 120, command=None):
    if ctk is not None:
        bg = widget_color(parent, COLORS.get("card", "#111c31"))
        menu = ctk.CTkOptionMenu(
            parent, variable=variable, values=values, width=width, height=30,
            bg_color=bg, fg_color=COLORS.get("soft", "#0e1a2d"),
            button_color=COLORS.get("soft", "#0e1a2d"), button_hover_color=COLORS.get("card_2", "#1d3353"),
            dropdown_fg_color=COLORS.get("card", "#111c31"), dropdown_hover_color=COLORS.get("card_2", "#1d3353"),
            dropdown_text_color=COLORS.get("text", "#edf6ff"), text_color=COLORS.get("text", "#edf6ff"),
            font=("Segoe UI", 11, "bold"), dropdown_font=("Segoe UI", 11), corner_radius=6, command=command
        )
        def custom_open():
            current_values = menu._values
            if not current_values:
                return
            top = tk.Toplevel(parent)
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            top.configure(bg=COLORS.get("line", "#2d496f"))
            x = menu.winfo_rootx()
            y = menu.winfo_rooty() + menu.winfo_height() + 2
            w = menu.winfo_width()
            max_items = min(len(current_values), 8)
            item_height = 28
            h = max_items * item_height + 2
            top.geometry(f"{w}x{h}+{x}+{y}")
            original_rooty = menu.winfo_rooty()
            def check_position():
                if not top.winfo_exists(): return
                try:
                    if menu.winfo_rooty() != original_rooty:
                        top.destroy()
                        return
                except tk.TclError:
                    pass
                top.after(50, check_position)
            top.after(50, check_position)
            
            max_items = min(len(current_values), 8)
            item_height = 25
            h = max_items * item_height + 4
            top.geometry(f"{w}x{h}+{x}+{y}")
            
            frame = tk.Frame(top, bg=COLORS.get("card", "#111c31"))
            frame.pack(fill="both", expand=True, padx=1, pady=1)
            
            scrollbar = tk.Scrollbar(frame, orient="vertical")
            lb = tk.Listbox(frame, bg=COLORS.get("card", "#111c31"), fg=COLORS.get("text", "#edf6ff"),
                            selectbackground=COLORS.get("card_2", "#1d3353"), selectforeground=COLORS.get("text", "#edf6ff"),
                            font=("Segoe UI", 10, "bold"), bd=0, highlightthickness=0, relief="flat",
                            activestyle="none", yscrollcommand=scrollbar.set)
            scrollbar.config(command=lb.yview)
            
            if len(current_values) > max_items:
                scrollbar.pack(side="right", fill="y")
            lb.pack(side="left", fill="both", expand=True)
            
            for v in current_values:
                lb.insert("end", f"  {v}")
                
            def motion(e):
                idx = lb.nearest(e.y)
                if idx >= 0:
                    lb.selection_clear(0, "end")
                    lb.selection_set(idx)
                    
            def select(e=None):
                sel = lb.curselection()
                if sel:
                    menu._dropdown_callback(current_values[sel[0]])
                top.destroy()
                
            lb.bind("<Motion>", motion)
            lb.bind("<Leave>", lambda e: lb.selection_clear(0, "end"))
            lb.bind("<ButtonRelease-1>", select)
            
            def on_mousewheel(e):
                lb.yview_scroll(int(-1*(e.delta/120)), "units")
                return "break"
                
            top.bind("<MouseWheel>", on_mousewheel)
            
            def on_focus_out(event):
                if not top.winfo_exists(): return
                focused = top.focus_get()
                if not focused or not str(focused).startswith(str(top)):
                    top.destroy()
                    
            top.bind("<FocusOut>", on_focus_out)
            top.after(50, top.focus_set)
        
        menu._open_dropdown_menu = custom_open
        return menu
    return ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=width//10)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class IdentifyItemCategory(ttk.Frame):
    def __init__(self, parent: ttk.Widget, translator: Translator | None = None) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.tr = translator or Translator()
        self.base_dir = Path(__file__).resolve().parent
        self.icons_dir = self.base_dir / "Content" / "Textures" / "UI" / "ItemIcons"
        self.mods_dir = self.base_dir / "mods"

        self.selected_path: Path | None = None
        self.pasted_image = None
        self.preview_photo = None
        self.status_var = tk.StringVar(value=self.tr.t("identify.ready"))
        self.threshold_var = tk.StringVar(value="0.85")
        self.match_mode_var = tk.StringVar(value="Hybrid")

        self.items_index: list[tuple[str, object, str]] = []
        self.templates_by_name: dict[str, list[object]] = {}
        self.last_ranked_names: list[str] = []
        self.monitor_target_name: str | None = None
        self.last_target_template = None

        self.monitor_enabled = False
        self.monitor_job: str | None = None
        self.monitor_tick = 0
        self.monitor_hwnd: int = 0
        self.active = False
        self.match_distance = 20

        self.overlay_window: tk.Toplevel | None = None
        self.overlay_canvas: tk.Canvas | None = None

        self._build()
        self._index_icons()
        self.bind_all("<Control-v>", self.on_paste_image, add="+")
        self._dbg(f"init | cv2={cv2 is not None} numpy={np is not None} imagegrab={ImageGrab is not None}")

    def _dbg(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{stamp}] [Identify] {message}", flush=True)

    def _build(self) -> None:
        outer = modern_frame(self, COLORS["bg"], radius=0)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text=self.tr.t("identify.title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 24, "bold")).pack(
            anchor="w", padx=22, pady=(20, 4)
        )
        tk.Label(outer, text=self.tr.t("identify.subtitle"), bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=22, pady=(0, 14)
        )

        card = modern_frame(outer, COLORS["card"], radius=18, border=1, border_color=COLORS["line"])
        card.pack(fill="both", expand=True, padx=22, pady=(0, 22))

        top = modern_frame(card, COLORS["card"], radius=0)
        top.pack(fill="x", padx=16, pady=16)
        tk.Button(top, text=self.tr.t("identify.select"), command=self.select_image, bg=COLORS["accent"], fg="#041014", relief="flat", padx=14, pady=8).pack(side="left")
        tk.Button(top, text=self.tr.t("identify.scan"), command=self.scan_match, bg=COLORS["soft"], fg=COLORS["text"], relief="flat", padx=14, pady=8).pack(side="left", padx=(8, 0))
        self.monitor_button = tk.Button(
            top,
            text=self.tr.t("identify.monitor_start"),
            command=self.toggle_monitor,
            bg=COLORS["soft"],
            fg=COLORS["text"],
            relief="flat",
            padx=14,
            pady=8,
        )
        self.monitor_button.pack(side="left", padx=(8, 0))
        tk.Label(top, text=self.tr.t("identify.threshold"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(12, 4))
        tk.Entry(
            top,
            textvariable=self.threshold_var,
            width=6,
            bg=COLORS["soft"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            justify="center",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        tk.Label(top, text=self.tr.t("identify.mode"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 4))
        mode_combo = modern_option_menu(top, variable=self.match_mode_var, width=80, values=["Gray", "Color", "Hybrid"])
        mode_combo.pack(side="left")
        tk.Label(top, textvariable=self.status_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(side="right")

        body = modern_frame(card, COLORS["card"], radius=0)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = modern_frame(body, COLORS["soft"], radius=14, border=1, border_color=COLORS["line"])
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.preview_label = tk.Label(left, text=self.tr.t("identify.no_image"), bg=COLORS["soft"], fg=COLORS["muted"], width=24, height=12)
        self.preview_label.pack(padx=12, pady=12)

        right = modern_frame(body, COLORS["soft"], radius=14, border=1, border_color=COLORS["line"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.result_list = tk.Listbox(right, bg=COLORS["soft"], fg=COLORS["text"], relief="flat", font=("Segoe UI", 10))
        self.result_list.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.result_list.bind("<<ListboxSelect>>", self.on_select_ranked_item)

    def _index_icons(self) -> None:
        self.items_index.clear()
        self.templates_by_name.clear()
        if not self.icons_dir.exists():
            self._dbg(f"icons dir missing: {self.icons_dir}")
            return

        for path in self.icons_dir.rglob("*.png"):
            template = self._prepare_template(path)
            if template is None:
                continue
            name = path.stem
            self.items_index.append((name, template, str(path)))
            self.templates_by_name.setdefault(name, []).append(template)

        self._load_mod_templates()
        self.status_var.set(self.tr.t("identify.indexed", count=len(self.items_index)))
        self._dbg(f"index done | items={len(self.items_index)} unique={len(self.templates_by_name)}")

    def _load_mod_templates(self) -> None:
        if not self.mods_dir.exists():
            self._dbg(f"mods dir missing: {self.mods_dir}")
            return
        loaded = 0
        for path in self.mods_dir.rglob("*.png"):
            stem = path.stem
            if "_" not in stem:
                continue
            base_name = stem.split("_", 1)[0]
            template = self._prepare_template(path)
            if template is None:
                continue
            self.templates_by_name.setdefault(base_name, []).append(template)
            loaded += 1
        self._dbg(f"mods templates loaded={loaded}")

    def _prepare_template(self, path: Path):
        if Image is None:
            return None
        try:
            img = Image.open(path).convert("RGBA")
            black = Image.new("RGBA", img.size, (0, 0, 0, 255))
            img = Image.alpha_composite(black, img)
            img = img.resize((32, 32), Image.Resampling.LANCZOS)
            if ImageEnhance is not None:
                img = ImageEnhance.Sharpness(img).enhance(2.0)
            gray = img.convert("L")
            if np is None:
                return gray
            return np.array(gray, dtype=np.uint8)
        except Exception:
            self._dbg(f"template prep failed: {path}")
            return None

    def _target_from_selected(self):
        if self.selected_path and self.selected_path.exists():
            return self._prepare_template(self.selected_path)
        if self.pasted_image is not None and Image is not None:
            try:
                img = self.pasted_image.convert("RGBA")
                black = Image.new("RGBA", img.size, (0, 0, 0, 255))
                img = Image.alpha_composite(black, img).resize((32, 32), Image.Resampling.LANCZOS)
                if ImageEnhance is not None:
                    img = ImageEnhance.Sharpness(img).enhance(2.0)
                gray = img.convert("L")
                if np is None:
                    return gray
                return np.array(gray, dtype=np.uint8)
            except Exception:
                return None
        return None

    def select_image(self) -> None:
        file_path = filedialog.askopenfilename(
            title=self.tr.t("identify.select"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")],
        )
        if not file_path:
            return
        self.selected_path = Path(file_path)
        self.pasted_image = None
        self.status_var.set(self.selected_path.name)
        self._dbg(f"selected image: {self.selected_path}")
        if Image is not None:
            try:
                self._set_preview_image(Image.open(self.selected_path).convert("RGB"))
            except Exception:
                self._dbg("preview failed for selected image")

    def on_paste_image(self, _event=None):
        if ImageGrab is None or Image is None:
            self.status_var.set("Clipboard de imagem indisponivel")
            self._dbg("paste unavailable (missing ImageGrab/PIL)")
            return "break"
        try:
            grabbed = ImageGrab.grabclipboard()
        except Exception:
            grabbed = None
        if grabbed is None:
            self.status_var.set("Nenhuma imagem no Ctrl+V")
            self._dbg("paste empty")
            return "break"

        if isinstance(grabbed, list):
            candidates = [Path(item) for item in grabbed if isinstance(item, str)]
            first_image = next((path for path in candidates if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}), None)
            if first_image and first_image.exists():
                self.selected_path = first_image
                self.pasted_image = None
                try:
                    self._set_preview_image(Image.open(first_image).convert("RGB"))
                    self.status_var.set(f"Colado: {first_image.name}")
                    self._dbg(f"paste file image: {first_image}")
                except Exception:
                    self.status_var.set("Erro ao abrir imagem colada")
                    self._dbg("paste file image failed to open")
                return "break"
            self.status_var.set("Ctrl+V sem imagem valida")
            self._dbg("paste list without valid image")
            return "break"

        if hasattr(grabbed, "convert"):
            self.selected_path = None
            self.pasted_image = grabbed.convert("RGB")
            self._set_preview_image(self.pasted_image)
            self.status_var.set("Imagem colada do Ctrl+V")
            self._dbg(f"paste raw image size={self.pasted_image.size}")
            return "break"

        self.status_var.set("Ctrl+V sem imagem valida")
        self._dbg(f"paste unsupported type={type(grabbed)}")
        return "break"

    def _set_preview_image(self, image) -> None:
        if ImageTk is None:
            return
        preview = image.copy()
        preview.thumbnail((220, 220))
        self.preview_photo = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self.preview_photo, text="")

    def _similarity(self, a, b) -> float:
        if cv2 is not None and np is not None:
            result = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)
            return float(result[0][0])
        if np is not None:
            diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
            mae = float(diff.mean()) / 255.0
            return max(0.0, 1.0 - mae)
        a_data = list(a.getdata())
        b_data = list(b.getdata())
        if not a_data or len(a_data) != len(b_data):
            return 0.0
        total = 0.0
        for av, bv in zip(a_data, b_data):
            total += abs(int(av) - int(bv))
        mae = (total / len(a_data)) / 255.0
        return max(0.0, 1.0 - mae)

    def _prepare_color_32(self, path: Path):
        if Image is None or np is None:
            return None
        try:
            img = Image.open(path).convert("RGBA")
            black = Image.new("RGBA", img.size, (0, 0, 0, 255))
            img = Image.alpha_composite(black, img).resize((32, 32), Image.Resampling.LANCZOS).convert("RGB")
            return np.array(img, dtype=np.uint8)
        except Exception:
            return None

    def _target_color_from_selected(self):
        if Image is None or np is None:
            return None
        if self.selected_path and self.selected_path.exists():
            return self._prepare_color_32(self.selected_path)
        if self.pasted_image is not None:
            try:
                img = self.pasted_image.convert("RGBA")
                black = Image.new("RGBA", img.size, (0, 0, 0, 255))
                img = Image.alpha_composite(black, img).resize((32, 32), Image.Resampling.LANCZOS).convert("RGB")
                return np.array(img, dtype=np.uint8)
            except Exception:
                return None
        return None

    def _color_similarity(self, a_rgb, b_rgb) -> float:
        if np is None or a_rgb is None or b_rgb is None:
            return 0.0
        diff = np.abs(a_rgb.astype(np.int16) - b_rgb.astype(np.int16))
        mae = float(diff.mean()) / 255.0
        return max(0.0, 1.0 - mae)

    def scan_match(self) -> None:
        self._dbg("scan start")
        target = self._target_from_selected()
        if target is None:
            self.status_var.set(self.tr.t("identify.pick_first"))
            self._dbg("scan aborted: no target")
            return
        self.last_target_template = target
        target_color = self._target_color_from_selected()
        mode = self.match_mode_var.get().strip().lower()
        self._dbg(f"scan mode={mode}")
        scores: list[tuple[float, str]] = []
        for name, icon, icon_path in self.items_index:
            gray_score = self._similarity(target, icon)
            if mode == "gray" or np is None or target_color is None:
                final_score = gray_score
            else:
                icon_color = self._prepare_color_32(Path(icon_path))
                color_score = self._color_similarity(target_color, icon_color)
                if mode == "color":
                    final_score = color_score
                else:
                    final_score = (gray_score * 0.65) + (color_score * 0.35)
            scores.append((final_score, name))
        scores.sort(key=lambda item: item[0], reverse=True)
        self.last_ranked_names = [name for _score, name in scores[:25]]
        self.monitor_target_name = self.last_ranked_names[0] if self.last_ranked_names else None
        self.result_list.delete(0, "end")
        for score, name in scores[:25]:
            self.result_list.insert("end", f"{name}  ({score:.3f})")
        self.status_var.set(self.tr.t("identify.done", count=min(25, len(scores))))
        self._dbg(f"scan done | top={self.monitor_target_name} count={len(self.last_ranked_names)}")

    def on_select_ranked_item(self, _event=None) -> None:
        if not self.result_list.curselection():
            return
        raw = self.result_list.get(self.result_list.curselection()[0])
        self.monitor_target_name = raw.split("  (", 1)[0].strip() if raw else None
        self._dbg(f"selected monitor target={self.monitor_target_name}")
        if self.monitor_enabled:
            self.status_var.set(self.tr.t("identify.monitor_target", item=self.monitor_target_name or "-"))

    def _threshold(self) -> float:
        try:
            value = float(self.threshold_var.get().strip().replace(",", "."))
        except ValueError:
            return 0.85
        return max(0.5, min(0.99, value))

    def _templates_for_target(self) -> list[object]:
        templates: list[object] = []
        # Prefer exact image/template supplied by user (faithful to original finder flow).
        if self.last_target_template is not None:
            templates.append(self.last_target_template)
        elif self._target_from_selected() is not None:
            templates.append(self._target_from_selected())

        # Keep ranked item templates as fallback/extra coverage.
        if self.monitor_target_name:
            templates.extend(self.templates_by_name.get(self.monitor_target_name) or [])

        # Deduplicate by object id.
        dedup: list[object] = []
        seen = set()
        for tpl in templates:
            marker = id(tpl)
            if marker in seen:
                continue
            seen.add(marker)
            dedup.append(tpl)
        return dedup

    def _is_foxhole_focused(self) -> bool:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            self.monitor_hwnd = 0
            return False
        title_buffer = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
        title = (title_buffer.value or "").lower()
        focused = "war" in title or "foxhole" in title
        self.monitor_hwnd = int(hwnd) if focused else 0
        if self.monitor_tick % 8 == 0:
            self._dbg(f"focus={focused} hwnd={self.monitor_hwnd} title={title[:80]}")
        return focused

    def _window_client_rect(self) -> tuple[int, int, int, int] | None:
        if not self.monitor_hwnd:
            return None
        user32 = ctypes.windll.user32
        rect = RECT()
        if not user32.GetClientRect(ctypes.c_void_p(self.monitor_hwnd), ctypes.byref(rect)):
            return None
        top_left = POINT(0, 0)
        bottom_right = POINT(rect.right, rect.bottom)
        if not user32.ClientToScreen(ctypes.c_void_p(self.monitor_hwnd), ctypes.byref(top_left)):
            return None
        if not user32.ClientToScreen(ctypes.c_void_p(self.monitor_hwnd), ctypes.byref(bottom_right)):
            return None
        left, top, right, bottom = int(top_left.x), int(top_left.y), int(bottom_right.x), int(bottom_right.y)
        if right <= left or bottom <= top:
            return None
        if self.monitor_tick % 8 == 0:
            self._dbg(f"client rect=({left},{top})-({right},{bottom})")
        return (left, top, right, bottom)

    def _ensure_overlay(self) -> None:
        if self.overlay_window and self.overlay_window.winfo_exists():
            return
        root = self.winfo_toplevel()
        overlay = tk.Toplevel(root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        sw = overlay.winfo_screenwidth()
        sh = overlay.winfo_screenheight()
        overlay.geometry(f"{sw}x{sh}+0+0")
        transparent = "#ff00ff"
        overlay.configure(bg=transparent)
        try:
            overlay.attributes("-transparentcolor", transparent)
        except tk.TclError:
            pass
        canvas = tk.Canvas(overlay, bg=transparent, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self.overlay_window = overlay
        self.overlay_canvas = canvas
        self._dbg("overlay created")

    def _hide_overlay(self) -> None:
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.overlay_window.withdraw()

    def _draw_matches(self, matches: list[tuple[int, int, int, int]]) -> None:
        self._ensure_overlay()
        if not self.overlay_window or not self.overlay_canvas:
            return
        self.overlay_window.deiconify()
        canvas = self.overlay_canvas
        canvas.delete("all")
        for x, y, w, h in matches:
            pad = 4
            canvas.create_oval(x - pad, y - pad, x + w + pad, y + h + pad, outline="#4ef7b2", width=3)
        self._dbg(f"overlay draw matches={len(matches)} first={matches[0] if matches else None}")

    def toggle_monitor(self) -> None:
        if self.monitor_enabled:
            self.stop_monitor()
        else:
            self.start_monitor()

    def start_monitor(self) -> None:
        if cv2 is None or np is None or ImageGrab is None:
            self.status_var.set(self.tr.t("identify.monitor_deps"))
            self._dbg("monitor blocked: missing deps")
            return
        if not self.monitor_target_name and self.last_ranked_names:
            self.monitor_target_name = self.last_ranked_names[0]
        if not self.monitor_target_name:
            self.status_var.set(self.tr.t("identify.monitor_pick"))
            self._dbg("monitor blocked: no target")
            return
        templates = self._templates_for_target()
        self._dbg(
            f"monitor start target={self.monitor_target_name} "
            f"templates={len(templates)} exact_template={'yes' if self.last_target_template is not None else 'no'} "
            f"threshold={self._threshold()}"
        )
        self.monitor_enabled = True
        self.monitor_tick = 0
        self.monitor_button.configure(text=self.tr.t("identify.monitor_stop"), bg=COLORS["accent"], fg="#041014")
        self.status_var.set(self.tr.t("identify.monitor_target", item=self.monitor_target_name))
        self.monitor_screen()

    def stop_monitor(self) -> None:
        self.monitor_enabled = False
        if self.monitor_job:
            try:
                self.after_cancel(self.monitor_job)
            except tk.TclError:
                pass
            self.monitor_job = None
        self._hide_overlay()
        self.monitor_button.configure(text=self.tr.t("identify.monitor_start"), bg=COLORS["soft"], fg=COLORS["text"])
        self._dbg("monitor stopped")

    def monitor_screen(self) -> None:
        self.monitor_job = None
        self.monitor_tick += 1
        if not self.monitor_enabled:
            return
        if not self.active:
            self._hide_overlay()
            self.monitor_job = self.after(350, self.monitor_screen)
            return
        templates = self._templates_for_target()
        if not templates:
            self.stop_monitor()
            self.status_var.set(self.tr.t("identify.monitor_pick"))
            self._dbg("monitor aborted: template list empty")
            return
        if not self._is_foxhole_focused():
            self._hide_overlay()
            self.monitor_job = self.after(250, self.monitor_screen)
            return
        try:
            bbox = self._window_client_rect()
            screenshot = ImageGrab.grab(bbox=bbox) if bbox else ImageGrab.grab()
            screen_np = np.array(screenshot)
            gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)

            threshold = self._threshold()
            scales = (0.85, 1.0, 1.15)
            matches: list[tuple[int, int, int, int]] = []
            best_score = -1.0

            for template in templates:
                for scale in scales:
                    th = max(12, int(template.shape[0] * scale))
                    tw = max(12, int(template.shape[1] * scale))
                    if th >= gray.shape[0] or tw >= gray.shape[1]:
                        continue
                    resized = cv2.resize(template, (tw, th), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
                    result = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
                    _min_val, max_val, _min_loc, _max_loc = cv2.minMaxLoc(result)
                    best_score = max(best_score, float(max_val))
                    ys, xs = np.where(result >= threshold)
                    for x, y in zip(xs.tolist(), ys.tolist()):
                        gx = int(x + (bbox[0] if bbox else 0))
                        gy = int(y + (bbox[1] if bbox else 0))
                        if all(abs(gx - mx) > self.match_distance or abs(gy - my) > self.match_distance for mx, my, _mw, _mh in matches):
                            matches.append((gx, gy, tw, th))

            if self.monitor_tick % 5 == 0:
                self._dbg(
                    f"tick={self.monitor_tick} threshold={threshold} templates={len(templates)} "
                    f"matches={len(matches)} best={best_score:.3f} bbox={bbox}"
                )

            if matches:
                self._draw_matches(matches[:10])
                self.status_var.set(self.tr.t("identify.monitor_found", count=len(matches)))
            else:
                self._hide_overlay()
                self.status_var.set(self.tr.t("identify.monitor_wait", score=f"{best_score:.3f}"))
        except Exception as exc:
            self._hide_overlay()
            self._dbg(f"monitor exception: {exc}")
            self._dbg(traceback.format_exc())

        self.monitor_job = self.after(260, self.monitor_screen)

    def set_active(self, active: bool) -> None:
        self.active = active
        if not active:
            self._hide_overlay()

    def stop(self) -> None:
        self.stop_monitor()
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.overlay_window.destroy()
        self.overlay_window = None
        self.overlay_canvas = None

    def refresh_language(self, translator: Translator) -> None:
        self.tr = translator
