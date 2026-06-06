from __future__ import annotations

import ctypes
import ctypes.wintypes
from dataclasses import dataclass
import json
from pathlib import Path
import threading
import time
from typing import Any, Callable

from app_paths import user_data_dir





MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
VK_ESCAPE = 0x1B
VK_LWIN = 0x5B
VK_RWIN = 0x5C
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
FOXHOLE_PROCESS_NAMES = ("war-win64-shipping.exe", "foxhole.exe")
FOXHOLE_PATH_HINTS = ("\\steamapps\\common\\foxhole\\", "/steamapps/common/foxhole/")
SW_RESTORE = 9
MACRO_DIR = user_data_dir() / "macros"

MOUSE_VKS = {0x01, 0x02, 0x04, 0x05, 0x06}
KEYS_TO_POLL = [vk for vk in range(1, 255) if vk not in MOUSE_VKS]
MOUSE_BUTTONS = {
    0x01: "left",
    0x02: "right",
    0x04: "middle",
    0x05: "x1",
    0x06: "x2",
}
REPLAY_BLOCKED_KEYS = {VK_LWIN, VK_RWIN, VK_ESCAPE}
REPLAY_BUTTON_UP_FLAGS = {
    "left": MOUSEEVENTF_LEFTUP,
    "right": MOUSEEVENTF_RIGHTUP,
    "middle": MOUSEEVENTF_MIDDLEUP,
    "x1": MOUSEEVENTF_XUP,
    "x2": MOUSEEVENTF_XUP,
}
EXTENDED_KEYS = {
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E,
    0x5B, 0x5C, 0x6F, 0x90, 0x91, 0xA3, 0xA5,
}
VK_NAMES = {
    0x08: "Backspace",
    0x09: "Tab",
    0x0D: "Enter",
    0x10: "Shift",
    0x11: "Ctrl",
    0x12: "Alt",
    0x13: "Pause",
    0x14: "Caps",
    0x1B: "Esc",
    0x20: "Space",
    0x21: "PageUp",
    0x22: "PageDown",
    0x23: "End",
    0x24: "Home",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
    0x2C: "Print",
    0x2D: "Insert",
    0x2E: "Delete",
    0x5B: "Win",
    0x5C: "Win",
    0xA0: "LShift",
    0xA1: "RShift",
    0xA2: "LCtrl",
    0xA3: "RCtrl",
    0xA4: "LAlt",
    0xA5: "RAlt",
    0x60: "Num0",
    0x61: "Num1",
    0x62: "Num2",
    0x63: "Num3",
    0x64: "Num4",
    0x65: "Num5",
    0x66: "Num6",
    0x67: "Num7",
    0x68: "Num8",
    0x69: "Num9",
    0x6A: "Num*",
    0x6B: "Num+",
    0x6D: "Num-",
    0x6E: "Num.",
    0x6F: "Num/",
}
for _code in range(0x30, 0x3A):
    VK_NAMES[_code] = chr(_code)
for _code in range(0x41, 0x5B):
    VK_NAMES[_code] = chr(_code)
for _index in range(1, 25):
    VK_NAMES[0x6F + _index] = f"F{_index}"


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]




@dataclass
class MacroSummary:
    name: str
    path: Path
    duration: float
    events: int
    created_at: str


