import ctypes
from ctypes import wintypes
import os
import queue
import random
from pathlib import Path
import threading
import time


DEBUG_CONSOLE = os.environ.get("FELB_DEBUG_AUTOCLICKER", "").lower() in {"1", "true", "yes", "on"}
HOTKEYS = {f"F{i}": 0x6F + i for i in range(1, 13)}
ACTION_KEYS = {
    **HOTKEYS,
    **{chr(code): code for code in range(0x41, 0x5B)},  # A-Z
    **{str(number): 0x30 + number for number in range(0, 10)},  # 0-9
    "Esc": 0x1B,
    "Tab": 0x09,
    "Enter": 0x0D,
    "Space": 0x20,
    "Up": 0x26,
    "Down": 0x28,
    "Left": 0x25,
    "Right": 0x27,
    "Insert": 0x2D,
    "Delete": 0x2E,
    "Home": 0x24,
    "End": 0x23,
    "PageUp": 0x21,
    "PageDown": 0x22,
}
MOUSE_BUTTONS = {
    "Esquerdo": {"down": 0x0201, "up": 0x0202, "mk": 0x0001},
    "Direito": {"down": 0x0204, "up": 0x0205, "mk": 0x0002},
    "Meio": {"down": 0x0207, "up": 0x0208, "mk": 0x0010},
}
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")
IGNORED_PROCESS_HINTS = ("discord", "chrome", "msedge", "firefox", "opera", "steam", "python")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WM_MOUSEMOVE = 0x0200
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
LLKHF_INJECTED = 0x00000010
LLMHF_INJECTED = 0x00000001
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002

