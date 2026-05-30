import ctypes
from dataclasses import dataclass
from pathlib import Path
import re


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


@dataclass
class DiscordStatus:
    found: bool = False
    title: str = ""
    process_name: str = ""
    hwnd: int = 0
    call_hint: str = ""
    people_count: int | None = None


class DiscordWindowReader:
    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def get_status(self) -> DiscordStatus:
        windows = self.find_discord_windows()
        if not windows:
            return DiscordStatus(call_hint="Discord nao encontrado")

        foreground = self.user32.GetForegroundWindow()
        selected = next((item for item in windows if item.hwnd == foreground), windows[0])
        selected.call_hint = self.describe_window(selected.title)
        selected.people_count = self.extract_people_count(selected.title)
        return selected

    def find_discord_windows(self) -> list[DiscordStatus]:
        matches: list[DiscordStatus] = []
        enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_proc(hwnd, _lparam):
            if not self.user32.IsWindowVisible(hwnd):
                return True

            process_name = self.get_window_process_name(hwnd)
            if "discord" not in process_name.lower():
                return True

            title = self.get_window_title(hwnd)
            if title or process_name:
                matches.append(
                    DiscordStatus(
                        found=True,
                        title=title,
                        process_name=process_name,
                        hwnd=hwnd,
                    )
                )
            return True

        self.user32.EnumWindows(enum_proc_type(enum_proc), 0)
        return matches

    def get_window_title(self, hwnd: int) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value.strip()

    def get_window_process_name(self, hwnd: int) -> str:
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
                return Path(path_buffer.value).name
            return ""
        finally:
            self.kernel32.CloseHandle(process_handle)

    @staticmethod
    def describe_window(title: str) -> str:
        clean_title = " ".join(title.split())
        if not clean_title:
            return "Discord aberto, sem titulo visivel"

        lowered = clean_title.lower()
        if any(word in lowered for word in ("voice", "voz", "call", "chamada")):
            return f"Possivel call: {clean_title}"
        if "discord" in lowered:
            return clean_title
        return f"Canal/janela: {clean_title}"

    @staticmethod
    def extract_people_count(title: str) -> int | None:
        lowered = title.lower()
        patterns = (
            r"(\d+)\s+pessoas",
            r"(\d+)\s+people",
            r"(\d+)\s+members",
            r"(\d+)\s+membros",
        )
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return int(match.group(1))
        return None


def get_discord_status() -> DiscordStatus:
    return DiscordWindowReader().get_status()