class MacroRecorder:
    def __init__(self, status_callback: Callable[[str], None] | None = None) -> None:
        self.status_callback = status_callback or (lambda _message: None)
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        try:
            self.winmm = ctypes.windll.winmm
        except Exception:
            self.winmm = None
        self.events: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.recording = False
        self.paused = False
        self.replaying = False
        self.replay_paused = False
        self.stop_record_event = threading.Event()
        self.stop_replay_event = threading.Event()
        self.poll_thread: threading.Thread | None = None
        self.start_time = 0.0
        self.last_move_time = 0.0
        self.last_cursor: tuple[int, int] | None = None
        self.key_down: dict[int, bool] = {}
        self.button_down: dict[str, bool] = {}
        self.active_keys: set[int] = set()
        self.active_buttons: set[str] = set()
        self.replay_pressed_keys: set[int] = set()
        self.replay_pressed_buttons: set[str] = set()
        self.last_activity = "Aguardando entrada"
        self.replay_loop_text = ""
        self.replay_action_text = "Aguardando reproducao"
        self.last_context_ok = False
        self.last_context_status = ""
        self.target_hwnd = 0
        self.user32.MapVirtualKeyW.restype = ctypes.c_uint
        MACRO_DIR.mkdir(parents=True, exist_ok=True)

    def start_recording(self) -> bool:
        if self.recording:
            self.paused = False
            self.status_callback("Gravacao retomada")
            return True
        with self.lock:
            self.events = []
        self.stop_replay()
        self.stop_record_event.clear()
        self.start_time = time.perf_counter()
        self.last_move_time = 0.0
        self.last_cursor = None
        self.key_down = {}
        self.button_down = {}
        self.active_keys = set()
        self.active_buttons = set()
        self.last_activity = "Aguardando entrada"
        self.replay_loop_text = ""
        self.replay_action_text = "Aguardando reproducao"
        self.paused = False
        self.recording = True
        if self.winmm:
            self.winmm.timeBeginPeriod(1)
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()
        self.status_callback("TimeTask armado. Entre no Foxhole para gravar.")
        return True

    def pause_recording(self) -> None:
        if self.recording:
            self.paused = True
            self.status_callback("Gravacao pausada")

    def resume_recording(self) -> None:
        if self.recording:
            self.paused = False
            self.status_callback("Gravacao retomada")

    def stop_recording(self) -> list[dict[str, Any]]:
        if not self.recording:
            return self.snapshot_events()
        self.recording = False
        self.paused = False
        self.stop_record_event.set()
        if self.winmm:
            self.winmm.timeEndPeriod(1)
        self.status_callback("Gravacao parada")
        return self.snapshot_events()

    def snapshot_events(self) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(event) for event in self.events]

    def save_macro(self, name: str, path: Path | None = None) -> Path:
        events = self.snapshot_events()
        safe_name = "".join(char for char in name.strip() if char.isalnum() or char in (" ", "-", "_")).strip()
        if not safe_name:
            safe_name = time.strftime("macro-%Y%m%d-%H%M%S")
        target = path or (MACRO_DIR / f"{safe_name}.json")
        payload = {
            "name": safe_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": round(events[-1]["t"], 3) if events else 0,
            "events": events,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    def load_macro(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        events = data.get("events", [])
        if not isinstance(events, list):
            raise ValueError("Arquivo de macro invalido.")
        return {
            "name": str(data.get("name") or path.stem),
            "created_at": str(data.get("created_at") or ""),
            "duration": float(data.get("duration") or (events[-1].get("t", 0) if events else 0)),
            "events": events,
        }

    def list_macros(self) -> list[MacroSummary]:
        summaries: list[MacroSummary] = []
        for path in sorted(MACRO_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                data = self.load_macro(path)
            except Exception:
                continue
            summaries.append(MacroSummary(str(data["name"]), path, float(data["duration"]), len(data["events"]), str(data["created_at"])))
        return summaries

    def replay_macro(self, path: Path, speed: float = 1.0, repeat: int = 1, delay_between: float = 0.0, stock_path: Path | None = None, stock_interval: int = 1) -> bool:
        data = self.load_macro(path)
        stock_events = self.load_macro(stock_path)["events"] if stock_path else None
        return self.replay_events(data["events"], speed=speed, repeat=repeat, delay_between=delay_between, stock_events=stock_events, stock_interval=stock_interval)

    def replay_events(self, events: list[dict[str, Any]], speed: float = 1.0, repeat: int = 1, delay_between: float = 0.0, stock_events: list[dict[str, Any]] | None = None, stock_interval: int = 1) -> bool:
        if self.replaying:
            return False
        if not events:
            self.status_callback("Macro vazia. Grave e salve uma rota primeiro.")
            return False
        if not self.ensure_foxhole_foreground():
            self.status_callback("Nao encontrei o Foxhole para reproduzir.")
            return False
        self.stop_recording()
        self.stop_replay_event.clear()
        self.replay_paused = False
        self.replay_loop_text = ""
        self.replay_action_text = "Iniciando reproducao"
        self._release_replay_inputs()
        if self.winmm:
            self.winmm.timeBeginPeriod(1)
        threading.Thread(target=self._replay_worker, args=(events, max(0.1, speed), max(0, repeat), delay_between, stock_events, max(1, stock_interval)), daemon=True).start()
        return True

    def pause_replay(self) -> None:
        if self.replaying:
            self.replay_paused = True
            self.status_callback("Reproducao pausada")

    def resume_replay(self) -> None:
        if self.replaying:
            self.replay_paused = False
            self.status_callback("Reproducao retomada")

    def stop_replay(self) -> None:
        if self.replaying:
            self.stop_replay_event.set()
            self._release_replay_inputs()
        self.replay_paused = False

    def _poll_loop(self) -> None:
        while self.recording and not self.stop_record_event.is_set():
            if self.paused:
                time.sleep(0.05)
                continue
            if not self.is_foxhole_active():
                self._set_context_status("Aguardando Foxhole em foco")
                self._reset_input_state()
                time.sleep(0.08)
                continue
            self._set_context_status("Gravando no Foxhole")
            frame_t = self._event_time()
            self._poll_keyboard(frame_t)
            self._poll_mouse(frame_t)
            time.sleep(0.016)

    def _poll_mouse(self, event_t: float | None = None) -> None:
        event_t = self._event_time() if event_t is None else event_t
        point = POINT()
        if self.user32.GetCursorPos(ctypes.byref(point)):
            point_client = POINT(point.x, point.y)
            self.user32.ScreenToClient(self.target_hwnd, ctypes.byref(point_client))
            
            now = time.perf_counter()
            cursor = (int(point_client.x), int(point_client.y))
            if cursor != self.last_cursor and now - self.last_move_time >= 0.035:
                self.last_move_time = now
                self.last_cursor = cursor
                self._append_event({"t": event_t, "type": "mouse_move", "x": cursor[0], "y": cursor[1]})
                self._set_activity(f"Mouse movendo {cursor[0]},{cursor[1]}")
        for vk, button in MOUSE_BUTTONS.items():
            down = bool(self.user32.GetAsyncKeyState(vk) & 0x8000)
            if down != self.button_down.get(button, False):
                self.button_down[button] = down
                if down:
                    self.active_buttons.add(button)
                else:
                    self.active_buttons.discard(button)
                self._append_event({
                    "t": event_t,
                    "type": "mouse_button",
                    "button": button,
                    "action": "down" if down else "up",
                    "x": int(point_client.x),
                    "y": int(point_client.y),
                })
                self._set_activity(f"Mouse {button} {'down' if down else 'up'}")

    def _poll_keyboard(self, event_t: float | None = None) -> None:
        event_t = self._event_time() if event_t is None else event_t
        changed: list[str] = []
        for vk in KEYS_TO_POLL:
            down = bool(self.user32.GetAsyncKeyState(vk) & 0x8000)
            if down != self.key_down.get(vk, False):
                self.key_down[vk] = down
                if down:
                    self.active_keys.add(vk)
                else:
                    self.active_keys.discard(vk)
                changed.append(f"{self.key_name(vk)} {'down' if down else 'up'}")
                scan = int(self.user32.MapVirtualKeyW(vk, 0))
                self._append_event({"t": event_t, "type": "key", "action": "down" if down else "up", "vk": vk, "scan": scan, "extended": vk in EXTENDED_KEYS})
        if changed:
            self._set_activity(", ".join(changed[:4]))


    def _reset_input_state(self) -> None:
        self.key_down = {}
        self.button_down = {}
        self.active_keys = set()
        self.active_buttons = set()
        self.last_cursor = None
        self._set_activity("Aguardando entrada")

    def _set_context_status(self, message: str) -> None:
        if message == self.last_context_status:
            return
        self.last_context_status = message
        self.status_callback(message)

    def _event_time(self) -> float:
        return round(time.perf_counter() - self.start_time, 4)

    def _append_event(self, event: dict[str, Any]) -> None:
        with self.lock:
            self.events.append(event)

    def _set_activity(self, text: str) -> None:
        with self.lock:
            self.last_activity = text

    @staticmethod
    def key_name(vk: int) -> str:
        return VK_NAMES.get(vk, f"VK{vk}")

    def live_status(self) -> str:
        with self.lock:
            active_keys = sorted(self.active_keys)
            key_names = [self.key_name(vk) for vk in active_keys[:8]]
            if len(active_keys) > 8:
                key_names.append(f"+{len(active_keys) - 8}")
            keys = "+".join(key_names)
            buttons = "+".join(sorted(self.active_buttons))
            activity = self.last_activity
        parts = []
        if keys:
            parts.append(f"Teclas: {keys}")
        if buttons:
            parts.append(f"Mouse: {buttons}")
        if activity:
            parts.append(activity)
        text = " | ".join(parts) if parts else "Aguardando entrada"
        return text if len(text) <= 110 else f"{text[:107]}..."

    def replay_status(self) -> str:
        with self.lock:
            text = f"{self.replay_loop_text} | {self.replay_action_text}" if self.replay_loop_text else self.replay_action_text
        return text if len(text) <= 110 else f"{text[:107]}..."

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

    def get_window_title(self, hwnd: int) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def is_foxhole_hwnd(self, hwnd: int) -> bool:
        if not self.user32.IsWindowVisible(hwnd):
            return False
        title = self.get_window_title(hwnd).lower()
        path = self.get_window_process_path(hwnd).lower()
        
        if "discord" in path or "discord" in title:
            return False
        if "gg coalition" in title:
            return False
            
        process_name = Path(path).name.lower() if path else ""
        if process_name in {"foxhole.exe", "foxhole-win64-shipping.exe", "foxholeclient.exe"}:
            return True
        if "steamapps\\common\\foxhole" in path:
            return True
        if "foxhole" in title:
            return True
            
        return False

    def find_foxhole_window(self) -> int:
        if self.target_hwnd and self.user32.IsWindow(self.target_hwnd) and self.is_foxhole_hwnd(self.target_hwnd):
            return self.target_hwnd
        matches: list[int] = []
        enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_proc(hwnd, _lparam):
            if self.user32.IsWindowVisible(hwnd) and self.is_foxhole_hwnd(hwnd):
                matches.append(int(hwnd))
                return False
            return True

        self.user32.EnumWindows(enum_proc_type(enum_proc), 0)
        self.target_hwnd = matches[0] if matches else 0
        return self.target_hwnd

    def ensure_foxhole_foreground(self) -> bool:
        if self.is_foxhole_active():
            return True
        hwnd = self.find_foxhole_window()
        if not hwnd:
            return False
        try:
            self.user32.ShowWindow(hwnd, SW_RESTORE)
            self.user32.SetForegroundWindow(hwnd)
            time.sleep(0.15)
        except Exception:
            pass
        return self.is_foxhole_active()

    def is_foxhole_active(self) -> bool:
        try:
            hwnd = self.user32.GetForegroundWindow()
            active = self.is_foxhole_hwnd(hwnd)
            if active:
                self.target_hwnd = int(hwnd)
            return active
        except Exception:
            return False

    def _snap_to_start_position(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        for event in events:
            if event.get("type") == "mouse_move":
                point = ctypes.wintypes.POINT(int(event["x"]), int(event["y"]))
                self.user32.ClientToScreen(self.target_hwnd, ctypes.byref(point))
                self.user32.SetCursorPos(point.x, point.y)
                time.sleep(0.01)
                break

    def _play_event_list(self, events: list[dict[str, Any]], speed: float) -> bool:
        previous_t = 0.0
        for group_time, group in self.group_replay_events(events):
            if self.stop_replay_event.is_set():
                return False
            while self.replay_paused and not self.stop_replay_event.is_set():
                self._release_replay_inputs()
                time.sleep(0.05)
            if self.stop_replay_event.is_set():
                return False
            delay = max(0.0, (group_time - previous_t) / speed)
            previous_t = group_time
            if delay:
                if self.stop_replay_event.wait(delay):
                    return False
            for event in group:
                self._replay_event(event)
            time.sleep(0.002)
        return True

    def _replay_worker(self, events: list[dict[str, Any]], speed: float, repeat: int, delay_between: float = 0.0, stock_events: list[dict[str, Any]] | None = None, stock_interval: int = 1) -> None:
        self.replaying = True
        self.status_callback("Reproduzindo macro")
        self._set_replay_loop_text("")
        finished_message = "Macro finalizada"
        
        def escape_watcher():
            while self.replaying and not self.stop_replay_event.is_set():
                if self.user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                    self.stop_replay_event.set()
                    break
                time.sleep(0.05)

        threading.Thread(target=escape_watcher, daemon=True).start()
        
        try:
            time.sleep(0.08)
            if not self.ensure_foxhole_foreground():
                finished_message = "Reproducao parada: Foxhole saiu do foco"
                return
            
            iteration = 0
            main_counter = 0
            while True:
                if repeat > 0 and iteration >= repeat:
                    break
                iteration += 1
                main_counter += 1

                loop_str = f"{iteration} de Infinito" if repeat == 0 else f"{iteration} de {repeat}"
                self._set_replay_loop_text(f"Principal ({loop_str})")

                if iteration > 1 and delay_between > 0:
                    self._set_replay_action_text(f"Aguardando {delay_between} segundos...")
                    if self.stop_replay_event.wait(delay_between):
                        finished_message = "Reproducao cancelada"
                        return

                self._set_replay_action_text("Iniciando Principal...")
                if self.stop_replay_event.is_set():
                    finished_message = "Reproducao cancelada"
                    return

                self._snap_to_start_position(events)
                if not self._play_event_list(events, speed):
                    finished_message = "Reproducao cancelada"
                    return
                self._release_replay_inputs()

                if stock_events and main_counter >= stock_interval:
                    main_counter = 0
                    
                    for i in range(3, 0, -1):
                        self._set_replay_action_text(f"Trocando para Estoque em {i}...")
                        if self.stop_replay_event.wait(1.0):
                            finished_message = "Reproducao cancelada"
                            return

                    self._set_replay_loop_text(f"Estoque ({loop_str})")
                    self._set_replay_action_text("Iniciando Estoque...")
                    
                    self._snap_to_start_position(stock_events)
                    if not self._play_event_list(stock_events, speed):
                        finished_message = "Reproducao cancelada"
                        return
                    self._release_replay_inputs()

                    if repeat == 0 or iteration < repeat:
                        for i in range(3, 0, -1):
                            self._set_replay_action_text(f"Trocando para Principal em {i}...")
                            if self.stop_replay_event.wait(1.0):
                                finished_message = "Reproducao cancelada"
                                return
                
        finally:
            self._release_replay_inputs()
            self.replaying = False
            self.replay_paused = False
            self.stop_replay_event.clear()
            if self.winmm:
                self.winmm.timeEndPeriod(1)
            self.status_callback(finished_message)

    def group_replay_events(self, events: list[dict[str, Any]]) -> list[tuple[float, list[dict[str, Any]]]]:
        ordered = sorted(events, key=lambda event: float(event.get("t", 0.0)))
        groups: list[tuple[float, list[dict[str, Any]]]] = []
        current_time: float | None = None
        current_group: list[dict[str, Any]] = []
        for event in ordered:
            event_t = float(event.get("t", 0.0))
            if current_time is None or event_t - current_time <= 0.006:
                if current_time is None:
                    current_time = event_t
                current_group.append(event)
            else:
                groups.append((current_time, sorted(current_group, key=self.replay_priority)))
                current_time = event_t
                current_group = [event]
        if current_time is not None:
            groups.append((current_time, sorted(current_group, key=self.replay_priority)))
        return groups

    @staticmethod
    def replay_priority(event: dict[str, Any]) -> int:
        event_type = event.get("type")
        action = event.get("action")
        if event_type == "key" and action == "down":
            return 0
        if event_type == "mouse_move":
            return 1
        if event_type == "mouse_button" and action == "down":
            return 2
        if event_type == "mouse_button" and action == "up":
            return 3
        if event_type == "key" and action == "up":
            return 4
        return 5

    def _replay_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "mouse_move" or event_type == "mouse_button":
            point = POINT(int(event["x"]), int(event["y"]))
            self.user32.ClientToScreen(self.target_hwnd, ctypes.byref(point))
            self.user32.SetCursorPos(point.x, point.y)
            
        if event_type == "mouse_move":
            self._set_replay_action_text(f"Mouse movendo {int(event['x'])},{int(event['y'])}")
        elif event_type == "mouse_button":
            flag_map = {
                ("left", "down"): MOUSEEVENTF_LEFTDOWN,
                ("left", "up"): MOUSEEVENTF_LEFTUP,
                ("right", "down"): MOUSEEVENTF_RIGHTDOWN,
                ("right", "up"): MOUSEEVENTF_RIGHTUP,
                ("middle", "down"): MOUSEEVENTF_MIDDLEDOWN,
                ("middle", "up"): MOUSEEVENTF_MIDDLEUP,
                ("x1", "down"): MOUSEEVENTF_XDOWN,
                ("x1", "up"): MOUSEEVENTF_XUP,
                ("x2", "down"): MOUSEEVENTF_XDOWN,
                ("x2", "up"): MOUSEEVENTF_XUP,
            }
            flag = flag_map.get((event.get("button"), event.get("action")))
            if flag:
                data = 1 if event.get("button") == "x1" else 2 if event.get("button") == "x2" else 0
                self.user32.mouse_event(flag, 0, 0, data, 0)
                button = str(event.get("button"))
                if event.get("action") == "down":
                    self.replay_pressed_buttons.add(button)
                else:
                    self.replay_pressed_buttons.discard(button)
                self._set_replay_action_text(f"Mouse {event.get('button')} {event.get('action')}")
        elif event_type == "key":
            vk = int(event["vk"])
            if vk in REPLAY_BLOCKED_KEYS:
                self._set_replay_action_text(f"{self.key_name(vk)} ignorado por seguranca")
                return
            flags = KEYEVENTF_KEYUP if event.get("action") == "up" else 0
            if event.get("extended"):
                flags |= KEYEVENTF_EXTENDEDKEY
            scan = int(event.get("scan", 0)) or int(self.user32.MapVirtualKeyW(vk, 0))
            self.user32.keybd_event(vk, scan, flags, 0)
            if event.get("action") == "down":
                self.replay_pressed_keys.add(vk)
            else:
                self.replay_pressed_keys.discard(vk)
            self._set_replay_action_text(f"{self.key_name(int(event['vk']))} {event.get('action')}")

    def _set_replay_action_text(self, text: str) -> None:
        with self.lock:
            self.replay_action_text = text

    def _set_replay_loop_text(self, text: str) -> None:
        with self.lock:
            self.replay_loop_text = text

    def _release_replay_inputs(self) -> None:
        for button in list(self.replay_pressed_buttons):
            flag = REPLAY_BUTTON_UP_FLAGS.get(button)
            if not flag:
                continue
            data = 1 if button == "x1" else 2 if button == "x2" else 0
            try:
                self.user32.mouse_event(flag, 0, 0, data, 0)
            except Exception:
                pass
            self.replay_pressed_buttons.discard(button)
        for vk in list(self.replay_pressed_keys):
            try:
                scan = int(self.user32.MapVirtualKeyW(vk, 0))
                flags = KEYEVENTF_KEYUP
                if vk in EXTENDED_KEYS:
                    flags |= KEYEVENTF_EXTENDEDKEY
                self.user32.keybd_event(vk, scan, flags, 0)
            except Exception:
                pass
            self.replay_pressed_keys.discard(vk)

    def stop(self) -> None:
        self.stop_recording()
        self.stop_replay()
        self._release_replay_inputs()