VK_W = 0x57
VK_A = 0x41
VK_S = 0x53
VK_D = 0x44
VK_Z = 0x5A
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_4 = 0x34
VK_ESC = 0x1B
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_R = 0x52
MK_SHIFT = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class AutoClicker:
    def __init__(self, status_callback) -> None:
        self.status_callback = status_callback
        self.hotkey_name = "F3"
        self.hotkey_vk = HOTKEYS[self.hotkey_name]
        self.mouse_button = "Esquerdo"
        self.interval = 0.5
        self.modes_enabled: dict[str, bool] = {
            "auto": True,
            "move": True,
            "pilot": True,
            "right_hold": True,
            "fixed": True,
            "artillery": True,
        }

        self.target_hwnd = 0
        self.click_hwnd = 0
        self.target_title = ""
        self.click_x = 0
        self.click_y = 0
        self.click_count = 0
        self.last_status_update = 0.0
        self.last_find_log = 0.0
        self.last_missing_log = 0.0

        # Modo original (auto clicker configuravel da UI)
        self.enabled = False
        self.waiting_for_foxhole = False

        # Modo extra: double-click fixo com tecla dedicada
        self.fixed_hotkey_name = "F6"
        self.fixed_hotkey_vk = ACTION_KEYS[self.fixed_hotkey_name]
        self.fixed_click_enabled = False
        self.double_click_range = (0.08, 0.15)

        # Move-click / piloto automatico configuraveis
        self.move_hotkey_name = "F2"
        self.move_hotkey_vk = ACTION_KEYS[self.move_hotkey_name]
        self.pilot_hotkey_name = "F4"
        self.pilot_hotkey_vk = ACTION_KEYS[self.pilot_hotkey_name]
        self.right_hold_hotkey_name = "F9"
        self.right_hold_hotkey_vk = ACTION_KEYS[self.right_hold_hotkey_name]
        self.pilot_w_paused = False
        self.pilot_w_hwnd = 0
        self.w_hold_key_down = False
        self.w_hold_worker_running = False
        self.shift_pressed = False

        # Override para forcar W mesmo quando idioma for FR (toggle na UI)
        self.force_w_in_fr = False
        # tecla usada para W-hold (pode ser VK_W ou VK_Z dependendo do idioma/layout)
        self._w_hold_vk = VK_W

        # W double-tap to hold W mode
        self.w_hold_enabled = False
        self.w_hold_hwnd = 0
        self.w_last_tap = 0.0
        self.w_double_tap_threshold = 0.35  # seconds between taps
        self.w_doubletap_enabled = False  # can be toggled from UI

        # Right mouse hold: background RMB hold for Foxhole.
        self.right_hold_enabled = False
        self.right_hold_hwnd = 0
        self.right_hold_lparam = 0
        self.right_hold_worker_running = False
        self.right_hold_button_down = False
        self.right_double_tap_threshold = 0.35
        self.right_doubletap_enabled = False
        self.right_last_tap = 0.0
        self.right_suppress_next_up = False
        self.right_mouse_action_queue = queue.SimpleQueue()

        # Shift hold with autoclick
        self.shift_enabled = False

        # Artilharia: R + Left Click
        self.artillery_hotkey_name = "F7"
        self.artillery_hotkey_vk = ACTION_KEYS[self.artillery_hotkey_name]
        self.artillery_enabled = False
        self.artillery_interval = 0.55
        self.artillery_key_delay = 0.045

        # F2 - move-click segurando esquerdo
        self.move_click_enabled = False
        self.move_click_holding = False
        self.move_click_hwnd = 0
        self.move_click_lparam = 0
        self.move_click_worker_running = False

        # Slots 1-4 para clique posicional durante double-click fixo
        self.slot_positions: dict[int, tuple[int, int]] = {
            1: (40, 80),
            2: (95, 80),
            3: (150, 80),
            4: (205, 80),
        }

        # F5 menu callback (UI thread-safe callback supplied by view layer)
        self.menu_callback = None

        self.stop_event = threading.Event()
        self.key_was_down: dict[int, bool] = {}
        self.keyboard_hook_handle = 0
        self.keyboard_hook_proc = None
        self.keyboard_hook_thread_id = 0
        self.mouse_hook_handle = 0
        self.mouse_hook_proc = None
        self.mouse_hook_thread_id = 0
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
        self.user32.PostMessageW.restype = ctypes.c_bool
        self.user32.GetForegroundWindow.restype = ctypes.c_void_p
        self.user32.WindowFromPoint.argtypes = [POINT]
        self.user32.WindowFromPoint.restype = ctypes.c_void_p
        self.user32.ChildWindowFromPointEx.argtypes = [ctypes.c_void_p, POINT, ctypes.c_uint]
        self.user32.ChildWindowFromPointEx.restype = ctypes.c_void_p
        self.user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
        self.user32.SetWindowsHookExW.restype = ctypes.c_void_p
        self.user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        self.user32.UnhookWindowsHookEx.restype = ctypes.c_bool
        self.user32.PostThreadMessageW.argtypes = [wintypes.DWORD, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.PostThreadMessageW.restype = ctypes.c_bool
        self.user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.CallNextHookEx.restype = wintypes.LPARAM
        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self.user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
        self.user32.GetMessageW.restype = ctypes.c_int
        self.user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        self.user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]

        self.monitor_thread = threading.Thread(target=self.monitor_hotkeys, daemon=True)
        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.keyboard_hook_thread = threading.Thread(target=self._keyboard_hook_loop, daemon=True)
        self.mouse_hook_thread = threading.Thread(target=self._mouse_hook_loop, daemon=True)
        self.right_mouse_action_thread = threading.Thread(target=self._right_mouse_action_loop, daemon=True)
        self.monitor_thread.start()
        self.click_thread.start()
        self.keyboard_hook_thread.start()
        self.mouse_hook_thread.start()
        self.right_mouse_action_thread.start()
        self.log("AutoClicker iniciado")

    def set_language(self, language: str) -> None:
        """Configura a tecla usada para W-Hold com base no código de idioma normalizado.
        Se o idioma for 'fr', usa `Z` (AZERTY), caso contrário usa `W` (QWERTY/pt/en/es).
        """
        try:
            from i18n import normalize_language

            code = normalize_language(language)
        except Exception:
            code = "pt"
        # Se o usuário ativou o override para manter W no FR, respeitamos isso
        if code == "fr" and not getattr(self, "force_w_in_fr", False):
            self._w_hold_vk = VK_Z
        else:
            self._w_hold_vk = VK_W

    def w_hold_label(self) -> str:
        """Retorna o rótulo visível da tecla usada para W-hold ("W" ou "Z")."""
        return "Z" if self._w_hold_vk == VK_Z else "W"

    def log(self, message: str) -> None:
        if DEBUG_CONSOLE:
            try:
                print(f"[AutoClicker] {message}", flush=True)
            except Exception:
                pass

    def set_slot_positions(self, positions: dict[int, tuple[int, int]]) -> None:
        for slot, value in positions.items():
            if slot in (1, 2, 3, 4):
                try:
                    x, y = int(value[0]), int(value[1])
                except Exception:
                    continue
                self.slot_positions[slot] = (max(0, x), max(0, y))
        self.log(f"Slots atualizados: {self.slot_positions}")

    def set_menu_callback(self, callback) -> None:
        self.menu_callback = callback

    def configure(self, hotkey_name: str, mouse_button: str, interval: float) -> None:
        # Mantemos para compatibilidade da tela já existente.
        self.hotkey_name = hotkey_name
        self.hotkey_vk = ACTION_KEYS.get(hotkey_name, ACTION_KEYS["F3"])
        self.mouse_button = mouse_button if mouse_button in MOUSE_BUTTONS else "Esquerdo"
        self.interval = max(0.03, interval)
        self.log(f"Config: hotkey={self.hotkey_name} botao={self.mouse_button} intervalo={self.interval:.2f}s")
        self.status_callback(self.status_text())

    def configure_modes_enabled(self, modes: dict[str, bool]) -> None:
        defaults = {
            "auto": True,
            "move": True,
            "pilot": True,
            "right_hold": True,
            "fixed": True,
            "artillery": True,
        }
        defaults.update({key: bool(value) for key, value in modes.items() if key in defaults})
        self.modes_enabled = defaults
        if not self.mode_is_enabled("auto"):
            self.pause()
        if not self.mode_is_enabled("move"):
            self.disable_move_click("modo desativado")
        if not self.mode_is_enabled("pilot"):
            self.disable_w_hold("modo desativado")
        if not self.mode_is_enabled("right_hold"):
            self.disable_right_hold("modo desativado")
        if not self.mode_is_enabled("fixed"):
            self.disable_fixed_click("modo desativado")
        if not self.mode_is_enabled("artillery"):
            self.disable_artillery("modo desativado")
        self.status_callback(self.status_text())

    def mode_is_enabled(self, mode: str) -> bool:
        return bool(self.modes_enabled.get(mode, True))

    def configure_action_hotkeys(
        self,
        move_hotkey: str,
        fixed_hotkey: str,
        pilot_hotkey: str,
        artillery_hotkey: str = "F7",
        right_hold_hotkey: str = "F9",
    ) -> None:
        self.move_hotkey_name = move_hotkey if move_hotkey in ACTION_KEYS else "F2"
        self.fixed_hotkey_name = fixed_hotkey if fixed_hotkey in ACTION_KEYS else "F6"
        self.pilot_hotkey_name = pilot_hotkey if pilot_hotkey in ACTION_KEYS else "F4"
        self.artillery_hotkey_name = artillery_hotkey if artillery_hotkey in ACTION_KEYS else "F7"
        self.right_hold_hotkey_name = right_hold_hotkey if right_hold_hotkey in ACTION_KEYS else "F9"
        self.move_hotkey_vk = ACTION_KEYS[self.move_hotkey_name]
        self.fixed_hotkey_vk = ACTION_KEYS[self.fixed_hotkey_name]
        self.pilot_hotkey_vk = ACTION_KEYS[self.pilot_hotkey_name]
        self.artillery_hotkey_vk = ACTION_KEYS[self.artillery_hotkey_name]
        self.right_hold_hotkey_vk = ACTION_KEYS[self.right_hold_hotkey_name]
        self.log(
            f"Hotkeys extras: move={self.move_hotkey_name} "
            f"fixed={self.fixed_hotkey_name} pilot={self.pilot_hotkey_name} "
            f"right={self.right_hold_hotkey_name}"
        )
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
            if process_name or title:
                visible_windows.append((hwnd, process_name, title))
            if any(blocked in process_name for blocked in IGNORED_PROCESS_HINTS):
                return True
            if self.is_foxhole_process(process_name, process_path) or title.strip() == "Foxhole":
                self.log(f"Foxhole confirmado: hwnd={hwnd} processo={process_name} titulo='{title}' caminho='{process_path}'")
                matches.append((hwnd, title))
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
        except Exception:
            return ""
        finally:
            self.kernel32.CloseHandle(process_handle)

    def is_foxhole_window(self, hwnd: int) -> bool:
        process_name = self.get_window_process_name(hwnd).lower()
        process_path = self.get_window_process_path(hwnd).lower()
        
        length = self.user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value
            
        return self.is_foxhole_process(process_name, process_path) or title.strip() == "Foxhole"

    @staticmethod
    def is_foxhole_process(process_name: str, process_path: str) -> bool:
        return process_name in FOXHOLE_PROCESS_NAMES or any(hint in process_path for hint in FOXHOLE_PATH_HINTS)

    def toggle(self) -> None:
        if self.enabled:
            self.pause()
        else:
            self.start()

    def start(self) -> None:
        if not self.mode_is_enabled("auto"):
            self.log("Auto Clicker ignorado: modo desativado")
            self.status_callback(self.status_text())
            return
        self.disable_fixed_click("auto on")
        self.use_foxhole_window()
        self.enabled = True
        self.waiting_for_foxhole = False
        self.status_callback(self.status_text())

    def pause(self) -> None:
        if not self.enabled:
            return
        self.enabled = False
        self.waiting_for_foxhole = False
        self.status_callback(self.status_text())

    def stop(self) -> None:
        self.pause()
        self.disable_fixed_click("stop")
        self.disable_move_click("stop")
        self.disable_artillery("stop")
        self.disable_w_hold("stop")
        self.disable_right_hold("stop")
        self.stop_event.set()
        if self.keyboard_hook_handle:
            try:
                self.user32.UnhookWindowsHookEx(self.keyboard_hook_handle)
            except Exception:
                pass
            self.keyboard_hook_handle = 0
        if self.keyboard_hook_thread_id:
            try:
                self.user32.PostThreadMessageW(self.keyboard_hook_thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        if self.mouse_hook_handle:
            try:
                self.user32.UnhookWindowsHookEx(self.mouse_hook_handle)
            except Exception:
                pass
            self.mouse_hook_handle = 0
        if self.mouse_hook_thread_id:
            try:
                self.user32.PostThreadMessageW(self.mouse_hook_thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        try:
            self.right_mouse_action_queue.put(None)
        except Exception:
            pass
        self.log("Parando AutoClicker")

    def status_text(self) -> str:
        running = (
            self.enabled
            or self.fixed_click_enabled
            or self.move_click_enabled
            or self.artillery_enabled
            or self.w_hold_enabled
            or self.right_hold_enabled
        )
        if running and (not self.target_hwnd or not self.user32.IsWindow(self.target_hwnd) or self.waiting_for_foxhole):
            return f"Ligado | aguardando Foxhole | {self.hotkey_name}"
        state = "Ligado" if running else "Desligado"
        target = self.target_title if self.target_title else "Foxhole"
        point = f"{self.click_x},{self.click_y}" if self.target_hwnd else "--"
        mode = []
        if self.move_click_enabled:
            mode.append("F2")
        if self.enabled:
            mode.append("AUTO")
        if self.fixed_click_enabled:
            mode.append(self.fixed_hotkey_name)
        if self.artillery_enabled:
            mode.append(f"{self.artillery_hotkey_name}:ART")
        if self.w_hold_enabled:
            mode.append(f"{self.pilot_hotkey_name}:W{'(S=PAUSE)' if self.pilot_w_paused else ''}")
        if self.right_hold_enabled:
            mode.append(f"{self.right_hold_hotkey_name}:RMB")
        if self.shift_enabled:
            mode.append("SHIFT+" if self.shift_pressed else "SHIFT")
        mode_text = ",".join(mode) if mode else "-"
        return f"{state} | {target} | virtual {point} | cliques {self.click_count} | {self.hotkey_name} | {self.interval:.2f}s | {mode_text}"

    def monitor_hotkeys(self) -> None:
        watch_keys = [
            self.hotkey_vk,
            self.move_hotkey_vk,
            self.pilot_hotkey_vk,
            self.right_hold_hotkey_vk,
            self.fixed_hotkey_vk,
            self.artillery_hotkey_vk,
            HOTKEYS["F5"],
            VK_1, VK_2, VK_3, VK_4,
        ]
        for vk in watch_keys:
            self.key_was_down[vk] = False

        # Double-tap W monitoring runs in a background thread.
        threading.Thread(target=self._w_doubletap_monitor, daemon=True).start()

        while not self.stop_event.is_set():
            self.handle_key_press(self.move_hotkey_vk, self.toggle_move_click)
            self.handle_key_press(self.hotkey_vk, self.toggle)
            self.handle_key_press(self.fixed_hotkey_vk, self.toggle_fixed_click)
            self.handle_key_press(self.pilot_hotkey_vk, self.toggle_pilot)
            self.handle_key_press(self.right_hold_hotkey_vk, self.toggle_right_hold)
            self.handle_key_press(self.artillery_hotkey_vk, self.toggle_artillery)
            self.handle_key_press(HOTKEYS["F5"], self.open_orders_menu)

            if self.fixed_click_enabled:
                self.handle_key_press(VK_1, lambda: self.trigger_slot_click(1))
                self.handle_key_press(VK_2, lambda: self.trigger_slot_click(2))
                self.handle_key_press(VK_3, lambda: self.trigger_slot_click(3))
                self.handle_key_press(VK_4, lambda: self.trigger_slot_click(4))

            self.check_cancel_shortcuts()
            self.refresh_shift_state()
            time.sleep(0.015)

    def handle_key_press(self, vk: int, callback) -> None:
        is_down = bool(self.user32.GetAsyncKeyState(vk) & 0x8000)
        was_down = self.key_was_down.get(vk, False)
        if is_down and not was_down:
            try:
                callback()
            except Exception as exc:
                self.log(f"Erro no callback da tecla {vk}: {exc}")
        self.key_was_down[vk] = is_down

    def check_cancel_shortcuts(self) -> None:
        esc = bool(self.user32.GetAsyncKeyState(VK_ESC) & 0x8000)
        lbtn = bool(self.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
        rbtn = bool(self.user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000)
        mbtn = bool(self.user32.GetAsyncKeyState(VK_MBUTTON) & 0x8000)
        if self.move_click_enabled and esc:
            self.disable_move_click("cancel: esc")

        # Double-click fixo cancela com mouse/asd/esc (W excludido pois w_hold usa W)
        asd = any(bool(self.user32.GetAsyncKeyState(vk) & 0x8000) for vk in (VK_A, VK_S, VK_D))
        if self.fixed_click_enabled and (esc or lbtn or rbtn or mbtn or asd):
            self.disable_fixed_click("cancel: mouse/asd/esc")

        if self.artillery_enabled and lbtn:
            self.disable_artillery("cancel: left click")

        # W-hold cancels on Esc only (not on W press — that would cancel itself)
        if self.w_hold_enabled and esc:
            self.disable_w_hold("cancel: esc")

        if self.right_hold_enabled and esc:
            self.disable_right_hold("cancel: esc")

    def shift_modifier_active(self) -> bool:
        return bool(self.shift_enabled and self.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)

    def refresh_shift_state(self) -> None:
        current = self.shift_modifier_active()
        if current == self.shift_pressed:
            return
        self.shift_pressed = current
        if self.enabled or self.fixed_click_enabled or self.artillery_enabled or self.w_hold_enabled or self.right_hold_enabled:
            self.status_callback(self.status_text())

    def click_loop(self) -> None:
        while not self.stop_event.is_set():
            if self.enabled:
                self.refresh_target_if_needed()
                if self.target_hwnd and self.user32.IsWindow(self.target_hwnd):
                    self.waiting_for_foxhole = False
                    self.click()
                    now = time.monotonic()
                    if now - self.last_status_update >= 1:
                        self.last_status_update = now
                        self.status_callback(self.status_text())
                    time.sleep(self.interval)
                else:
                    if not self.waiting_for_foxhole:
                        self.waiting_for_foxhole = True
                        self.log("Aguardando Foxhole: target inexistente ou janela fechada")
                        self.status_callback(self.status_text())
                    time.sleep(0.12)
            elif self.fixed_click_enabled:
                self.refresh_target_if_needed()
                if self.target_hwnd and self.user32.IsWindow(self.target_hwnd):
                    self.waiting_for_foxhole = False
                    self.click()
                    now = time.monotonic()
                    if now - self.last_status_update >= 1:
                        self.last_status_update = now
                        self.status_callback(self.status_text())
                    time.sleep(random.uniform(*self.double_click_range))
                else:
                    if not self.waiting_for_foxhole:
                        self.waiting_for_foxhole = True
                        self.log("Aguardando Foxhole: target inexistente ou janela fechada")
                        self.status_callback(self.status_text())
                    time.sleep(0.12)
            elif self.artillery_enabled:
                self.refresh_target_if_needed()
                if self.target_hwnd and self.user32.IsWindow(self.target_hwnd):
                    self.waiting_for_foxhole = False
                    self.artillery_step()
                    now = time.monotonic()
                    if now - self.last_status_update >= 1:
                        self.last_status_update = now
                        self.status_callback(self.status_text())
                    time.sleep(self.artillery_interval)
                else:
                    if not self.waiting_for_foxhole:
                        self.waiting_for_foxhole = True
                        self.log("Aguardando Foxhole: target inexistente ou janela fechada")
                        self.status_callback(self.status_text())
                    time.sleep(0.12)
            else:
                time.sleep(0.05)

    def toggle_fixed_click(self) -> None:
        if self.fixed_click_enabled:
            self.disable_fixed_click(f"{self.fixed_hotkey_name} off")
        else:
            self.enable_fixed_click()

    def enable_fixed_click(self) -> None:
        if not self.mode_is_enabled("fixed"):
            self.log(f"{self.fixed_hotkey_name} ignorado: modo desativado")
            self.status_callback(self.status_text())
            return
        self.pause()
        self.use_foxhole_window()
        self.fixed_click_enabled = True
        self.waiting_for_foxhole = False
        self.log(f"{self.fixed_hotkey_name} on: double-click fixo ativo")
        self.status_callback(self.status_text())

    def disable_fixed_click(self, reason: str) -> None:
        if not self.fixed_click_enabled:
            return
        self.fixed_click_enabled = False
        self.waiting_for_foxhole = False
        self.log(f"{self.fixed_hotkey_name} off: {reason}")
        self.status_callback(self.status_text())

    def toggle_move_click(self) -> None:
        if self.move_click_enabled:
            self.disable_move_click(f"{self.move_hotkey_name} off")
        else:
            self.enable_move_click()

    def enable_move_click(self) -> None:
        if not self.mode_is_enabled("move"):
            self.log(f"{self.move_hotkey_name} ignorado: modo desativado")
            self.status_callback(self.status_text())
            return
        self.pause()
        self.disable_fixed_click("move click on")
        self.disable_artillery("move click on")
        self.disable_w_hold("move click on")
        self.disable_right_hold("move click on")
        self.use_foxhole_window(quiet=True)
        hwnd = self.click_hwnd or self.target_hwnd
        if not hwnd:
            self.log("F2 on abortado: sem janela alvo")
            self.status_callback(self.status_text())
            return
        button = MOUSE_BUTTONS["Esquerdo"]
        lparam = self.make_lparam(self.click_x, self.click_y)
        self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        down_sent = self.user32.PostMessageW(hwnd, button["down"], button["mk"], lparam)
        if down_sent:
            self.move_click_enabled = True
            self.move_click_holding = True
            self.move_click_hwnd = hwnd
            self.move_click_lparam = lparam
            self.log(f"{self.move_hotkey_name} on: segurando esquerdo hwnd={hwnd} ponto={self.click_x},{self.click_y}")
            self.status_callback(self.status_text())
            if not self.move_click_worker_running:
                threading.Thread(target=self._move_click_worker, daemon=True).start()
        else:
            self.log(f"{self.move_hotkey_name} falhou ao segurar esquerdo")
            self.status_callback(self.status_text())

    def disable_move_click(self, reason: str) -> None:
        if not self.move_click_enabled and not self.move_click_holding:
            return
        button = MOUSE_BUTTONS["Esquerdo"]
        hwnd = self.move_click_hwnd or self.click_hwnd or self.target_hwnd
        if hwnd:
            self.user32.PostMessageW(hwnd, button["up"], 0, self.move_click_lparam or self.make_lparam(self.click_x, self.click_y))
        self.move_click_enabled = False
        self.move_click_holding = False
        self.move_click_hwnd = 0
        self.move_click_lparam = 0
        self.log(f"F2 off: {reason}")
        self.status_callback(self.status_text())

    def _move_click_worker(self) -> None:
        self.move_click_worker_running = True
        last_reassert = 0.0
        try:
            while self.move_click_enabled and not self.stop_event.is_set():
                hwnd = self.move_click_hwnd or self.click_hwnd or self.target_hwnd
                if not hwnd or not self.user32.IsWindow(hwnd):
                    self.disable_move_click("janela perdida")
                    break
                now = time.monotonic()
                if now - last_reassert >= 0.20:
                    last_reassert = now
                    button = MOUSE_BUTTONS["Esquerdo"]
                    lparam = self.move_click_lparam or self.make_lparam(self.click_x, self.click_y)
                    self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
                    self.user32.PostMessageW(hwnd, button["down"], button["mk"], lparam)
                time.sleep(0.025)
        finally:
            self.move_click_worker_running = False
            if not self.move_click_enabled:
                self.disable_move_click("worker stop")



    def toggle_artillery(self) -> None:
        if self.artillery_enabled:
            self.disable_artillery(f"{self.artillery_hotkey_name} off")
        else:
            self.enable_artillery()

    def enable_artillery(self) -> None:
        if not self.mode_is_enabled("artillery"):
            self.log(f"{self.artillery_hotkey_name} ignorado: modo desativado")
            self.status_callback(self.status_text())
            return
        self.pause()
        self.disable_fixed_click("artillery on")
        self.disable_w_hold("artillery on")
        self.disable_right_hold("artillery on")
        self.use_foxhole_window()
        self.artillery_enabled = True
        self.waiting_for_foxhole = False
        self.log(f"{self.artillery_hotkey_name} on: artilharia ativa")
        self.status_callback(self.status_text())

    def disable_artillery(self, reason: str) -> None:
        if not self.artillery_enabled:
            return
        self.artillery_enabled = False
        self.waiting_for_foxhole = False
        self.log(f"{self.artillery_hotkey_name} off: {reason}")
        self.status_callback(self.status_text())

    def artillery_step(self) -> None:
        hwnd = self.click_hwnd or self.target_hwnd
        if not hwnd:
            return
        self._post_key(hwnd, VK_R, down=True)
        time.sleep(self.artillery_key_delay)
        self._post_key(hwnd, VK_R, down=False)
        time.sleep(0.08)
        self.click_at(hwnd, self.click_x, self.click_y, "Esquerdo", include_shift=False)

    def toggle_right_hold(self) -> None:
        if self.right_hold_enabled:
            self.disable_right_hold(f"{self.right_hold_hotkey_name} off")
        else:
            self.enable_right_hold()

    def enable_right_hold(self) -> None:
        if self.right_hold_enabled:
            return
        if not self.mode_is_enabled("right_hold"):
            self.log("Right Hold ignorado: modo desativado")
            self.status_callback(self.status_text())
            return
        self.pause()
        self.disable_fixed_click("right hold on")
        self.disable_artillery("right hold on")
        self.disable_w_hold("right hold on")
        self.use_foxhole_window(quiet=True)
        hwnd = self.click_hwnd or self.target_hwnd
        if not hwnd:
            self.log("Right Hold abortado: sem janela alvo")
            self.status_callback(self.status_text())
            return
        self.right_hold_enabled = True
        self.right_hold_hwnd = hwnd
        self.right_hold_lparam = self.make_lparam(self.click_x, self.click_y)
        self._set_right_hold_button(True)
        self.log(f"Right Hold ON ({self.right_hold_hotkey_name}): Esc/hotkey para parar")
        self.status_callback(self.status_text())
        if not self.right_hold_worker_running:
            threading.Thread(target=self._right_hold_worker, daemon=True).start()

    def disable_right_hold(self, reason: str) -> None:
        if not self.right_hold_enabled and not self.right_hold_button_down:
            return
        self.right_hold_enabled = False
        self._set_right_hold_button(False)
        self.right_hold_hwnd = 0
        self.right_hold_lparam = 0
        self.log(f"Right Hold OFF: {reason}")
        self.status_callback(self.status_text())

    def _set_right_hold_button(self, down: bool) -> None:
        if down == self.right_hold_button_down:
            return
        hwnd = self.right_hold_hwnd or self.click_hwnd or self.target_hwnd
        button = MOUSE_BUTTONS["Direito"]
        lparam = self.right_hold_lparam or self.make_lparam(self.click_x, self.click_y)
        if hwnd:
            self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
            self.user32.PostMessageW(hwnd, button["down" if down else "up"], button["mk"] if down else 0, lparam)
        self.right_hold_button_down = down

    def _right_hold_worker(self) -> None:
        self.right_hold_worker_running = True
        last_reassert = 0.0
        try:
            while self.right_hold_enabled and not self.stop_event.is_set():
                hwnd = self.right_hold_hwnd or self.click_hwnd or self.target_hwnd
                if not hwnd or not self.user32.IsWindow(hwnd):
                    self.disable_right_hold("janela perdida")
                    break
                now = time.monotonic()
                if now - last_reassert >= 0.20:
                    last_reassert = now
                    self.right_hold_button_down = False
                    self._set_right_hold_button(True)
                time.sleep(0.04)
        finally:
            self.right_hold_worker_running = False
            if not self.right_hold_enabled:
                self._set_right_hold_button(False)

    # -----------------------------------------------------------------------
    # W-HOLD MODE (F4 ou duplo-toque W)
    # Usa PostMessageW direto na janela do jogo (funciona mesmo sem foco)
    # Parar: F4 de novo, apertar W fisicamente, ou Esc
    # Pausar: segurar S (solta W), soltar S (retoma W)
    # -----------------------------------------------------------------------
    def toggle_w_hold(self) -> None:
        if self.w_hold_enabled:
            self.disable_w_hold(f"{self.pilot_hotkey_name} off")
        else:
            self.enable_w_hold()

    # legacy compat
    def toggle_pilot(self) -> None:
        self.toggle_w_hold()

    def enable_pilot(self) -> None:
        self.enable_w_hold()

    def _post_key(self, hwnd: int, vk: int, *, down: bool) -> None:
        """Send WM_KEYDOWN or WM_KEYUP directly to the game window via PostMessageW."""
        scan = self.user32.MapVirtualKeyW(vk, 0)
        if down:
            lparam = 1 | (scan << 16)
            self.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, lparam)
        else:
            lparam = 1 | (scan << 16) | (0xC0 << 24)
            self.user32.PostMessageW(hwnd, WM_KEYUP, vk, lparam)

    def enable_w_hold(self) -> None:
        if self.w_hold_enabled:
            return
        if not self.mode_is_enabled("pilot"):
            self.log("W-Hold ignorado: modo desativado")
            self.status_callback(self.status_text())
            return
        self.pause()
        self.disable_fixed_click("pilot on")
        self.disable_artillery("pilot on")
        self.disable_right_hold("pilot on")
        self.use_foxhole_window(quiet=True)
        self.w_hold_enabled = True
        self.pilot_w_paused = False
        self.w_hold_hwnd = self.click_hwnd or self.target_hwnd
        self._set_w_hold_key(True)
        self.log(f"W-Hold ON ({self.pilot_hotkey_name}): F4/Esc para parar, S pausa")
        self.status_callback(self.status_text())
        if not self.w_hold_worker_running:
            threading.Thread(target=self._w_hold_worker, daemon=True).start()

    def disable_w_hold(self, reason: str) -> None:
        if not self.w_hold_enabled and not self.w_hold_key_down:
            return
        self.w_hold_enabled = False
        self.pilot_w_paused = False
        self._set_w_hold_key(False)
        self.w_hold_hwnd = 0
        self.log(f"W-Hold OFF: {reason}")
        self.status_callback(self.status_text())

    def _set_w_hold_key(self, down: bool) -> None:
        if down == self.w_hold_key_down:
            return
        hwnd = self.w_hold_hwnd or self.click_hwnd or self.target_hwnd
        if hwnd:
            self._post_key(hwnd, self._w_hold_vk, down=down)
        self.user32.keybd_event(self._w_hold_vk, 0, 0 if down else 0x0002, 0)
        self.w_hold_key_down = down

    def _w_hold_worker(self) -> None:
        self.w_hold_worker_running = True
        prev_s = False
        last_reassert = 0.0
        try:
            while self.w_hold_enabled and not self.stop_event.is_set():
                s_down = bool(self.user32.GetAsyncKeyState(VK_S) & 0x8000)

                if s_down and not prev_s and not self.pilot_w_paused:
                    self.pilot_w_paused = True
                    self._set_w_hold_key(False)
                    self.log("W-Hold: pausado (S pressionado)")
                    self.status_callback(self.status_text())

                if not s_down and prev_s and self.pilot_w_paused and self.w_hold_enabled:
                    self.pilot_w_paused = False
                    self._set_w_hold_key(True)
                    self.log("W-Hold: retomado (S solto)")
                    self.status_callback(self.status_text())

                now = time.monotonic()
                if self.w_hold_enabled and not self.pilot_w_paused and now - last_reassert >= 0.20:
                    last_reassert = now
                    hwnd = self.w_hold_hwnd or self.click_hwnd or self.target_hwnd
                    if hwnd:
                        self._post_key(hwnd, self._w_hold_vk, down=True)

                prev_s = s_down
                time.sleep(0.03)
        finally:
            self.w_hold_worker_running = False
            if not self.w_hold_enabled:
                self._set_w_hold_key(False)

    def _w_doubletap_monitor(self) -> None:
        """Background thread: detects W double-tap.
        NOTE: Cannot use GetAsyncKeyState(VK_W) when w_hold is active via keybd_event,
        because keybd_event itself sets the async key state. Instead, we track rising
        edges of VK_W only when w_hold is NOT active.
        """
        prev_w = False
        last_tap = 0.0
        while not self.stop_event.is_set():
            if self.w_hold_enabled:
                # While holding W via keybd_event, skip detection to avoid false triggers
                prev_w = True  # treat as "held" so we don't see a false rising edge after disable
                time.sleep(0.02)
                continue

            w_down = bool(self.user32.GetAsyncKeyState(self._w_hold_vk) & 0x8000)
            if w_down and not prev_w:
                now = time.monotonic()
                if self.mode_is_enabled("pilot") and self.w_doubletap_enabled and (now - last_tap) <= self.w_double_tap_threshold:
                    self.enable_w_hold()
                last_tap = now
            prev_w = w_down
            time.sleep(0.01)

    def _keyboard_hook_loop(self) -> None:
        self.keyboard_hook_thread_id = int(self.kernel32.GetCurrentThreadId() or 0)
        hook_proc_type = ctypes.WINFUNCTYPE(wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        def hook_proc(code: int, w_param: int, l_param: int) -> int:
            try:
                if code >= 0 and int(w_param) in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    is_injected = bool(event.flags & LLKHF_INJECTED)
                    if event.vkCode == int(self._w_hold_vk) and not is_injected and self.w_hold_enabled:
                        self.disable_w_hold("cancel: W")
            except Exception:
                pass
            return self.user32.CallNextHookEx(self.keyboard_hook_handle, code, w_param, l_param)

        self.keyboard_hook_proc = hook_proc_type(hook_proc)
        self.keyboard_hook_handle = int(self.user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.keyboard_hook_proc, 0, 0) or 0)
        if not self.keyboard_hook_handle:
            self.log("Keyboard hook indisponivel; W-Hold ainda cancela por F4/Esc/S")
            return

        message = wintypes.MSG()
        while not self.stop_event.is_set():
            result = self.user32.GetMessageW(ctypes.byref(message), 0, 0, 0)
            if result <= 0:
                break
            self.user32.TranslateMessage(ctypes.byref(message))
            self.user32.DispatchMessageW(ctypes.byref(message))
        self.keyboard_hook_thread_id = 0

    def _right_mouse_action_loop(self) -> None:
        while not self.stop_event.is_set():
            action = self.right_mouse_action_queue.get()
            if action is None:
                break
            try:
                if action == "enable":
                    self.enable_right_hold()
                elif action == "cancel":
                    self.disable_right_hold("cancel: right click")
            except Exception as exc:
                self.log(f"Erro na acao do botao direito: {exc}")

    def _queue_right_mouse_action(self, action: str) -> None:
        try:
            self.right_mouse_action_queue.put(action)
        except Exception:
            pass

    def _mouse_hook_loop(self) -> None:
        self.mouse_hook_thread_id = int(self.kernel32.GetCurrentThreadId() or 0)
        hook_proc_type = ctypes.WINFUNCTYPE(wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        def hook_proc(code: int, w_param: int, l_param: int) -> int:
            try:
                if code >= 0:
                    event = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    is_injected = bool(event.flags & LLMHF_INJECTED)
                    if not is_injected and self._handle_right_mouse_hook_message(int(w_param)):
                        return 1
            except Exception:
                pass
            return self.user32.CallNextHookEx(self.mouse_hook_handle, code, w_param, l_param)

        self.mouse_hook_proc = hook_proc_type(hook_proc)
        self.mouse_hook_handle = int(self.user32.SetWindowsHookExW(WH_MOUSE_LL, self.mouse_hook_proc, 0, 0) or 0)
        if not self.mouse_hook_handle:
            self.log("Mouse hook indisponivel; duplo RMB nao consegue absorver o segundo clique")
            return

        message = wintypes.MSG()
        while not self.stop_event.is_set():
            result = self.user32.GetMessageW(ctypes.byref(message), 0, 0, 0)
            if result <= 0:
                break
            self.user32.TranslateMessage(ctypes.byref(message))
            self.user32.DispatchMessageW(ctypes.byref(message))
        self.mouse_hook_thread_id = 0

    def _handle_right_mouse_hook_message(self, message: int) -> bool:
        right_down = MOUSE_BUTTONS["Direito"]["down"]
        right_up = MOUSE_BUTTONS["Direito"]["up"]

        if message == right_up and self.right_suppress_next_up:
            self.right_suppress_next_up = False
            return True

        if message != right_down:
            return False

        if self.right_hold_enabled:
            self.right_last_tap = 0.0
            if self.is_foxhole_foreground_window():
                self._queue_right_mouse_action("cancel")
            return False

        if not self._right_doubletap_context_active():
            self.right_last_tap = 0.0
            return False

        now = time.monotonic()
        if self.right_last_tap and (now - self.right_last_tap) <= self.right_double_tap_threshold:
            self.right_last_tap = 0.0
            self.right_suppress_next_up = True
            self._queue_right_mouse_action("enable")
            return True

        self.right_last_tap = now
        return False

    def _right_doubletap_context_active(self) -> bool:
        return bool(
            self.mode_is_enabled("right_hold")
            and self.right_doubletap_enabled
            and self.is_foxhole_foreground_window()
        )

    def is_foxhole_foreground_window(self) -> bool:
        hwnd = int(self.user32.GetForegroundWindow() or 0)
        return bool(hwnd and self.is_foxhole_window(hwnd))


    # -----------------------------------------------------------------------
    # LEGADO (usado por configure_action_hotkeys como forward_sequence compat)
    # -----------------------------------------------------------------------
    def run_forward_sequence(self) -> None:
        """Legacy: just toggle pilot now."""
        self.toggle_pilot()

    def open_orders_menu(self) -> None:
        self.log("F5: abrir menu ordens/estoques")
        if self.menu_callback:
            try:
                self.menu_callback()
            except Exception as exc:
                self.log(f"F5 callback falhou: {exc}")

    def trigger_slot_click(self, slot: int) -> None:
        if slot not in self.slot_positions:
            return
        self.refresh_target_if_needed()
        hwnd = self.target_hwnd
        if not hwnd:
            self.log(f"Slot {slot} ignorado: sem target")
            return
        x, y = self.slot_positions[slot]
        self.click_at(hwnd, x, y, "Esquerdo")
        self.log(f"Slot {slot} clicado em {x},{y}")

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
            if window_at_cursor and self.is_same_process_window(window_at_cursor, self.target_hwnd):
                self.click_hwnd = window_at_cursor
                client_point = POINT(point.x, point.y)
                if self.user32.ScreenToClient(self.click_hwnd, ctypes.byref(client_point)):
                    if self.is_point_inside_client(client_point.x, client_point.y):
                        self.click_x = max(0, client_point.x)
                        self.click_y = max(0, client_point.y)
                        return

        rect = RECT()
        if self.user32.GetClientRect(self.target_hwnd, ctypes.byref(rect)):
            self.click_hwnd = self.find_child_at_point(self.target_hwnd, (rect.right - rect.left) // 2, (rect.bottom - rect.top) // 2)
            self.click_x = max(0, (rect.right - rect.left) // 2)
            self.click_y = max(0, (rect.bottom - rect.top) // 2)
            return

        self.click_hwnd = self.target_hwnd
        self.click_x = 0
        self.click_y = 0

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
            return
        self.click_at(hwnd, self.click_x, self.click_y, self.mouse_button)

    def click_at(self, hwnd: int, x: int, y: int, mouse_button: str, *, include_shift: bool = True) -> None:
        button = MOUSE_BUTTONS.get(mouse_button, MOUSE_BUTTONS["Esquerdo"])
        lparam = self.make_lparam(x, y)
        shift_active = bool(include_shift and self.shift_modifier_active())
        modifiers = button["mk"] | (MK_SHIFT if shift_active else 0)
        move_sent = self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        down_sent = self.user32.PostMessageW(hwnd, button["down"], modifiers, lparam)
        up_sent = self.user32.PostMessageW(hwnd, button["up"], 0, lparam)
        if down_sent and up_sent:
            self.click_count += 1
            if self.click_count == 1 or self.click_count % 20 == 0:
                self.log(f"Clique enviado #{self.click_count}: hwnd={hwnd} ponto={x},{y} move={bool(move_sent)} shift={shift_active}")
        else:
            error = self.kernel32.GetLastError()
            self.log(f"Falha clique hwnd={hwnd} ponto={x},{y} erro={error}")

    def send_key_pair(self, vk: int) -> None:
        self.key_down(vk)
        time.sleep(0.02)
        self.key_up(vk)

    def key_down(self, vk: int) -> None:
        # Global key simulation - practical for F4 sequence.
        self.user32.keybd_event(vk, 0, 0, 0)

    def key_up(self, vk: int) -> None:
        self.user32.keybd_event(vk, 0, 0x0002, 0)

    @staticmethod
    def make_lparam(x: int, y: int) -> int:
        return (y & 0xFFFF) << 16 | (x & 0xFFFF)
