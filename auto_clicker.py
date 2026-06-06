import ctypes
import random
from pathlib import Path
import threading
import time


DEBUG_CONSOLE = True
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
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002

VK_W = 0x57
VK_A = 0x41
VK_S = 0x53
VK_D = 0x44
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
VK_S = 0x53


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


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
        self.last_pilot_until = 0.0
        # Pilot toggle mode: holds W, Enter to enter vehicle, S pauses W
        self.pilot_enabled = False
        self.pilot_w_paused = False
        self.pilot_w_hwnd = 0

        # W double-tap to hold W mode
        self.w_hold_enabled = False
        self.w_hold_hwnd = 0
        self.w_last_tap = 0.0
        self.w_double_tap_threshold = 0.35  # seconds between taps
        self.w_doubletap_enabled = True  # can be toggled from UI

        # Shift hold with autoclick
        self.shift_enabled = False

        # Artilharia: R + Left Click
        self.artillery_hotkey_name = "F7"
        self.artillery_hotkey_vk = ACTION_KEYS[self.artillery_hotkey_name]
        self.artillery_enabled = False

        # F2 - move-click segurando esquerdo
        self.move_click_enabled = False
        self.move_click_holding = False
        self.move_click_hwnd = 0
        self.move_click_lparam = 0

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
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
        self.user32.PostMessageW.restype = ctypes.c_bool
        self.user32.WindowFromPoint.argtypes = [POINT]
        self.user32.WindowFromPoint.restype = ctypes.c_void_p
        self.user32.ChildWindowFromPointEx.argtypes = [ctypes.c_void_p, POINT, ctypes.c_uint]
        self.user32.ChildWindowFromPointEx.restype = ctypes.c_void_p

        self.monitor_thread = threading.Thread(target=self.monitor_hotkeys, daemon=True)
        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.monitor_thread.start()
        self.click_thread.start()
        self.log("AutoClicker iniciado")

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

    def configure_action_hotkeys(self, move_hotkey: str, fixed_hotkey: str, pilot_hotkey: str, artillery_hotkey: str = "F7") -> None:
        self.move_hotkey_name = move_hotkey if move_hotkey in ACTION_KEYS else "F2"
        self.fixed_hotkey_name = fixed_hotkey if fixed_hotkey in ACTION_KEYS else "F6"
        self.pilot_hotkey_name = pilot_hotkey if pilot_hotkey in ACTION_KEYS else "F4"
        self.artillery_hotkey_name = artillery_hotkey if artillery_hotkey in ACTION_KEYS else "F7"
        self.move_hotkey_vk = ACTION_KEYS[self.move_hotkey_name]
        self.fixed_hotkey_vk = ACTION_KEYS[self.fixed_hotkey_name]
        self.pilot_hotkey_vk = ACTION_KEYS[self.pilot_hotkey_name]
        self.artillery_hotkey_vk = ACTION_KEYS[self.artillery_hotkey_name]
        self.log(
            f"Hotkeys extras: move={self.move_hotkey_name} "
            f"fixed={self.fixed_hotkey_name} pilot={self.pilot_hotkey_name}"
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
        self.stop_event.set()
        self.log("Parando AutoClicker")

    def status_text(self) -> str:
        running = self.enabled or self.fixed_click_enabled or self.artillery_enabled or self.pilot_enabled or self.w_hold_enabled
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
        if time.monotonic() < self.last_pilot_until:
            mode.append(self.pilot_hotkey_name)
        if self.artillery_enabled:
            mode.append(self.artillery_hotkey_name)
        if self.pilot_enabled:
            mode.append(f"{self.pilot_hotkey_name}:PILOTO{'(S=PAUSE)' if self.pilot_w_paused else ''}")
        if self.w_hold_enabled:
            mode.append("W-HOLD")
        if self.shift_enabled:
            mode.append("SHIFT")
        mode_text = ",".join(mode) if mode else "-"
        return f"{state} | {target} | virtual {point} | cliques {self.click_count} | {self.hotkey_name} | {self.interval:.2f}s | {mode_text}"

    def monitor_hotkeys(self) -> None:
        watch_keys = [
            self.hotkey_vk,
            self.move_hotkey_vk,
            self.pilot_hotkey_vk,
            self.fixed_hotkey_vk,
            self.artillery_hotkey_vk,
            HOTKEYS["F5"],
            VK_1, VK_2, VK_3, VK_4,
        ]
        for vk in watch_keys:
            self.key_was_down[vk] = False

        # W double-tap monitoring runs in its own thread
        threading.Thread(target=self._w_doubletap_monitor, daemon=True).start()

        while not self.stop_event.is_set():
            self.handle_key_press(self.move_hotkey_vk, self.toggle_move_click)
            self.handle_key_press(self.hotkey_vk, self.toggle)
            self.handle_key_press(self.fixed_hotkey_vk, self.toggle_fixed_click)
            self.handle_key_press(self.pilot_hotkey_vk, self.toggle_w_hold)  # F4 = segurar W
            self.handle_key_press(self.artillery_hotkey_vk, self.toggle_artillery)
            self.handle_key_press(HOTKEYS["F5"], self.open_orders_menu)

            if self.fixed_click_enabled:
                self.handle_key_press(VK_1, lambda: self.trigger_slot_click(1))
                self.handle_key_press(VK_2, lambda: self.trigger_slot_click(2))
                self.handle_key_press(VK_3, lambda: self.trigger_slot_click(3))
                self.handle_key_press(VK_4, lambda: self.trigger_slot_click(4))

            self.check_cancel_shortcuts()
            time.sleep(0.03)

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
        wasd = any(bool(self.user32.GetAsyncKeyState(vk) & 0x8000) for vk in (VK_W, VK_A, VK_S, VK_D))

        if self.move_click_enabled and (esc or lbtn or rbtn or mbtn):
            self.disable_move_click("cancel: esc/outro clique")

        # Double-click fixo cancela com mouse/asd/esc (W excludido pois w_hold usa W)
        asd = any(bool(self.user32.GetAsyncKeyState(vk) & 0x8000) for vk in (VK_A, VK_S, VK_D))
        if self.fixed_click_enabled and (esc or lbtn or rbtn or mbtn or asd):
            self.disable_fixed_click("cancel: mouse/asd/esc")

        if self.artillery_enabled and (esc or rbtn or mbtn):
            self.disable_artillery("cancel: esc")

        # W-hold cancels on Esc only (not on W press — that would cancel itself)
        if self.w_hold_enabled and esc:
            self.disable_w_hold("cancel: esc")

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
                    time.sleep(self.interval)
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
        self.use_foxhole_window()
        hwnd = self.click_hwnd or self.target_hwnd
        if not hwnd:
            self.log("F2 on abortado: sem janela alvo")
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
        else:
            self.log(f"{self.move_hotkey_name} falhou ao segurar esquerdo")

    def disable_move_click(self, reason: str) -> None:
        if not self.move_click_enabled:
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



    def toggle_artillery(self) -> None:
        if self.artillery_enabled:
            self.disable_artillery(f"{self.artillery_hotkey_name} off")
        else:
            self.enable_artillery()

    def enable_artillery(self) -> None:
        self.pause()
        self.disable_fixed_click("artillery on")
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
        # Press R
        vk_r = 0x52
        hwnd = self.click_hwnd or self.target_hwnd
        if not hwnd:
            return
        self.send_key_pair(vk_r)
        time.sleep(0.02)
        # Click left
        self.click_at(hwnd, self.click_x, self.click_y, "Esquerdo")

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
        self.use_foxhole_window(quiet=True)
        self.w_hold_enabled = True
        self.pilot_w_paused = False
        self.user32.keybd_event(VK_W, 0, 0, 0)  # global WM_KEYDOWN → Foxhole responds to this
        self.log(f"W-Hold ON ({self.pilot_hotkey_name}) — F4/Esc para parar, S pausa")
        self.status_callback(self.status_text())
        threading.Thread(target=self._w_hold_worker, daemon=True).start()

    def disable_w_hold(self, reason: str) -> None:
        if not self.w_hold_enabled:
            return
        self.w_hold_enabled = False
        self.pilot_w_paused = False
        self.user32.keybd_event(VK_W, 0, 0x0002, 0)  # global WM_KEYUP
        self.log(f"W-Hold OFF: {reason}")
        self.status_callback(self.status_text())

    def _w_hold_worker(self) -> None:
        """Monitors S for pause/resume. Runs while w_hold is active.
        NOTE: We do NOT detect W press here — keybd_event sets GetAsyncKeyState(W)=True,
        so we can't distinguish physical W from our synthetic hold.
        Stop is handled by: F4 (handle_key_press in monitor loop) or Esc (check_cancel).
        """
        prev_s = False
        while self.w_hold_enabled and not self.stop_event.is_set():
            s_down = bool(self.user32.GetAsyncKeyState(VK_S) & 0x8000)

            # S pressed → pause W (keybd_event keyup)
            if s_down and not prev_s and not self.pilot_w_paused:
                self.pilot_w_paused = True
                self.user32.keybd_event(VK_W, 0, 0x0002, 0)
                self.log("W-Hold: pausado (S pressionado)")
                self.status_callback(self.status_text())

            # S released → resume W (keybd_event keydown)
            if not s_down and prev_s and self.pilot_w_paused and self.w_hold_enabled:
                self.pilot_w_paused = False
                self.user32.keybd_event(VK_W, 0, 0, 0)
                self.log("W-Hold: retomado (S solto)")
                self.status_callback(self.status_text())

            prev_s = s_down
            time.sleep(0.03)


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
                time.sleep(0.05)
                continue

            w_down = bool(self.user32.GetAsyncKeyState(VK_W) & 0x8000)
            if w_down and not prev_w:
                now = time.monotonic()
                if self.w_doubletap_enabled and (now - last_tap) <= self.w_double_tap_threshold:
                    self.enable_w_hold()
                last_tap = now
            prev_w = w_down
            time.sleep(0.03)


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

    def click_at(self, hwnd: int, x: int, y: int, mouse_button: str) -> None:
        button = MOUSE_BUTTONS.get(mouse_button, MOUSE_BUTTONS["Esquerdo"])
        lparam = self.make_lparam(x, y)
        if self.shift_enabled:
            self.user32.keybd_event(VK_SHIFT, 0, 0, 0)  # Shift down
        move_sent = self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
        down_sent = self.user32.PostMessageW(hwnd, button["down"], button["mk"], lparam)
        up_sent = self.user32.PostMessageW(hwnd, button["up"], 0, lparam)
        if self.shift_enabled:
            self.user32.keybd_event(VK_SHIFT, 0, 0x0002, 0)  # Shift up
        if down_sent and up_sent:
            self.click_count += 1
            if self.click_count == 1 or self.click_count % 20 == 0:
                self.log(f"Clique enviado #{self.click_count}: hwnd={hwnd} ponto={x},{y} move={bool(move_sent)} shift={self.shift_enabled}")
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
