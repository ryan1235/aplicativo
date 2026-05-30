import ctypes
import os
from pathlib import Path
import threading
import time


DEBUG_CONSOLE = True
HOTKEYS = {f"F{i}": 0x6F + i for i in range(1, 13)}
MOUSE_BUTTONS = {
    "Esquerdo": {
        "down": 0x0201,
        "up": 0x0202,
        "mk": 0x0001,
    },
    "Direito": {
        "down": 0x0204,
        "up": 0x0205,
        "mk": 0x0002,
    },
    "Meio": {
        "down": 0x0207,
        "up": 0x0208,
        "mk": 0x0010,
    },
}
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")
IGNORED_PROCESS_HINTS = ("discord", "chrome", "msedge", "firefox", "opera", "steam", "python")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WM_MOUSEMOVE = 0x0200
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class AutoClicker:
    def __init__(self, status_callback) -> None:
        self.status_callback = status_callback
        self.hotkey_name = "F3"
        self.hotkey_vk = HOTKEYS[self.hotkey_name]
        self.mouse_button = "Esquerdo"
        self.interval = 0.1
        self.target_hwnd = 0
        self.click_hwnd = 0
        self.target_title = ""
        self.click_x = 0
        self.click_y = 0
        self.click_count = 0
        self.last_status_update = 0.0
        self.last_find_log = 0.0
        self.last_missing_log = 0.0
        self.enabled = False
        self.waiting_for_foxhole = False
        self.stop_event = threading.Event()
        self.hotkey_was_down = False
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
        self.user32.PostMessageW.restype = ctypes.c_bool
        self.user32.WindowFromPoint.argtypes = [POINT]
        self.user32.WindowFromPoint.restype = ctypes.c_void_p
        self.user32.ChildWindowFromPointEx.argtypes = [ctypes.c_void_p, POINT, ctypes.c_uint]
        self.user32.ChildWindowFromPointEx.restype = ctypes.c_void_p
        self.monitor_thread = threading.Thread(target=self.monitor_hotkey, daemon=True)
        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.monitor_thread.start()
        self.click_thread.start()
        self.log("AutoClicker iniciado")

    def log(self, message: str) -> None:
        if DEBUG_CONSOLE:
            print(f"[AutoClicker] {message}", flush=True)

    def configure(self, hotkey_name: str, mouse_button: str, interval: float) -> None:
        self.hotkey_name = hotkey_name
        self.hotkey_vk = HOTKEYS[hotkey_name]
        self.mouse_button = mouse_button
        self.interval = max(0.03, interval)
        self.log(f"Config: hotkey={self.hotkey_name} botao={self.mouse_button} intervalo={self.interval:.2f}s")
        self.status_callback(self.status_text())

    def use_foxhole_window(self, *, quiet: bool = False) -> str:
        if not quiet:
            self.log("Procurando janela do Foxhole...")
        hwnd, title = self.find_foxhole_window(quiet=quiet)
        if not hwnd:
            self.target_hwnd = 0
            self.click_hwnd = 0
            self.target_title = ""
            if not quiet:
                self.log("Foxhole nao encontrado")
            self.status_callback(self.status_text())
            return "Foxhole nao encontrado"

        self.target_hwnd = hwnd
        self.target_title = title or "Foxhole"
        self.capture_click_point()
        self.log(
            f"Foxhole capturado: hwnd={self.target_hwnd} click_hwnd={self.click_hwnd} "
            f"title='{self.target_title}' ponto={self.click_x},{self.click_y}"
        )
        self.status_callback(self.status_text())
        return self.target_title

    def find_foxhole_window(self, *, quiet: bool = False) -> tuple[int, str]:
        matches: list[tuple[int, str]] = []
        visible_windows: list[tuple[int, str, str]] = []
        enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_proc(hwnd, _lparam):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            length = self.user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
            process_name = self.get_window_process_name(hwnd).lower()
            process_path = self.get_window_process_path(hwnd).lower()
            title_lower = title.lower()
            if process_name or title:
                visible_windows.append((hwnd, process_name, title))

            if any(blocked in process_name for blocked in IGNORED_PROCESS_HINTS):
                return True
            if self.is_foxhole_process(process_name, process_path):
                self.log(f"Foxhole confirmado: hwnd={hwnd} processo={process_name} titulo='{title}' caminho='{process_path}'")
                matches.append((hwnd, title))
                return True
            return True

        self.user32.EnumWindows(enum_proc_type(enum_proc), 0)
        now = time.monotonic()
        if not quiet and now - self.last_find_log >= 3:
            self.last_find_log = now
            self.log(f"Janelas Foxhole encontradas: {len(matches)}")
            if not matches:
                self.log("Janelas visiveis detectadas:")
                for hwnd, process_name, title in visible_windows[:25]:
                    self.log(f"  hwnd={hwnd} processo='{process_name}' titulo='{title}'")
        return matches[0] if matches else (0, "")

    def get_window_title(self, hwnd: int) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def get_window_process_name(self, hwnd: int) -> str:
        process_path = self.get_window_process_path(hwnd)
        return Path(process_path).name if process_path else ""

    def get_window_process_path(self, hwnd: int) -> str:
        pid = ctypes.c_ulong()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""

        process_handle = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not process_handle:
            return ""

        try:
            path_buffer = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(len(path_buffer))
            if self.kernel32.QueryFullProcessImageNameW(process_handle, 0, path_buffer, ctypes.byref(size)):
                return path_buffer.value
            return ""
        finally:
            self.kernel32.CloseHandle(process_handle)

    def is_foxhole_window(self, hwnd: int) -> bool:
        process_name = self.get_window_process_name(hwnd).lower()
        process_path = self.get_window_process_path(hwnd).lower()
        return self.is_foxhole_process(process_name, process_path)

    @staticmethod
    def is_foxhole_process(process_name: str, process_path: str) -> bool:
        return process_name in FOXHOLE_PROCESS_NAMES or any(hint in process_path for hint in FOXHOLE_PATH_HINTS)

    def toggle(self) -> None:
        turning_on = not self.enabled
        if turning_on:
            self.use_foxhole_window()
        self.enabled = not self.enabled
        self.waiting_for_foxhole = False
        self.log(f"F3/toggle: enabled={self.enabled} target_hwnd={self.target_hwnd} click_hwnd={self.click_hwnd}")
        self.status_callback(self.status_text())

    def start(self) -> None:
        if not self.target_hwnd:
            self.use_foxhole_window()
        self.enabled = True
        self.waiting_for_foxhole = False
        self.log(f"Start: enabled={self.enabled} target_hwnd={self.target_hwnd} click_hwnd={self.click_hwnd}")
        self.status_callback(self.status_text())

    def pause(self) -> None:
        self.enabled = False
        self.waiting_for_foxhole = False
        self.log("Pausado")
        self.status_callback(self.status_text())

    def stop(self) -> None:
        self.enabled = False
        self.stop_event.set()
        self.log("Parando AutoClicker")

    def status_text(self) -> str:
        if self.enabled and self.waiting_for_foxhole:
            return f"Ligado | aguardando Foxhole | {self.hotkey_name}"
        state = "Ligado" if self.enabled else "Desligado"
        target = self.target_title if self.target_title else "Foxhole"
        point = f"{self.click_x},{self.click_y}" if self.target_hwnd else "--"
        return f"{state} | {target} | virtual {point} | cliques {self.click_count} | {self.hotkey_name} | {self.interval:.2f}s"

    def monitor_hotkey(self) -> None:
        while not self.stop_event.is_set():
            is_down = bool(self.user32.GetAsyncKeyState(self.hotkey_vk) & 0x8000)
            if is_down and not self.hotkey_was_down:
                self.log(f"Hotkey detectada: {self.hotkey_name}")
                self.toggle()
            self.hotkey_was_down = is_down
            time.sleep(0.03)

    def click_loop(self) -> None:
        while not self.stop_event.is_set():
            if self.enabled:
                self.refresh_target_if_needed()
                if self.target_hwnd and self.user32.IsWindow(self.target_hwnd):
                    should_update = self.waiting_for_foxhole
                    self.waiting_for_foxhole = False
                    if should_update:
                        self.status_callback(self.status_text())
                    self.click()
                    now = time.monotonic()
                    if now - self.last_status_update >= 1:
                        self.last_status_update = now
                        self.status_callback(self.status_text())
                    time.sleep(self.interval)
                else:
                    if not self.waiting_for_foxhole:
                        self.waiting_for_foxhole = True
                        now = time.monotonic()
                        if now - self.last_missing_log >= 3:
                            self.last_missing_log = now
                            self.log("Aguardando Foxhole: target inexistente ou janela fechada")
                        self.status_callback(self.status_text())
                    time.sleep(0.12)
            else:
                time.sleep(0.05)

    def refresh_target_if_needed(self) -> None:
        if self.target_hwnd and self.user32.IsWindow(self.target_hwnd):
            return
        self.use_foxhole_window()

    def capture_click_point(self) -> None:
        if not self.target_hwnd:
            self.click_hwnd = 0
            self.click_x = 0
            self.click_y = 0
            self.log("Nao capturou ponto: sem target_hwnd")
            return

        point = POINT()
        if self.user32.GetCursorPos(ctypes.byref(point)):
            window_at_cursor = self.user32.WindowFromPoint(point)
            self.log(f"Cursor na tela: {point.x},{point.y} window_at_cursor={window_at_cursor}")
            if window_at_cursor and self.is_same_process_window(window_at_cursor, self.target_hwnd):
                self.click_hwnd = window_at_cursor
                client_point = POINT(point.x, point.y)
                if self.user32.ScreenToClient(self.click_hwnd, ctypes.byref(client_point)):
                    if self.is_point_inside_client(client_point.x, client_point.y):
                        self.click_x = max(0, client_point.x)
                        self.click_y = max(0, client_point.y)
                        self.log(f"Ponto capturado pelo cursor: hwnd={self.click_hwnd} ponto={self.click_x},{self.click_y}")
                        return
                    self.log(f"Cursor esta fora da area cliente: {client_point.x},{client_point.y}")
                else:
                    self.log("ScreenToClient falhou")
            else:
                self.log("Cursor nao esta sobre uma janela do mesmo processo do Foxhole")

        rect = RECT()
        if self.user32.GetClientRect(self.target_hwnd, ctypes.byref(rect)):
            self.click_hwnd = self.find_child_at_point(self.target_hwnd, (rect.right - rect.left) // 2, (rect.bottom - rect.top) // 2)
            self.click_x = max(0, (rect.right - rect.left) // 2)
            self.click_y = max(0, (rect.bottom - rect.top) // 2)
            self.log(f"Usando centro da janela: hwnd={self.click_hwnd} ponto={self.click_x},{self.click_y}")
            return

        self.click_hwnd = self.target_hwnd
        self.click_x = 0
        self.click_y = 0
        self.log("GetClientRect falhou; usando ponto 0,0")

    def is_point_inside_client(self, x: int, y: int) -> bool:
        rect = RECT()
        hwnd = self.click_hwnd or self.target_hwnd
        if not self.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return False
        return rect.left <= x < rect.right and rect.top <= y < rect.bottom

    def find_child_at_point(self, hwnd: int, x: int, y: int) -> int:
        child = self.user32.ChildWindowFromPointEx(hwnd, POINT(x, y), CWP_SKIPINVISIBLE | CWP_SKIPDISABLED)
        if child and child != hwnd:
            return child
        return hwnd

    def is_same_process_window(self, candidate_hwnd: int, target_hwnd: int) -> bool:
        candidate_pid = ctypes.c_ulong()
        target_pid = ctypes.c_ulong()
        self.user32.GetWindowThreadProcessId(candidate_hwnd, ctypes.byref(candidate_pid))
        self.user32.GetWindowThreadProcessId(target_hwnd, ctypes.byref(target_pid))
        return bool(candidate_pid.value and candidate_pid.value == target_pid.value)

    def click(self) -> None:
        hwnd = self.click_hwnd or self.target_hwnd
        if not hwnd:
            self.log("Clique ignorado: hwnd vazio")
            return

        button = MOUSE_BUTTONS[self.mouse_button]
        lparam = self.make_lparam(self.click_x, self.click_y)
        move_sent = self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        down_sent = self.user32.PostMessageW(hwnd, button["down"], button["mk"], lparam)
        up_sent = self.user32.PostMessageW(hwnd, button["up"], 0, lparam)
        if down_sent and up_sent:
            self.click_count += 1
            if self.click_count == 1 or self.click_count % 10 == 0:
                self.log(
                    f"Clique enviado #{self.click_count}: hwnd={hwnd} ponto={self.click_x},{self.click_y} "
                    f"move={bool(move_sent)} down={bool(down_sent)} up={bool(up_sent)}"
                )
        else:
            error = self.kernel32.GetLastError()
            self.log(
                f"Falha ao enviar clique: hwnd={hwnd} ponto={self.click_x},{self.click_y} "
                f"move={bool(move_sent)} down={bool(down_sent)} up={bool(up_sent)} erro={error}"
            )

    @staticmethod
    def make_lparam(x: int, y: int) -> int:
        return (y & 0xFFFF) << 16 | (x & 0xFFFF)
