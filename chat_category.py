from __future__ import annotations

import io
import json
import os
import re
from datetime import datetime, timezone
import threading
import time
import tkinter as tk
from tkinter import simpledialog, ttk
from pathlib import Path
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from settings_store import load_settings

try:
    from PIL import Image, ImageDraw, ImageSequence, ImageTk
except Exception:  # pragma: no cover - avatar rendering degrades to placeholders.
    Image = None
    ImageDraw = None
    ImageSequence = None
    ImageTk = None

try:
    import customtkinter as ctk
except Exception:  # pragma: no cover - scrollbar falls back to ttk.
    ctk = None


CHAT_API_BASE = "https://archpixel.squareweb.app"
CHAT_LOG_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GG Coalition" / "chat_debug.log"
WHISPER_CACHE_PATH = CHAT_LOG_PATH.with_name("whisper_cache.json")
IMAGE_URL_RE = re.compile(r"https?://[^\s<>\"]+\.(?:png|jpe?g|webp|gif)(?:\?[^\s<>\"]*)?", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_.-]{1,32})")
QUICK_EMOJIS = ("👍", "❤️", "😂", "🔥", "✅", "🫡", "👀", "🚚", "⚠️", "🎯")
COLORS = {
    "bg": "#070b16",
    "text": "#edf6ff",
    "muted": "#99abc4",
    "accent": "#5eead4",
    "accent_2": "#8ab4ff",
    "card": "#111c31",
    "card_2": "#1d3353",
    "soft": "#0e1a2d",
    "line": "#24486d",
    "accent_text": "#041014",
}


def _join_url(path: str) -> str:
    return f"{CHAT_API_BASE.rstrip('/')}/{path.lstrip('/')}"


def _append_chat_log(text: str) -> None:
    try:
        CHAT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        with CHAT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {text}\n")
    except Exception:
        pass


def _truncate(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…[truncated]"


def _http_json(method: str, path: str, *, token: str | None = None, payload: Any | None = None, timeout: int = 15) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "GG Coalition/1.0",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    _append_chat_log(
        f"[http] request method={method} path={path} token={'yes' if token else 'no'} payload={_truncate(json.dumps(payload, ensure_ascii=False)) if payload is not None else 'none'}"
    )
    request = urllib.request.Request(_join_url(path), data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            _append_chat_log(
                f"[http] response method={method} path={path} status={getattr(response, 'status', 'unknown')} headers={dict(response.headers.items())} body={_truncate(body)}"
            )
            try:
                result = json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Resposta JSON invalida em {path}: {body[:200]}") from exc
            _append_chat_log(f"[http] json keys path={path} keys={sorted(result.keys())}")
            return result
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        _append_chat_log(
            f"[http] error method={method} path={path} status={exc.code} reason={exc.reason} body={_truncate(body)}"
        )
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body or 'sem corpo'}") from exc
    except urllib.error.URLError as exc:
        _append_chat_log(f"[http] url error method={method} path={path} reason={exc.reason}")
        raise RuntimeError(f"Erro de rede em {path}: {exc.reason}") from exc


class HomeChatPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.app = app
        self.tr = app.tr
        self.chat_token: str | None = None
        self.chat_user: dict[str, Any] = {}
        self.chats: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []
        self.selected_chat_slug = tk.StringVar(value="")
        self.selected_chat_label = tk.StringVar(value="")
        self.status_var = tk.StringVar(value=self.tr.t("home.chat.connecting"))
        self.input_var = tk.StringVar(value="")
        self.room_title_var = tk.StringVar(value="")
        self.online_var = tk.StringVar(value=self.tr.t("home.chat.online_empty"))
        self.user_name_var = tk.StringVar(value=self.tr.t("home.chat.no_user"))
        self.user_detail_var = tk.StringVar(value="")
        self.refresh_job: str | None = None
        self.presence_job: str | None = None
        self.notification_job: str | None = None
        self.mention_suggest_job: str | None = None
        self.refresh_in_flight = False
        self.auth_in_flight = False
        self.auth_retry_after = 0.0
        self.messages_retry_after = 0.0
        self.send_retry_after = 0.0
        self.messages_in_flight = False
        self.pending_message_slug: str | None = None
        self.avatar_cache: dict[str, tk.PhotoImage] = {}
        self.pending_avatar_requests: set[str] = set()
        self.preview_cache: dict[str, tk.PhotoImage] = {}
        self.gif_preview_frames: dict[str, list[tk.PhotoImage]] = {}
        self.gif_preview_delays: dict[str, list[int]] = {}
        self.gif_animation_jobs: dict[str, str] = {}
        self.pending_preview_requests: set[str] = set()
        self.local_profile_avatar_path = ""
        self.local_profile_avatar: tk.PhotoImage | None = None
        self.message_image_refs: list[tk.PhotoImage] = []
        self.preview_image_refs: list[tk.PhotoImage] = []
        self.avatar_labels_by_url: dict[str, list[tk.Label]] = {}
        self.preview_labels_by_url: dict[str, list[tk.Label]] = {}
        self.chat_tab_buttons: dict[str, tk.Button] = {}
        self.chat_signature: tuple[tuple[str, str, str], ...] = ()
        self.rendered_message_signature: tuple[tuple[str, str, str, str], ...] = ()
        self.first_page_cache: dict[str, dict[str, Any]] = {}
        self.next_message_cursor: str | None = None
        self.loading_older_messages = False
        self.online_users: list[dict[str, Any]] = []
        self.all_chat_users: list[dict[str, Any]] = []
        self.whisper_conversations: list[dict[str, Any]] = []
        self.closed_whisper_ids: set[str] = set()
        self.whisper_messages_cache: dict[str, dict[str, Any]] = {}
        self.whisper_unread_ids: set[str] = set()
        self.mention_suggestions: list[dict[str, Any]] = []
        self.mentions_seen_ids: set[str] = set()
        self.notified_message_ids: set[str] = set()
        self.mention_overlay: tk.Toplevel | None = None
        self.mention_overlay_job: str | None = None
        self.mention_hover_card: tk.Toplevel | None = None
        self.keep_messages_pinned_to_bottom = True
        self.active = False

        self.columnconfigure(0, weight=1)
        self.load_whisper_cache()
        self.build()
        self.log("panel initialized")
        self.log("waiting for steam profile refresh before authenticate")

    def build(self) -> None:
        panel = tk.Frame(self, bg="#07111f", highlightthickness=1, highlightbackground="#203857")
        panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 18))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        header = tk.Frame(panel, bg="#07111f")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        header.columnconfigure(1, weight=1)

        tk.Label(
            header,
            text=self.tr.t("home.chat.title"),
            bg="#07111f",
            fg=COLORS["text"],
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, sticky="w")

        status_row = tk.Frame(header, bg="#07111f")
        status_row.grid(row=0, column=1, sticky="e")
        tk.Label(status_row, textvariable=self.status_var, bg="#10233a", fg="#dce8f7", font=("Segoe UI", 8, "bold"), padx=9, pady=4).pack(side="right")

        account_row = tk.Frame(panel, bg="#0d1729", highlightthickness=1, highlightbackground="#182d49")
        account_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        account_row.columnconfigure(1, weight=1)
        self.avatar_canvas = tk.Canvas(account_row, width=36, height=36, bg="#14243b", highlightthickness=0)
        self.avatar_canvas.grid(row=0, column=0, rowspan=2, sticky="w", padx=(10, 8), pady=8)
        self.draw_avatar_placeholder(self.avatar_canvas, 36)
        self.connected_label = tk.Label(account_row, text=self.tr.t("home.chat.connected_as"), bg="#0d1729", fg="#7f90aa", font=("Segoe UI", 8, "bold"))
        self.connected_label.grid(row=0, column=1, sticky="w", pady=(8, 0))
        tk.Label(account_row, textvariable=self.user_name_var, bg="#0d1729", fg="#edf6ff", font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="w", pady=(0, 8))
        tk.Label(account_row, textvariable=self.user_detail_var, bg="#0d1729", fg="#7f90aa", font=("Segoe UI", 8)).grid(row=0, column=2, rowspan=2, sticky="e", padx=10)
        account_row.grid_remove()

        top_controls = tk.Frame(panel, bg="#07111f")
        top_controls.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        top_controls.columnconfigure(0, weight=1)

        tabs_header = tk.Frame(top_controls, bg="#07111f")
        tabs_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        tabs_header.columnconfigure(1, weight=1)
        self.rooms_label = tk.Label(tabs_header, text=self.tr.t("home.chat.rooms"), bg="#07111f", fg="#8ab4ff", font=("Segoe UI", 9, "bold"))
        self.rooms_label.grid(row=0, column=0, sticky="w")
        self.room_title_label = tk.Label(tabs_header, textvariable=self.room_title_var, bg="#07111f", fg="#7f90aa", font=("Segoe UI", 9))
        self.room_title_label.grid(row=0, column=1, sticky="e")

        online_row = tk.Frame(top_controls, bg="#07111f")
        online_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        online_row.columnconfigure(1, weight=1)
        self.online_label = tk.Label(online_row, text=self.tr.t("home.chat.online"), bg="#07111f", fg="#5eead4", font=("Segoe UI", 8, "bold"))
        self.online_label.grid(row=0, column=0, sticky="w")
        self.online_users_label = tk.Label(online_row, textvariable=self.online_var, bg="#07111f", fg="#99abc4", font=("Segoe UI", 8))
        self.online_users_label.grid(row=0, column=1, sticky="w", padx=(8, 0))
        online_row.grid_remove()

        tabs_shell = tk.Frame(top_controls, bg="#07111f")
        tabs_shell.grid(row=1, column=0, sticky="ew")
        tabs_shell.columnconfigure(0, weight=1)
        self.chat_tabs_canvas = tk.Canvas(tabs_shell, bg="#07111f", height=33, highlightthickness=0, bd=0)
        self.chat_tabs_canvas.grid(row=0, column=0, sticky="ew")
        self.chat_tabs_scrollbar = ttk.Scrollbar(tabs_shell, orient="horizontal", command=self.chat_tabs_canvas.xview, style="Horizontal.TScrollbar")
        self.chat_tabs_scrollbar.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.chat_tabs_canvas.configure(xscrollcommand=self.chat_tabs_scrollbar.set)
        self.chat_tabs_frame = tk.Frame(self.chat_tabs_canvas, bg="#07111f")
        self.chat_tabs_window = self.chat_tabs_canvas.create_window((0, 0), window=self.chat_tabs_frame, anchor="nw")
        self.chat_tabs_frame.bind("<Configure>", self.on_chat_tabs_configure)
        self.chat_tabs_canvas.bind("<Configure>", self.on_chat_tabs_canvas_configure)
        self.chat_tabs_canvas.bind("<MouseWheel>", self.on_chat_tabs_mousewheel, add="+")

        self.refresh_button = tk.Button(
            top_controls,
            text=self.tr.t("home.chat.refresh"),
            command=self.refresh_now,
            bg="#0e1a2d",
            fg="#edf6ff",
            activebackground="#203857",
            activeforeground="#edf6ff",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.refresh_button.grid(row=1, column=1, sticky="e", padx=(10, 0))

        messages_shell = tk.Frame(panel, bg="#07111f")
        messages_shell.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 9))
        messages_shell.columnconfigure(0, weight=1)
        messages_shell.rowconfigure(0, weight=1)
        self.messages_canvas = tk.Canvas(messages_shell, bg="#0b1424", highlightthickness=1, highlightbackground="#1b3554", height=300, bd=0)
        self.messages_canvas.grid(row=0, column=0, sticky="nsew")
        if ctk is not None:
            self.messages_scrollbar = ctk.CTkScrollbar(
                messages_shell,
                orientation="vertical",
                command=self.messages_canvas.yview,
                width=10,
                fg_color="#07111f",
                button_color="#1d3353",
                button_hover_color="#5eead4",
            )
        else:
            self.messages_scrollbar = ttk.Scrollbar(messages_shell, orient="vertical", command=self.messages_canvas.yview, style="Vertical.TScrollbar")
        self.messages_scrollbar.grid(row=0, column=1, sticky="ns")
        self.messages_canvas.configure(yscrollcommand=self.messages_scrollbar.set)
        self.messages_inner = tk.Frame(self.messages_canvas, bg="#0b1424")
        self.messages_window = self.messages_canvas.create_window((0, 0), window=self.messages_inner, anchor="nw")
        self.messages_inner.bind("<Configure>", lambda _event: self.messages_canvas.configure(scrollregion=self.messages_canvas.bbox("all")))
        self.messages_canvas.bind("<Configure>", self.on_messages_canvas_configure)
        self.bind_messages_mousewheel(messages_shell)

        self.messages_empty_label = tk.Label(
            self.messages_inner,
            text=self.tr.t("home.chat.empty"),
            bg="#0b1424",
            fg="#99abc4",
            font=("Segoe UI", 10, "bold"),
            pady=12,
        )
        self.messages_empty_label.pack(fill="x", padx=8, pady=8)

        send_label_row = tk.Frame(panel, bg="#07111f")
        send_label_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 5))
        self.message_label = tk.Label(send_label_row, text=self.tr.t("home.chat.message"), bg="#07111f", fg="#8ab4ff", font=("Segoe UI", 9, "bold"))
        self.message_label.pack(side="left")

        self.emoji_label = tk.Label(send_label_row, text=self.tr.t("home.chat.emoji"), bg="#07111f", fg="#7f90aa", font=("Segoe UI", 8, "bold"))
        self.emoji_label.pack(side="left", padx=(12, 6))
        for emoji in QUICK_EMOJIS:
            tk.Button(
                send_label_row,
                text=emoji,
                command=lambda value=emoji: self.insert_emoji(value),
                bg="#0d1729",
                fg="#edf6ff",
                activebackground="#182d49",
                activeforeground="#edf6ff",
                relief="flat",
                bd=0,
                font=("Segoe UI Emoji", 10),
                padx=6,
                pady=1,
                cursor="hand2",
            ).pack(side="left", padx=(0, 3))
        self.gif_button = tk.Button(
            send_label_row,
            text=self.tr.t("home.chat.gif"),
            command=self.prompt_gif_url,
            bg="#172844",
            fg="#8ab4ff",
            activebackground="#203857",
            activeforeground="#edf6ff",
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
            cursor="hand2",
        )
        self.gif_button.pack(side="right")

        self.mention_popup = tk.Frame(panel, bg="#0d1729", highlightthickness=1, highlightbackground="#24486d")
        self.mention_popup.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.mention_popup.grid_remove()

        send_row = tk.Frame(panel, bg="#0b1424", highlightthickness=1, highlightbackground="#24486d")
        send_row.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 14))
        send_row.columnconfigure(0, weight=1)
        self.message_entry = tk.Entry(
            send_row,
            textvariable=self.input_var,
            bg="#0b1424",
            fg="#edf6ff",
            insertbackground="#5eead4",
            relief="flat",
            font=("Segoe UI", 10),
            highlightthickness=0,
        )
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(10, 8), ipady=9)
        self.message_entry.bind("<Return>", lambda _event: self.send_message())
        self.message_entry.bind("<KeyRelease>", self.on_message_input_changed)
        self.message_entry.bind("<Tab>", self.apply_first_mention_suggestion)
        self.message_entry.bind("<Escape>", lambda _event: self.hide_mention_suggestions())
        self.send_button = tk.Button(
            send_row,
            text=self.tr.t("home.chat.send"),
            command=self.send_message,
            bg="#5eead4",
            fg="#041014",
            activebackground="#8ab4ff",
            activeforeground="#041014",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=8,
            cursor="hand2",
        )
        self.send_button.grid(row=0, column=1, sticky="e", padx=(0, 5), pady=5)

        self.root_panel = panel

    def log(self, message: str) -> None:
        text = f"[Chat] {message}"
        print(text, flush=True)
        _append_chat_log(text)

    def load_whisper_cache(self) -> None:
        try:
            data = json.loads(WHISPER_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        self.whisper_conversations = list(data.get("conversations") or [])
        self.whisper_messages_cache = dict(data.get("messages") or {})
        self.closed_whisper_ids = {str(item) for item in data.get("closed") or []}

    def save_whisper_cache(self) -> None:
        try:
            WHISPER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "conversations": self.whisper_conversations[-30:],
                "messages": self.whisper_messages_cache,
                "closed": sorted(self.closed_whisper_ids),
            }
            WHISPER_CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            self.log(f"whisper cache save failed: {exc}")

    def conversation_id(self, conversation: dict[str, Any]) -> str:
        return str(conversation.get("id") or conversation.get("_id") or conversation.get("conversationId") or "")

    def selected_is_whisper(self) -> bool:
        return self.selected_chat_slug.get().startswith("whisper:")

    def selected_whisper_id(self) -> str:
        value = self.selected_chat_slug.get().strip()
        return value.split(":", 1)[1] if value.startswith("whisper:") else ""

    def whisper_key(self, conversation_id: str) -> str:
        return f"whisper:{conversation_id}"

    def selected_room_slug(self) -> str:
        return "" if self.selected_is_whisper() else self.selected_chat_slug.get().strip()

    def other_whisper_user(self, conversation: dict[str, Any]) -> dict[str, Any]:
        local_id = str(self.chat_user.get("id") or "")
        local_steam = str(self.chat_user.get("steamId") or "")
        for key in ("otherUser", "targetUser", "recipient", "receiver", "user"):
            user = conversation.get(key)
            if isinstance(user, dict):
                return user
        users = conversation.get("users") or conversation.get("participants") or []
        if isinstance(users, list):
            for item in users:
                user = item.get("user") if isinstance(item, dict) and isinstance(item.get("user"), dict) else item
                if not isinstance(user, dict):
                    continue
                if local_id and str(user.get("id") or "") == local_id:
                    continue
                if local_steam and str(user.get("steamId") or "") == local_steam:
                    continue
                return user
        return {}

    def normalize_whisper_message(self, message: dict[str, Any]) -> dict[str, Any]:
        item = dict(message)
        if "user" not in item and isinstance(item.get("sender"), dict):
            item["user"] = item.get("sender")
        return item

    def bind_messages_mousewheel(self, widget: tk.Widget) -> None:
        def on_mousewheel(event) -> str:
            self.messages_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.keep_messages_pinned_to_bottom = self.is_messages_near_bottom()
            return "break"

        if not getattr(widget, "_chat_mousewheel_bound", False):
            widget.bind("<MouseWheel>", on_mousewheel, add="+")
            setattr(widget, "_chat_mousewheel_bound", True)
        for child in widget.winfo_children():
            self.bind_messages_mousewheel(child)

    def on_messages_canvas_configure(self, event) -> None:
        self.messages_canvas.itemconfigure(self.messages_window, width=event.width)
        if self.keep_messages_pinned_to_bottom:
            self.after(0, self.scroll_messages_to_bottom)

    def insert_emoji(self, value: str) -> None:
        try:
            self.message_entry.insert(tk.INSERT, value)
            self.message_entry.focus_set()
        except tk.TclError:
            pass

    def prompt_gif_url(self) -> None:
        url = simpledialog.askstring(
            self.tr.t("home.chat.gif_title"),
            self.tr.t("home.chat.gif_prompt"),
            parent=self,
        )
        if not url:
            return
        current = self.input_var.get().strip()
        separator = " " if current else ""
        self.input_var.set(f"{current}{separator}{url.strip()}")
        self.message_entry.icursor(tk.END)
        self.message_entry.focus_set()

    def on_message_input_changed(self, _event=None) -> None:
        if self.mention_suggest_job:
            try:
                self.after_cancel(self.mention_suggest_job)
            except tk.TclError:
                pass
        self.mention_suggest_job = self.after(120, self.update_mention_suggestions)

    def current_mention_query(self) -> tuple[str, int, int] | None:
        text = self.input_var.get()
        try:
            cursor = self.message_entry.index(tk.INSERT)
        except tk.TclError:
            cursor = len(text)
        prefix = text[:cursor]
        match = None
        for item in MENTION_RE.finditer(prefix):
            match = item
        if not match or match.end() != len(prefix):
            return None
        return match.group(1).casefold(), match.start(), cursor

    def update_mention_suggestions(self) -> None:
        self.mention_suggest_job = None
        query_data = self.current_mention_query()
        if not query_data:
            self.hide_mention_suggestions()
            return
        query, _start, _end = query_data
        users = self.filter_online_users(query)
        self.mention_suggestions = users[:6]
        self.render_mention_suggestions()

    def filter_online_users(self, query: str) -> list[dict[str, Any]]:
        local_steam_id = str(self.chat_user.get("steamId") or getattr(self.app.profile, "steam_id", "") or "")
        scored: list[tuple[int, str, dict[str, Any]]] = []
        seen_users: set[str] = set()
        combined_users = [*self.online_users, *self.all_chat_users]
        for user in combined_users:
            steam_id = str(user.get("steamId") or user.get("steam_id") or "")
            user_id = str(user.get("id") or "")
            unique_key = user_id or steam_id or self.user_mention_name(user).casefold()
            if unique_key in seen_users:
                continue
            seen_users.add(unique_key)
            name = self.user_mention_name(user)
            if steam_id and steam_id == local_steam_id:
                continue
            haystack = f"{name} {user.get('mention') or ''} {steam_id}".casefold()
            if query and query not in haystack:
                continue
            score = 0 if name.casefold().startswith(query) else 1
            scored.append((score, name.casefold(), user))
        scored.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in scored]

    def render_mention_suggestions(self) -> None:
        for child in self.mention_popup.winfo_children():
            child.destroy()
        if not self.mention_suggestions:
            tk.Label(
                self.mention_popup,
                text=self.tr.t("home.chat.no_mention_results"),
                bg="#0d1729",
                fg="#99abc4",
                font=("Segoe UI", 8, "bold"),
                padx=10,
                pady=7,
            ).pack(anchor="w")
            self.mention_popup.grid()
            return
        for user in self.mention_suggestions:
            name = self.user_mention_name(user)
            steam_id = str(user.get("steamId") or user.get("steam_id") or "")
            label = f"@{name}"
            if steam_id:
                label = f"{label}  {steam_id}"
            button = tk.Button(
                self.mention_popup,
                text=label,
                command=lambda item=user: self.insert_mention_user(item),
                bg="#0d1729",
                fg="#edf6ff",
                activebackground="#182d49",
                activeforeground="#5eead4",
                relief="flat",
                bd=0,
                anchor="w",
                font=("Segoe UI", 9, "bold"),
                padx=10,
                pady=5,
                cursor="hand2",
            )
            button.pack(fill="x")
        self.mention_popup.grid()

    def hide_mention_suggestions(self) -> str:
        self.mention_suggestions = []
        try:
            self.mention_popup.grid_remove()
        except tk.TclError:
            pass
        return "break"

    def apply_first_mention_suggestion(self, _event=None) -> str:
        if self.mention_suggestions:
            self.insert_mention_user(self.mention_suggestions[0])
        return "break"

    def insert_mention_user(self, user: dict[str, Any]) -> None:
        query_data = self.current_mention_query()
        if not query_data:
            return
        _query, start, end = query_data
        text = self.input_var.get()
        name = self.user_mention_name(user)
        replacement = f"@{name} "
        self.input_var.set(f"{text[:start]}{replacement}{text[end:]}")
        try:
            self.message_entry.icursor(start + len(replacement))
            self.message_entry.focus_set()
        except tk.TclError:
            pass
        self.hide_mention_suggestions()

    def user_mention_name(self, user: dict[str, Any]) -> str:
        raw = str(user.get("mention") or user.get("personaname") or user.get("nickname") or user.get("name") or "")
        return raw.lstrip("@").strip() or str(user.get("steamId") or user.get("steam_id") or "user")

    def on_chat_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.chats):
            self.log(f"chat selection ignored index={index} chats={len(self.chats)}")
            return
        chat = self.chats[index]
        self.selected_chat_slug.set(str(chat.get("slug") or ""))
        self.selected_chat_label.set(self.format_chat_tab_label(chat))
        self.update_chat_tab_styles()
        self.log(f"chat selected slug={self.selected_chat_slug.get()} label={self.selected_chat_label.get()}")
        self.messages = []
        self.next_message_cursor = None
        self.rendered_message_signature = ()
        self.render_messages(scroll_to_bottom=True)
        self.load_messages()

    def open_whisper_by_id(self, conversation_id: str, *, auto_open: bool = False) -> None:
        if not conversation_id:
            return
        self.closed_whisper_ids.discard(conversation_id)
        key = self.whisper_key(conversation_id)
        self.selected_chat_slug.set(key)
        conversation = self.find_whisper_conversation(conversation_id) or {"id": conversation_id}
        self.selected_chat_label.set(self.format_whisper_tab_label(conversation))
        self.room_title_var.set(self.tr.t("home.chat.current_room", room=self.selected_chat_label.get()))
        self.whisper_unread_ids.discard(conversation_id)
        self.messages = []
        self.next_message_cursor = None
        self.rendered_message_signature = ()
        self.render_chat_tabs()
        self.render_messages(scroll_to_bottom=True)
        self.load_messages()
        self.mark_whisper_read(conversation_id)
        if auto_open and hasattr(self.app, "open_chat_from_overlay"):
            self.app.open_chat_from_overlay()

    def close_whisper_tab(self, conversation_id: str) -> None:
        self.closed_whisper_ids.add(conversation_id)
        self.save_whisper_cache()
        if self.selected_whisper_id() == conversation_id:
            self.selected_chat_slug.set(str(self.chats[0].get("slug") or "") if self.chats else "")
            self.messages = []
            self.rendered_message_signature = ()
            self.load_messages()
        self.render_chat_tabs()

    def find_whisper_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        for conversation in self.whisper_conversations:
            if self.conversation_id(conversation) == conversation_id:
                return conversation
        return None

    def open_whisper_with_user(self, user: dict[str, Any]) -> None:
        if not user or not self.chat_token:
            return
        target_payload: dict[str, str] = {}
        if user.get("id"):
            target_payload["targetUserId"] = str(user.get("id"))
        elif user.get("steamId") or user.get("steam_id"):
            target_payload["targetSteamId"] = str(user.get("steamId") or user.get("steam_id"))
        else:
            target_payload["personaname"] = self.user_mention_name(user)
        self.status_var.set(self.tr.t("home.chat.whisper_opening"))

        def worker() -> None:
            try:
                result = _http_json("POST", "/chat/whispers", token=self.chat_token, payload=target_payload, timeout=12)
                conversation = dict(result.get("conversation") or result.get("whisper") or result)
                self.after(0, self.apply_open_whisper_result, conversation)
            except Exception as exc:
                self.log(f"open whisper error: {exc}")
                self.after(0, self.set_error, self.tr.t("home.chat.whisper_error", message=str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def apply_open_whisper_result(self, conversation: dict[str, Any]) -> None:
        conversation_id = self.conversation_id(conversation)
        if not conversation_id:
            self.set_error(self.tr.t("home.chat.whisper_error", message=self.tr.t("home.chat.missing_conversation")))
            return
        known = {self.conversation_id(item): item for item in self.whisper_conversations if self.conversation_id(item)}
        known[conversation_id] = conversation
        self.whisper_conversations = list(known.values())
        self.save_whisper_cache()
        self.open_whisper_by_id(conversation_id)

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            self.refresh_now()
            self.start_presence()
            self.start_mention_notifications()
        else:
            self.cancel_refresh()
            self.cancel_presence()
            self.cancel_mention_notifications()

    def refresh_language(self, translator) -> None:
        self.tr = translator
        self.log("language refreshed")
        self.apply_current_user_labels()
        self.messages_empty_label.configure(text=self.tr.t("home.chat.empty"))
        self.send_button.configure(text=self.tr.t("home.chat.send"))
        self.refresh_button.configure(text=self.tr.t("home.chat.refresh"))
        self.emoji_label.configure(text=self.tr.t("home.chat.emoji"))
        self.gif_button.configure(text=self.tr.t("home.chat.gif"))
        self.connected_label.configure(text=self.tr.t("home.chat.connected_as"))
        self.rooms_label.configure(text=self.tr.t("home.chat.rooms"))
        self.online_label.configure(text=self.tr.t("home.chat.online"))
        self.message_label.configure(text=self.tr.t("home.chat.message"))
        self.render_online_users()
        self.render_chat_tabs()
        self.sync_selected_chat_label()
        self.render_messages()
        if not self.chat_token and getattr(self.app.profile, "steam_id", None):
            self.status_var.set(self.tr.t("home.chat.auth_needed"))
        elif self.chat_token:
            self.status_var.set(self.tr.t("home.chat.ready"))
        else:
            self.status_var.set(self.tr.t("home.chat.no_steam"))

    def apply_current_user_labels(self) -> None:
        personaname = str(
            self.chat_user.get("personaname")
            or self.chat_user.get("nickname")
            or getattr(self.app.profile, "persona_name", None)
            or getattr(self.app.profile, "account_name", None)
            or self.tr.t("home.chat.no_user")
        )
        steam_id = str(self.chat_user.get("steamId") or getattr(self.app.profile, "steam_id", "") or "")
        self.user_name_var.set(personaname)
        self.user_detail_var.set(steam_id)
        self.apply_local_profile_avatar()

    def apply_local_profile_avatar(self) -> None:
        if self.chat_user.get("avatarfull") or self.chat_user.get("avatarmedium") or self.chat_user.get("avatar"):
            return
        avatar_path = getattr(self.app.profile, "avatar_path", None)
        if not avatar_path:
            return
        path = Path(avatar_path)
        key = str(path)
        if key == self.local_profile_avatar_path and self.local_profile_avatar is not None:
            return
        try:
            if Image and ImageTk:
                image = Image.open(path).convert("RGBA")
                image = image.resize((36, 36))
                photo = ImageTk.PhotoImage(image)
            else:
                photo = tk.PhotoImage(file=str(path))
            self.local_profile_avatar = photo
            self.local_profile_avatar_path = key
            self.avatar_canvas.delete("all")
            self.avatar_canvas.create_image(18, 18, image=photo)
            self.avatar_canvas.image = photo
        except Exception as exc:
            self.log(f"local steam avatar failed {path}: {exc}")

    def refresh_now(self) -> None:
        self.log("refresh requested")
        if self.auth_in_flight or self.messages_in_flight or self.refresh_in_flight:
            self.log(f"refresh skipped auth={self.auth_in_flight} messages={self.messages_in_flight} chats={self.refresh_in_flight}")
            return
        if not self.chat_token and self.app.profile and self.app.profile.steam_id:
            self.log(f"refresh -> authenticate steam_id={self.app.profile.steam_id}")
            self.authenticate()
        else:
            self.log("refresh -> load chats/messages")
            self.load_chats()
            self.load_whispers()
            self.load_all_chat_users()
            if self.selected_is_whisper():
                self.load_messages()
            elif self.selected_chat_slug.get():
                self.load_messages()

    def cancel_refresh(self) -> None:
        if self.refresh_job:
            try:
                self.after_cancel(self.refresh_job)
            except tk.TclError:
                pass
            self.refresh_job = None

    def schedule_refresh(self, delay_ms: int | None = None) -> None:
        self.cancel_refresh()
        if self.active:
            self.refresh_job = self.after(delay_ms or self.next_refresh_delay_ms(), self.poll_refresh)

    def next_refresh_delay_ms(self) -> int:
        retry_seconds = max(0.0, self.messages_retry_after - time.monotonic())
        if retry_seconds > 0:
            return int(retry_seconds * 1000) + 1000
        return 15000

    def poll_refresh(self) -> None:
        self.refresh_job = None
        if not self.active:
            return
        if self.selected_chat_slug.get():
            self.load_messages()
        self.schedule_refresh()

    def load_all_chat_users(self) -> None:
        if not self.chat_token:
            return

        def worker() -> None:
            try:
                result = _http_json("GET", "/chat/users", token=self.chat_token, timeout=12)
                self.after(0, self.apply_all_chat_users, list(result.get("users") or []))
            except Exception as exc:
                self.log(f"chat users error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def apply_all_chat_users(self, users: list[dict[str, Any]]) -> None:
        self.all_chat_users = users

    def start_presence(self) -> None:
        if not self.active:
            return
        self.cancel_presence()
        self.ping_presence()

    def cancel_presence(self) -> None:
        if self.presence_job:
            try:
                self.after_cancel(self.presence_job)
            except tk.TclError:
                pass
            self.presence_job = None

    def schedule_presence(self, delay_ms: int = 30000) -> None:
        self.cancel_presence()
        if self.active:
            self.presence_job = self.after(delay_ms, self.ping_presence)

    def ping_presence(self) -> None:
        self.presence_job = None
        steam_id = str(self.chat_user.get("steamId") or getattr(self.app.profile, "steam_id", "") or "")
        if not steam_id:
            self.schedule_presence(45000)
            return

        def worker() -> None:
            try:
                result = _http_json("POST", "/chat/presence/ping", token=self.chat_token, payload={"steamId": steam_id}, timeout=10)
                users = list(result.get("onlineUsers") or result.get("users") or [])
                self.after(0, self.apply_online_users, users)
            except Exception as exc:
                self.log(f"presence ping error: {exc}")
                self.after(0, self.load_online_users)
            finally:
                self.after(0, self.schedule_presence)

        threading.Thread(target=worker, daemon=True).start()

    def load_online_users(self) -> None:
        def worker() -> None:
            try:
                result = _http_json("GET", "/chat/presence/online", token=self.chat_token, timeout=10)
                self.after(0, self.apply_online_users, list(result.get("users") or []))
            except Exception as exc:
                self.log(f"online users error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def apply_online_users(self, users: list[dict[str, Any]]) -> None:
        self.online_users = users
        self.render_online_users()
        if hasattr(self.app, "update_home_online_users"):
            self.app.update_home_online_users(users)
        if self.mention_popup.winfo_ismapped():
            self.update_mention_suggestions()

    def render_online_users(self) -> None:
        if not self.online_users:
            self.online_var.set(self.tr.t("home.chat.online_empty"))
            return
        local_steam_id = str(self.chat_user.get("steamId") or getattr(self.app.profile, "steam_id", "") or "")
        names: list[str] = []
        for user in self.online_users:
            steam_id = str(user.get("steamId") or user.get("steam_id") or "")
            if steam_id and steam_id == local_steam_id:
                continue
            names.append(f"@{self.user_mention_name(user)}")
            if len(names) >= 5:
                break
        count = len(self.online_users)
        suffix = ", ".join(names) if names else self.tr.t("home.chat.only_you_online")
        self.online_var.set(f"{self.tr.t('home.chat.online_count', count=count)} - {suffix}")

    def start_mention_notifications(self) -> None:
        if not self.active:
            return
        self.cancel_mention_notifications()
        self.notification_job = self.after(2500, self.poll_mention_notifications)

    def cancel_mention_notifications(self) -> None:
        if self.notification_job:
            try:
                self.after_cancel(self.notification_job)
            except tk.TclError:
                pass
            self.notification_job = None

    def schedule_mention_notifications(self, delay_ms: int = 6000) -> None:
        self.cancel_mention_notifications()
        if self.active and self.chat_token:
            self.notification_job = self.after(delay_ms, self.poll_mention_notifications)

    def poll_mention_notifications(self) -> None:
        self.notification_job = None
        if not self.chat_token:
            self.schedule_mention_notifications(15000)
            return

        def worker() -> None:
            try:
                result = _http_json("GET", "/chat/notifications?unreadOnly=true&take=50", token=self.chat_token, timeout=10)
                self.after(0, self.apply_chat_notifications, result)
            except Exception as exc:
                self.log(f"combined notification error: {exc}")
                try:
                    result = _http_json("GET", "/chat/mentions/notifications?unreadOnly=true&take=50", token=self.chat_token, timeout=10)
                    self.after(0, self.apply_mention_notifications, list(result.get("mentions") or []))
                except Exception as inner_exc:
                    self.log(f"mention notification error: {inner_exc}")
            finally:
                self.after(0, self.schedule_mention_notifications)

        threading.Thread(target=worker, daemon=True).start()

    def apply_chat_notifications(self, result: dict[str, Any]) -> None:
        self.apply_mention_notifications(list(result.get("mentions") or []))
        whispers = list(result.get("whispers") or [])
        if whispers:
            self.apply_whisper_notifications(whispers)

    def apply_mention_notifications(self, mentions: list[dict[str, Any]]) -> None:
        received_new_mention = False
        for mention in mentions:
            mention_id = str(mention.get("id") or mention.get("_id") or "")
            if not mention_id or mention_id in self.mentions_seen_ids:
                continue
            self.mentions_seen_ids.add(mention_id)
            received_new_mention = True
            user = mention.get("mentionedBy") or mention.get("fromUser") or mention.get("user") or {}
            message = mention.get("message") or {}
            chat = message.get("chat") or mention.get("chat") or {}
            title = self.tr.t("home.chat.mention_title")
            body = self.tr.t(
                "home.chat.mention_body",
                user=self.user_mention_name(user),
                room=str(chat.get("name") or chat.get("slug") or self.selected_chat_label.get() or "-"),
            )
            self.show_mention_overlay(title, body)
            self.play_mention_sound()
            if mention_id:
                self.mark_mention_read(mention_id)
        if received_new_mention:
            self.refresh_after_mention_notification()

    def refresh_after_mention_notification(self) -> None:
        self.log("mention notification received, refreshing chat")
        if self.selected_chat_slug.get().strip():
            self.load_messages(use_cache=False)
        else:
            self.load_chats()

    def mark_mention_read(self, mention_id: str) -> None:
        def worker() -> None:
            try:
                _http_json("PATCH", f"/chat/mentions/{urllib.parse.quote(mention_id)}/read", token=self.chat_token, timeout=8)
            except Exception as exc:
                self.log(f"mention read error {mention_id}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def apply_whisper_notifications(self, whispers: list[dict[str, Any]]) -> None:
        first_conversation_id = ""
        first_sender: dict[str, Any] = {}
        for whisper in whispers:
            conversation = whisper.get("conversation") if isinstance(whisper.get("conversation"), dict) else {}
            conversation_id = str(whisper.get("conversationId") or whisper.get("conversation_id") or self.conversation_id(conversation))
            if not conversation_id:
                continue
            if not conversation:
                conversation = {
                    "id": conversation_id,
                    "otherUser": whisper.get("otherUser") if isinstance(whisper.get("otherUser"), dict) else whisper.get("sender"),
                }
            if conversation and not self.find_whisper_conversation(conversation_id):
                self.whisper_conversations.append(conversation)
            self.whisper_unread_ids.add(conversation_id)
            message = self.normalize_whisper_message(whisper)
            cached = self.whisper_messages_cache.setdefault(conversation_id, {"messages": [], "nextCursor": None})
            cached_messages = [self.normalize_whisper_message(item) for item in list(cached.get("messages") or [])]
            if all(self.message_identity(item) != self.message_identity(message) for item in cached_messages):
                cached_messages.append(message)
            cached["messages"] = cached_messages[-50:]
            if not first_conversation_id:
                first_conversation_id = conversation_id
                first_sender = whisper.get("sender") if isinstance(whisper.get("sender"), dict) else message.get("user") or {}
        self.save_whisper_cache()
        self.render_chat_tabs()
        if first_conversation_id:
            title = self.tr.t("home.chat.whisper_title")
            body = self.tr.t("home.chat.whisper_body", user=self.user_mention_name(first_sender))
            self.show_mention_overlay(title, body)
            self.play_mention_sound()
            self.open_whisper_by_id(first_conversation_id, auto_open=True)

    def mark_whisper_read(self, conversation_id: str) -> None:
        if not conversation_id or not self.chat_token:
            return
        self.whisper_unread_ids.discard(conversation_id)

        def worker() -> None:
            try:
                _http_json("PATCH", f"/chat/whispers/{urllib.parse.quote(conversation_id)}/read", token=self.chat_token, timeout=8)
            except Exception as exc:
                self.log(f"whisper read error {conversation_id}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def authenticate(self) -> None:
        if self.auth_in_flight:
            self.log("authenticate skipped: already in flight")
            return
        steam_id = getattr(self.app.profile, "steam_id", None)
        self.log(f"authenticate requested steam_id={steam_id!r}")
        if not steam_id:
            self.log("authenticate aborted: missing steam_id")
            self.status_var.set(self.tr.t("home.chat.no_steam"))
            return
        self.apply_current_user_labels()
        retry_seconds = int(max(0, self.auth_retry_after - time.monotonic()))
        if retry_seconds > 0:
            self.log(f"authenticate skipped: retry after {retry_seconds}s")
            self.status_var.set(self.tr.t("home.chat.auth_wait", seconds=retry_seconds))
            return
        self.auth_in_flight = True
        self.status_var.set(self.tr.t("home.chat.authenticating"))

        def worker() -> None:
            try:
                self.log(f"auth request POST /chat/auth/steam steam_id={steam_id}")
                result = _http_json("POST", "/chat/auth/steam", payload={"steamId": steam_id})
                self.log(f"auth response keys={sorted(result.keys())}")
                self.after(0, self.apply_auth_result, result)
            except Exception as exc:
                self.log(f"auth error: {exc}")
                self.after(0, self.handle_auth_error, str(exc))
            finally:
                self.after(0, self.finish_auth_request)

        threading.Thread(target=worker, daemon=True).start()

    def finish_auth_request(self) -> None:
        self.auth_in_flight = False

    def apply_auth_result(self, result: dict[str, Any]) -> None:
        self.auth_retry_after = 0.0
        self.chat_token = str(result.get("token") or "")
        self.chat_user = dict(result.get("user") or {})
        self.log(f"auth applied token={'yes' if self.chat_token else 'no'} user_keys={sorted(self.chat_user.keys())}")
        self.apply_current_user_labels()
        personaname = self.user_name_var.get()
        steam_id = self.user_detail_var.get()
        avatar = str(self.chat_user.get("avatarmedium") or self.chat_user.get("avatarfull") or self.chat_user.get("avatar") or "")
        self.log(f"auth user personaname={personaname!r} steam_id={steam_id!r} avatar={'yes' if avatar else 'no'}")
        self.load_avatar_async(avatar)
        self.status_var.set(self.tr.t("home.chat.connected"))
        self.start_presence()
        self.start_mention_notifications()
        self.load_chats()
        self.load_whispers()
        self.load_all_chat_users()

    def handle_auth_error(self, message: str) -> None:
        self.apply_current_user_labels()
        if "429" in message or "Too Many Requests" in message:
            self.auth_retry_after = time.monotonic() + 75
            self.status_var.set(self.tr.t("home.chat.auth_limited"))
            return
        self.status_var.set(self.tr.t("home.chat.auth_error", message=message))

    def load_chats(self) -> None:
        if self.refresh_in_flight:
            self.log("load chats skipped: already in flight")
            return
        self.refresh_in_flight = True
        self.log("load chats started")

        def worker() -> None:
            try:
                self.log("chat list request GET /chat/chats")
                result = _http_json("GET", "/chat/chats")
                chats = list(result.get("chats") or [])
                self.log(f"chat list response count={len(chats)}")
                self.after(0, self.apply_chats_result, chats)
            except Exception as exc:
                self.log(f"chat list error: {exc}")
                self.after(0, self.set_error, self.tr.t("home.chat.chat_error", message=str(exc)))
            finally:
                self.refresh_in_flight = False

        threading.Thread(target=worker, daemon=True).start()

    def apply_chats_result(self, chats: list[dict[str, Any]]) -> None:
        self.log(f"apply chats count={len(chats)}")
        sorted_chats = sorted(chats, key=lambda item: int(item.get("order") or 0))
        signature = self.chats_signature(sorted_chats)
        self.chats = sorted_chats
        if signature != self.chat_signature:
            self.chat_signature = signature
            self.render_chat_tabs()
        if not self.chats:
            self.log("no chats available")
            self.status_var.set(self.tr.t("home.chat.no_chats"))
            self.selected_chat_slug.set("")
            self.selected_chat_label.set("")
            return
        current = self.selected_chat_slug.get()
        valid_slugs = {str(chat.get("slug") or "") for chat in self.chats}
        valid_slugs.update(self.whisper_key(self.conversation_id(item)) for item in self.whisper_conversations if self.conversation_id(item))
        if current not in valid_slugs:
            current = str(self.chats[0].get("slug") or "")
            self.selected_chat_slug.set(current)
            self.log(f"default chat selected slug={current}")
        self.sync_selected_chat_label()
        self.status_var.set(self.tr.t("home.chat.ready"))
        self.load_messages()

    def load_whispers(self) -> None:
        if not self.chat_token:
            return

        def worker() -> None:
            try:
                result = _http_json("GET", "/chat/whispers", token=self.chat_token, timeout=12)
                self.after(0, self.apply_whispers_result, list(result.get("conversations") or result.get("whispers") or []))
            except Exception as exc:
                self.log(f"whispers list error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def apply_whispers_result(self, conversations: list[dict[str, Any]]) -> None:
        known = {self.conversation_id(item): item for item in self.whisper_conversations if self.conversation_id(item)}
        for conversation in conversations:
            conversation_id = self.conversation_id(conversation)
            if conversation_id:
                known[conversation_id] = conversation
        self.whisper_conversations = list(known.values())
        self.save_whisper_cache()
        self.render_chat_tabs()

    def chats_signature(self, chats: list[dict[str, Any]]) -> tuple[tuple[str, str, str], ...]:
        signature: list[tuple[str, str, str]] = []
        for chat in chats:
            count = chat.get("_count", {}).get("messages")
            signature.append((str(chat.get("slug") or ""), str(chat.get("name") or ""), str(count if count is not None else "")))
        return tuple(signature)

    def format_chat_label(self, chat: dict[str, Any]) -> str:
        name = str(chat.get("name") or chat.get("slug") or "-")
        count = chat.get("_count", {}).get("messages")
        if isinstance(count, int):
            return f"{name} ({count})"
        return name

    def format_chat_tab_label(self, chat: dict[str, Any]) -> str:
        return self.localized_chat_name(chat)

    def localized_chat_name(self, chat: dict[str, Any]) -> str:
        slug = str(chat.get("slug") or "").strip().lower()
        name = str(chat.get("name") or "").strip()
        key_by_slug = {
            "global": "home.chat.room_global",
            "discussion": "home.chat.room_discussion",
            "discusion": "home.chat.room_discussion",
            "logi": "home.chat.room_logi",
            "faci": "home.chat.room_faci",
            "front": "home.chat.room_front",
        }
        normalized_name = name.lower()
        key = key_by_slug.get(slug) or key_by_slug.get(normalized_name)
        if key:
            return self.tr.t(key)
        return name or slug or "-"

    def render_chat_tabs(self) -> None:
        for child in self.chat_tabs_frame.winfo_children():
            child.destroy()
        self.chat_tab_buttons = {}
        for index, chat in enumerate(self.chats):
            slug = str(chat.get("slug") or "")
            button = tk.Button(
                self.chat_tabs_frame,
                text=self.format_chat_tab_label(chat),
                command=lambda chat_index=index: self.on_chat_selected(chat_index),
                bg="#0f1b2e",
                fg="#edf6ff",
                activebackground="#182d49",
                activeforeground="#edf6ff",
                relief="flat",
                bd=0,
                font=("Segoe UI", 9),
                padx=11,
                pady=4,
                cursor="hand2",
            )
            button.pack(side="left", padx=(0, 4))
            self.chat_tab_buttons[slug] = button
        for conversation in self.visible_whisper_conversations():
            conversation_id = self.conversation_id(conversation)
            key = self.whisper_key(conversation_id)
            holder = tk.Frame(self.chat_tabs_frame, bg="#07111f")
            holder.pack(side="left", padx=(4, 4))
            label = self.format_whisper_tab_label(conversation)
            button = tk.Button(
                holder,
                text=label,
                command=lambda cid=conversation_id: self.open_whisper_by_id(cid),
                bg="#13233b",
                fg="#dce8f7",
                activebackground="#203857",
                activeforeground="#edf6ff",
                relief="flat",
                bd=0,
                font=("Segoe UI", 9, "bold" if conversation_id in self.whisper_unread_ids else "normal"),
                padx=10,
                pady=4,
                cursor="hand2",
            )
            button.pack(side="left")
            close_button = tk.Button(
                holder,
                text="x",
                command=lambda cid=conversation_id: self.close_whisper_tab(cid),
                bg="#13233b",
                fg="#99abc4",
                activebackground="#431926",
                activeforeground="#edf6ff",
                relief="flat",
                bd=0,
                font=("Segoe UI", 8, "bold"),
                padx=6,
                pady=4,
                cursor="hand2",
            )
            close_button.pack(side="left")
            self.chat_tab_buttons[key] = button
        self.update_chat_tab_styles()
        self.after(0, self.refresh_chat_tabs_scroll)

    def visible_whisper_conversations(self) -> list[dict[str, Any]]:
        return [item for item in self.whisper_conversations if self.conversation_id(item) and self.conversation_id(item) not in self.closed_whisper_ids]

    def format_whisper_tab_label(self, conversation: dict[str, Any]) -> str:
        name = self.user_mention_name(self.other_whisper_user(conversation))
        marker = "• " if self.conversation_id(conversation) in self.whisper_unread_ids else ""
        return f"{marker}{self.tr.t('home.chat.whisper_tab', user=name)}"

    def update_chat_tab_styles(self) -> None:
        current = self.selected_chat_slug.get().strip()
        for slug, button in self.chat_tab_buttons.items():
            if slug == current:
                button.configure(bg="#5eead4", fg="#041014", activebackground="#8ab4ff", activeforeground="#041014", font=("Segoe UI", 9, "bold"))
            else:
                is_whisper = slug.startswith("whisper:")
                button.configure(
                    bg="#13233b" if is_whisper else "#0f1b2e",
                    fg="#5eead4" if is_whisper and slug.split(":", 1)[1] in self.whisper_unread_ids else "#cbd8ea",
                    activebackground="#203857" if is_whisper else "#182d49",
                    activeforeground="#edf6ff",
                    font=("Segoe UI", 9, "bold" if is_whisper and slug.split(":", 1)[1] in self.whisper_unread_ids else "normal"),
                )

    def on_chat_tabs_configure(self, _event=None) -> None:
        self.refresh_chat_tabs_scroll()

    def on_chat_tabs_canvas_configure(self, event) -> None:
        self.chat_tabs_canvas.itemconfigure(self.chat_tabs_window, height=event.height)
        self.refresh_chat_tabs_scroll()

    def on_chat_tabs_mousewheel(self, event) -> str:
        self.chat_tabs_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def refresh_chat_tabs_scroll(self) -> None:
        self.chat_tabs_canvas.configure(scrollregion=self.chat_tabs_canvas.bbox("all"))
        bbox = self.chat_tabs_canvas.bbox("all")
        if not bbox:
            self.chat_tabs_scrollbar.grid_remove()
            return
        content_width = bbox[2] - bbox[0]
        if content_width > self.chat_tabs_canvas.winfo_width():
            self.chat_tabs_scrollbar.grid()
        else:
            self.chat_tabs_scrollbar.grid_remove()
            self.chat_tabs_canvas.xview_moveto(0)

    def sync_selected_chat_label(self) -> None:
        slug = self.selected_chat_slug.get().strip()
        self.log(f"sync selected chat label slug={slug!r}")
        if slug.startswith("whisper:"):
            conversation = self.find_whisper_conversation(slug.split(":", 1)[1]) or {}
            label = self.format_whisper_tab_label(conversation)
            self.selected_chat_label.set(label)
            self.room_title_var.set(self.tr.t("home.chat.current_room", room=label))
            self.update_chat_tab_styles()
            return
        for index, chat in enumerate(self.chats):
            if str(chat.get("slug") or "") == slug:
                label = self.format_chat_tab_label(chat)
                self.selected_chat_label.set(label)
                self.room_title_var.set(self.tr.t("home.chat.current_room", room=label))
                self.update_chat_tab_styles()
                return
        if self.chats:
            label = self.format_chat_tab_label(self.chats[0])
            self.selected_chat_label.set(label)
            self.room_title_var.set(self.tr.t("home.chat.current_room", room=label))
            self.update_chat_tab_styles()
        else:
            self.room_title_var.set("")

    def load_messages(self, *, cursor: str | None = None, append_older: bool = False, use_cache: bool = True) -> None:
        if self.selected_is_whisper():
            self.load_whisper_messages(cursor=cursor, append_older=append_older, use_cache=use_cache)
            return
        slug = self.selected_chat_slug.get().strip()
        if not slug:
            self.log(f"load messages skipped slug={slug!r} inflight={self.messages_in_flight}")
            return
        if not cursor and not append_older and use_cache:
            cached = self.first_page_cache.get(slug)
            if cached and not self.messages:
                self.messages = list(cached.get("messages") or [])
                self.next_message_cursor = cached.get("nextCursor")
                for message in self.messages:
                    self.notified_message_ids.add(self.message_identity(message))
                self.render_messages(scroll_to_bottom=True)
        retry_seconds = int(max(0, self.messages_retry_after - time.monotonic()))
        if retry_seconds > 0:
            self.log(f"load messages skipped: retry after {retry_seconds}s")
            self.status_var.set(self.tr.t("home.chat.message_wait", seconds=retry_seconds))
            if self.active:
                self.schedule_refresh((retry_seconds + 1) * 1000)
            return
        if self.messages_in_flight:
            self.pending_message_slug = slug
            self.status_var.set(self.tr.t("home.chat.loading"))
            self.log(f"load messages queued slug={slug!r}")
            return
        self.messages_in_flight = True
        self.loading_older_messages = append_older
        self.pending_message_slug = None
        self.status_var.set(self.tr.t("home.chat.loading_older") if append_older else self.tr.t("home.chat.loading"))
        self.log(f"load messages started slug={slug} cursor={cursor or ''} append={append_older}")

        def worker() -> None:
            try:
                path = f"/chat/chats/{urllib.parse.quote(slug)}/messages?take=50"
                if cursor:
                    path = f"{path}&cursor={urllib.parse.quote(cursor)}"
                self.log(f"messages request GET {path}")
                result = _http_json("GET", path, token=self.chat_token)
                messages = list(result.get("messages") or [])
                self.log(f"messages response slug={slug} count={len(messages)}")
                self.after(0, self.apply_messages_result, messages, slug, result.get("nextCursor"), append_older)
            except Exception as exc:
                self.log(f"messages error slug={slug}: {exc}")
                self.after(0, self.handle_messages_error, str(exc), slug)
            finally:
                self.messages_in_flight = False
                self.loading_older_messages = False
                pending = self.pending_message_slug
                if pending and pending != slug:
                    self.after(0, self.load_messages)
                elif self.active and self.selected_chat_slug.get().strip() == slug:
                    self.after(0, self.schedule_refresh)

        threading.Thread(target=worker, daemon=True).start()

    def load_whisper_messages(self, *, cursor: str | None = None, append_older: bool = False, use_cache: bool = True) -> None:
        conversation_id = self.selected_whisper_id()
        if not conversation_id:
            return
        if not cursor and not append_older and use_cache:
            cached = self.whisper_messages_cache.get(conversation_id)
            if cached and not self.messages:
                self.messages = [self.normalize_whisper_message(item) for item in list(cached.get("messages") or [])]
                self.next_message_cursor = cached.get("nextCursor")
                self.render_messages(scroll_to_bottom=True)
        if self.messages_in_flight:
            self.pending_message_slug = self.whisper_key(conversation_id)
            return
        self.messages_in_flight = True
        self.loading_older_messages = append_older
        self.pending_message_slug = None
        self.status_var.set(self.tr.t("home.chat.loading_older") if append_older else self.tr.t("home.chat.loading"))

        def worker() -> None:
            try:
                path = f"/chat/whispers/{urllib.parse.quote(conversation_id)}/messages?take=50"
                if cursor:
                    path = f"{path}&cursor={urllib.parse.quote(cursor)}"
                result = _http_json("GET", path, token=self.chat_token, timeout=12)
                messages = [self.normalize_whisper_message(item) for item in list(result.get("messages") or [])]
                self.after(0, self.apply_whisper_messages_result, conversation_id, messages, result.get("nextCursor"), append_older)
            except Exception as exc:
                self.log(f"whisper messages error {conversation_id}: {exc}")
                self.after(0, self.set_error, self.tr.t("home.chat.message_error", message=str(exc)))
            finally:
                self.messages_in_flight = False
                self.loading_older_messages = False
                if self.active and self.selected_whisper_id() == conversation_id:
                    self.after(0, self.schedule_refresh)

        threading.Thread(target=worker, daemon=True).start()

    def apply_whisper_messages_result(self, conversation_id: str, messages: list[dict[str, Any]], next_cursor: Any = None, append_older: bool = False) -> None:
        if self.selected_whisper_id() != conversation_id:
            return
        merged_messages = self.merge_messages(self.messages, messages) if append_older else messages
        self.next_message_cursor = str(next_cursor or "") or None
        if not append_older:
            self.whisper_messages_cache[conversation_id] = {"messages": list(messages), "nextCursor": self.next_message_cursor}
            self.save_whisper_cache()
        signature = self.messages_signature(merged_messages)
        if signature == self.rendered_message_signature:
            self.messages = merged_messages
            self.status_var.set(self.tr.t("home.chat.ready"))
            return
        should_scroll = False if append_older else (not self.rendered_message_signature or self.is_messages_near_bottom())
        self.messages = merged_messages
        self.render_messages(scroll_to_bottom=should_scroll)
        self.status_var.set(self.tr.t("home.chat.ready"))

    def apply_messages_result(self, messages: list[dict[str, Any]], slug: str, next_cursor: Any = None, append_older: bool = False) -> None:
        if self.selected_chat_slug.get() != slug:
            self.log(f"message result ignored slug={slug} current={self.selected_chat_slug.get()}")
            return
        self.messages_retry_after = 0.0
        merged_messages = self.merge_messages(self.messages, messages) if append_older else messages
        self.next_message_cursor = str(next_cursor or "") or None
        if not append_older:
            self.first_page_cache[slug] = {"messages": list(messages), "nextCursor": self.next_message_cursor}
        self.log(f"apply messages slug={slug} count={len(merged_messages)} append={append_older}")
        if self.rendered_message_signature and not append_older:
            self.detect_local_mentions(merged_messages)
        else:
            for message in merged_messages:
                self.notified_message_ids.add(self.message_identity(message))
        signature = self.messages_signature(merged_messages)
        if signature == self.rendered_message_signature:
            self.messages = merged_messages
            self.status_var.set(self.tr.t("home.chat.ready"))
            if self.active:
                self.schedule_refresh()
            return
        should_scroll = False if append_older else (not self.rendered_message_signature or self.is_messages_near_bottom())
        self.messages = merged_messages
        self.render_messages(scroll_to_bottom=should_scroll)
        self.status_var.set(self.tr.t("home.chat.ready"))
        if self.active:
            self.schedule_refresh()

    def merge_messages(self, current: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for message in [*incoming, *current]:
            key = self.message_identity(message)
            if key in seen:
                continue
            seen.add(key)
            merged.append(message)
        return merged

    def message_identity(self, message: dict[str, Any]) -> str:
        user = message.get("user") or {}
        fallback = f"{message.get('createdAt') or message.get('created_at') or ''}:{user.get('steamId') or user.get('id') or ''}:{message.get('content') or ''}"
        return str(message.get("id") or message.get("_id") or fallback)

    def load_older_messages(self) -> None:
        if not self.next_message_cursor or self.loading_older_messages:
            return
        self.load_messages(cursor=self.next_message_cursor, append_older=True, use_cache=False)

    def messages_signature(self, messages: list[dict[str, Any]]) -> tuple[tuple[str, str, str, str], ...]:
        signature: list[tuple[str, str, str, str]] = []
        for message in messages:
            user = message.get("user") or {}
            fallback_id = f"{message.get('createdAt') or message.get('created_at') or ''}:{user.get('steamId') or user.get('id') or ''}:{message.get('content') or ''}"
            signature.append(
                (
                    str(message.get("id") or message.get("_id") or fallback_id),
                    str(message.get("content") or ""),
                    str(message.get("createdAt") or message.get("created_at") or ""),
                    str(message.get("editedAt") or message.get("edited_at") or ""),
                )
            )
        return tuple(signature)

    def is_messages_near_bottom(self) -> bool:
        try:
            return self.messages_canvas.yview()[1] >= 0.96
        except tk.TclError:
            return True

    def handle_messages_error(self, message: str, slug: str) -> None:
        if self.selected_chat_slug.get() != slug:
            return
        if "429" in message or "Too Many Requests" in message:
            self.messages_retry_after = time.monotonic() + 45
            self.status_var.set(self.tr.t("home.chat.message_limited"))
            if self.active:
                self.schedule_refresh(46000)
            return
        self.set_error(self.tr.t("home.chat.message_error", message=message))

    def send_message(self) -> None:
        content = self.input_var.get().strip()
        if not content:
            self.log("send ignored: empty content")
            return
        if not self.chat_token:
            self.log("send requested without token, re-authenticating")
            self.status_var.set(self.tr.t("home.chat.auth_needed"))
            self.authenticate()
            return
        if self.selected_is_whisper():
            self.send_whisper_message(content)
            return
        slug = self.selected_chat_slug.get().strip()
        if not slug:
            self.log("send aborted: no selected chat")
            return
        retry_seconds = int(max(0, self.send_retry_after - time.monotonic()))
        if retry_seconds > 0:
            self.log(f"send skipped: retry after {retry_seconds}s")
            self.status_var.set(self.tr.t("home.chat.send_wait", seconds=retry_seconds))
            return
        self.send_button.configure(state="disabled")
        self.status_var.set(self.tr.t("home.chat.sending"))
        self.log(f"send started slug={slug} content_len={len(content)}")

        def worker() -> None:
            try:
                path = f"/chat/chats/{urllib.parse.quote(slug)}/messages"
                self.log(f"send request POST {path}")
                result = _http_json("POST", path, token=self.chat_token, payload={"content": content})
                message = dict(result.get("message") or {})
                self.log(f"send response keys={sorted(message.keys()) if message else []}")
                self.after(0, self.after_send_message, message, content)
            except Exception as exc:
                self.log(f"send error: {exc}")
                self.after(0, self.handle_send_error, str(exc))
            finally:
                self.after(0, lambda: self.send_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def send_whisper_message(self, content: str) -> None:
        conversation_id = self.selected_whisper_id()
        if not conversation_id:
            return
        retry_seconds = int(max(0, self.send_retry_after - time.monotonic()))
        if retry_seconds > 0:
            self.status_var.set(self.tr.t("home.chat.send_wait", seconds=retry_seconds))
            return
        self.send_button.configure(state="disabled")
        self.status_var.set(self.tr.t("home.chat.sending"))

        def worker() -> None:
            try:
                path = f"/chat/whispers/{urllib.parse.quote(conversation_id)}/messages"
                result = _http_json("POST", path, token=self.chat_token, payload={"content": content}, timeout=12)
                message = self.normalize_whisper_message(dict(result.get("message") or result))
                self.after(0, self.after_send_whisper_message, conversation_id, message)
            except Exception as exc:
                self.after(0, self.handle_send_error, str(exc))
            finally:
                self.after(0, lambda: self.send_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def after_send_whisper_message(self, conversation_id: str, message: dict[str, Any]) -> None:
        self.send_retry_after = 0.0
        self.input_var.set("")
        if message:
            self.messages.append(message)
            cached = self.whisper_messages_cache.setdefault(conversation_id, {"messages": [], "nextCursor": self.next_message_cursor})
            cached_messages = [self.normalize_whisper_message(item) for item in list(cached.get("messages") or [])]
            cached_messages.append(message)
            cached["messages"] = cached_messages[-50:]
            cached["nextCursor"] = self.next_message_cursor
            self.save_whisper_cache()
            self.render_messages(scroll_to_bottom=True)
        else:
            self.load_messages(use_cache=False)
        self.status_var.set(self.tr.t("home.chat.sent"))

    def after_send_message(self, message: dict[str, Any], fallback_content: str) -> None:
        self.send_retry_after = 0.0
        self.input_var.set("")
        if message:
            self.log("send applied from response")
            self.messages.append(message)
            slug = self.selected_chat_slug.get().strip()
            if slug:
                cached = self.first_page_cache.setdefault(slug, {"messages": [], "nextCursor": self.next_message_cursor})
                cached_messages = list(cached.get("messages") or [])
                cached_messages.append(message)
                cached["messages"] = cached_messages[-50:]
                cached["nextCursor"] = self.next_message_cursor
            self.render_messages(scroll_to_bottom=True)
        else:
            self.log("send response empty, reloading messages")
            self.load_messages()
        self.status_var.set(self.tr.t("home.chat.sent"))
        if self.active:
            self.schedule_refresh()

    def handle_send_error(self, message: str) -> None:
        if "429" in message or "Too Many Requests" in message:
            self.send_retry_after = time.monotonic() + 45
            self.messages_retry_after = max(self.messages_retry_after, time.monotonic() + 30)
            self.status_var.set(self.tr.t("home.chat.send_limited"))
            return
        self.set_error(self.tr.t("home.chat.send_error", message=message))

    def set_error(self, text: str) -> None:
        self.log(f"ui error: {text}")
        self.status_var.set(text)

    def render_messages(self, *, scroll_to_bottom: bool = True) -> None:
        self.stop_preview_animations()
        self.hide_mention_hover_card()
        for child in self.messages_inner.winfo_children():
            child.destroy()
        self.message_image_refs = []
        self.preview_image_refs = []
        self.avatar_labels_by_url = {}
        self.preview_labels_by_url = {}
        if not self.messages:
            tk.Label(
                self.messages_inner,
                text=self.tr.t("home.chat.empty"),
                bg="#0b1424",
                fg="#99abc4",
                font=("Segoe UI", 10, "bold"),
                pady=12,
            ).pack(fill="x", padx=8, pady=8)
            self.rendered_message_signature = ()
            return

        if self.next_message_cursor:
            tk.Button(
                self.messages_inner,
                text=self.tr.t("home.chat.load_older"),
                command=self.load_older_messages,
                bg="#10233a",
                fg="#dce8f7",
                activebackground="#203857",
                activeforeground="#edf6ff",
                relief="flat",
                bd=0,
                font=("Segoe UI", 8, "bold"),
                padx=10,
                pady=5,
                cursor="hand2",
            ).pack(anchor="center", pady=(8, 4))

        for message in self.messages:
            self.render_message_row(message)
        self.bind_messages_mousewheel(self.messages_inner)
        self.rendered_message_signature = self.messages_signature(self.messages)
        if scroll_to_bottom:
            self.keep_messages_pinned_to_bottom = True
            self.after(0, self.scroll_messages_to_bottom)
            self.after(80, self.scroll_messages_to_bottom)
            self.after(220, self.scroll_messages_to_bottom)
        else:
            self.keep_messages_pinned_to_bottom = self.is_messages_near_bottom()

    def stop_preview_animations(self) -> None:
        for job in list(self.gif_animation_jobs.values()):
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self.gif_animation_jobs = {}

    def scroll_messages_to_bottom(self) -> None:
        try:
            self.messages_canvas.configure(scrollregion=self.messages_canvas.bbox("all"))
            self.messages_canvas.yview_moveto(1.0)
            self.keep_messages_pinned_to_bottom = True
        except tk.TclError:
            pass

    def render_message_row(self, message: dict[str, Any]) -> None:
        is_mine = self.is_own_message(message)
        row = tk.Frame(self.messages_inner, bg="#0b1424")
        row.pack(fill="x", padx=10, pady=(7, 0), anchor="e" if is_mine else "w")
        avatar_url = self.message_avatar_url(message)
        avatar = self.get_avatar_image(avatar_url, size=28)
        side = "right" if is_mine else "left"
        opposite_side = "left" if is_mine else "right"
        accent_color = "#5eead4" if is_mine else "#24486d"
        bubble_bg = "#10243a" if is_mine else "#0e192b"
        accent = tk.Frame(row, bg=accent_color, width=2)
        accent.pack(side=side, fill="y", padx=(8, 0) if is_mine else (0, 8))
        avatar_label = tk.Label(row, image=avatar, bg="#0b1424")
        avatar_label.image = avatar
        avatar_label.pack(side=side, anchor="n", padx=(8, 0) if is_mine else (0, 8), pady=7)
        self.message_image_refs.append(avatar)
        if avatar_url:
            self.avatar_labels_by_url.setdefault(avatar_url, []).append(avatar_label)

        spacer = tk.Frame(row, bg="#0b1424")
        spacer.pack(side=opposite_side, fill="x", expand=True)
        body = tk.Frame(row, bg=bubble_bg, highlightthickness=1, highlightbackground="#24486d" if is_mine else "#182d49")
        body.pack(side=side, fill="x", expand=False)
        body.configure(width=max(320, min(760, self.messages_canvas.winfo_width() - 150)))
        header = tk.Frame(body, bg=bubble_bg)
        header.pack(fill="x", padx=10, pady=(6, 1))
        user = message.get("user") or {}
        name = str(user.get("personaname") or user.get("nickname") or self.tr.t("home.chat.no_user"))
        created = str(message.get("createdAt") or message.get("created_at") or "")
        edited = message.get("editedAt") or message.get("edited_at")
        tk.Label(header, text=name, bg=bubble_bg, fg="#8ab4ff", font=("Segoe UI", 9, "bold")).pack(side="right" if is_mine else "left")
        if not is_mine and user:
            tk.Button(
                header,
                text=self.tr.t("home.chat.whisper_button"),
                command=lambda item=user: self.open_whisper_with_user(item),
                bg="#17324f",
                fg="#5eead4",
                activebackground="#203857",
                activeforeground="#edf6ff",
                relief="flat",
                bd=0,
                font=("Segoe UI", 7, "bold"),
                padx=6,
                pady=1,
                cursor="hand2",
            ).pack(side="right" if not is_mine else "left", padx=6)
        meta_text = self.format_message_time(created) if created else ""
        if edited:
            meta_text = f"{meta_text}  {self.tr.t('home.chat.edited')}"
        tk.Label(header, text=meta_text, bg=bubble_bg, fg="#7f90aa", font=("Segoe UI", 8)).pack(side="left" if is_mine else "right")
        content = str(message.get("content") or "")
        visible_content = self.visible_message_text(content)
        if visible_content:
            self.render_message_text(body, visible_content, message, bubble_bg, align_right=is_mine)
        self.render_message_mentions(body, message, visible_content, align_right=is_mine)
        self.render_message_previews(body, content, align_right=is_mine)

    def render_message_text(self, parent: tk.Widget, content: str, message: dict[str, Any], bubble_bg: str, *, align_right: bool = False) -> None:
        line_count = max(1, content.count("\n") + (len(content) // 82) + 1)
        text = tk.Text(
            parent,
            bg=bubble_bg,
            fg="#edf6ff",
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
            wrap="word",
            height=min(8, line_count),
            cursor="arrow",
            padx=0,
            pady=0,
            takefocus=0,
        )
        text.pack(fill="x", padx=10, pady=(0, 8))
        text.tag_configure("body", justify="right" if align_right else "left")
        text.insert("1.0", content, ("body",))
        mention_users = self.message_mention_users(message)
        for index, match in enumerate(MENTION_RE.finditer(content)):
            name = match.group(1)
            user = mention_users.get(name.casefold()) or self.find_online_user(name) or {"mention": name}
            tag = f"mention_{index}"
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            text.tag_add(tag, start, end)
            text.tag_configure(tag, foreground="#5eead4", background="#17324f", font=("Segoe UI", 10, "bold"))
            text.tag_bind(tag, "<Enter>", lambda event, item=user: self.show_mention_hover_card(event, item))
            text.tag_bind(tag, "<Leave>", lambda _event: self.hide_mention_hover_card())
        text.configure(state="disabled")

    def message_mention_users(self, message: dict[str, Any]) -> dict[str, dict[str, Any]]:
        users: dict[str, dict[str, Any]] = {}
        for mention in list(message.get("mentions") or []):
            user = mention.get("mentionedUser") or mention.get("user") or mention
            if not isinstance(user, dict):
                continue
            name = self.user_mention_name(user)
            if name:
                users[name.casefold()] = user
        return users

    def find_online_user(self, name: str) -> dict[str, Any] | None:
        wanted = name.casefold().lstrip("@")
        for user in [*self.online_users, *self.all_chat_users]:
            if self.user_mention_name(user).casefold() == wanted:
                return user
        return None

    def show_mention_hover_card(self, event, user: dict[str, Any]) -> None:
        self.hide_mention_hover_card()
        card = tk.Toplevel(self)
        self.mention_hover_card = card
        card.overrideredirect(True)
        card.attributes("-topmost", True)
        frame = tk.Frame(card, bg="#07111f", highlightthickness=1, highlightbackground="#5eead4")
        frame.pack(fill="both", expand=True)
        avatar_url = str(user.get("avatarmedium") or user.get("avatarfull") or user.get("avatar") or "")
        avatar = self.get_avatar_image(avatar_url, size=36)
        avatar_label = tk.Label(frame, image=avatar, bg="#07111f")
        avatar_label.image = avatar
        avatar_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(10, 8), pady=10)
        self.message_image_refs.append(avatar)
        if avatar_url:
            self.avatar_labels_by_url.setdefault(avatar_url, []).append(avatar_label)
        tk.Label(frame, text=f"@{self.user_mention_name(user)}", bg="#07111f", fg="#edf6ff", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w", padx=(0, 12), pady=(10, 1)
        )
        steam_id = str(user.get("steamId") or user.get("steam_id") or "")
        detail = steam_id if steam_id else self.tr.t("home.chat.online")
        tk.Label(frame, text=detail, bg="#07111f", fg="#99abc4", font=("Segoe UI", 8)).grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(0, 10))
        tk.Button(
            frame,
            text=self.tr.t("home.chat.whisper_button"),
            command=lambda item=user: (self.hide_mention_hover_card(), self.open_whisper_with_user(item)),
            bg="#17324f",
            fg="#5eead4",
            activebackground="#203857",
            activeforeground="#edf6ff",
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            cursor="hand2",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        card.update_idletasks()
        card.geometry(f"+{event.x_root + 14}+{event.y_root + 14}")

    def hide_mention_hover_card(self) -> None:
        try:
            if self.mention_hover_card and self.mention_hover_card.winfo_exists():
                self.mention_hover_card.destroy()
        except tk.TclError:
            pass
        self.mention_hover_card = None

    def render_message_mentions(self, parent: tk.Widget, message: dict[str, Any], visible_content: str, *, align_right: bool = False) -> None:
        mentions = list(message.get("mentions") or [])
        if not mentions:
            return
        if MENTION_RE.search(visible_content or ""):
            return
        parent_bg = str(parent.cget("bg"))
        row = tk.Frame(parent, bg=parent_bg)
        row.pack(fill="x", padx=10, pady=(0, 7), anchor="e" if align_right else "w")
        for mention in mentions[:4]:
            user = mention.get("mentionedUser") or mention.get("user") or mention
            name = self.user_mention_name(user)
            tk.Label(
                row,
                text=f"@{name}",
                bg="#17324f",
                fg="#5eead4",
                font=("Segoe UI", 8, "bold"),
                padx=7,
                pady=2,
            ).pack(side="right" if align_right else "left", padx=(4, 0) if align_right else (0, 4))

    def detect_local_mentions(self, messages: list[dict[str, Any]]) -> None:
        if not self.chat_user:
            return
        for message in messages:
            identity = self.message_identity(message)
            if identity in self.notified_message_ids or self.is_own_message(message):
                continue
            self.notified_message_ids.add(identity)
            if not self.message_mentions_current_user(message):
                continue
            user = message.get("user") or {}
            title = self.tr.t("home.chat.mention_title")
            body = self.tr.t(
                "home.chat.mention_body",
                user=self.user_mention_name(user),
                room=self.selected_chat_label.get() or "-",
            )
            self.show_mention_overlay(title, body)
            self.play_mention_sound()

    def message_mentions_current_user(self, message: dict[str, Any]) -> bool:
        local_steam_id = str(self.chat_user.get("steamId") or getattr(self.app.profile, "steam_id", "") or "")
        local_name = self.user_mention_name(self.chat_user).casefold()
        for mention in list(message.get("mentions") or []):
            user = mention.get("mentionedUser") or mention.get("user") or mention
            steam_id = str(user.get("steamId") or user.get("steam_id") or "")
            if local_steam_id and steam_id == local_steam_id:
                return True
            if local_name and self.user_mention_name(user).casefold() == local_name:
                return True
        content = str(message.get("content") or "").casefold()
        return bool(local_name and f"@{local_name}" in content)

    def show_mention_overlay(self, title: str, body: str) -> None:
        if not self.app_setting("chat_mention_overlay_enabled", True):
            return
        try:
            if self.mention_overlay_job:
                self.after_cancel(self.mention_overlay_job)
            if self.mention_overlay and self.mention_overlay.winfo_exists():
                self.mention_overlay.destroy()
        except tk.TclError:
            pass
        window = tk.Toplevel(self)
        self.mention_overlay = window
        window.title(title)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        frame = tk.Frame(window, bg="#07111f", highlightthickness=1, highlightbackground="#5eead4")
        frame.pack(fill="both", expand=True)
        title_label = tk.Label(frame, text=title, bg="#07111f", fg="#5eead4", font=("Segoe UI", 11, "bold"), cursor="hand2")
        title_label.pack(anchor="w", padx=14, pady=(12, 2))
        body_label = tk.Label(frame, text=body, bg="#07111f", fg="#edf6ff", font=("Segoe UI", 9), wraplength=300, justify="left", cursor="hand2")
        body_label.pack(anchor="w", padx=14, pady=(0, 12))
        for widget in (window, frame, title_label, body_label):
            widget.bind("<Button-1>", lambda _event: self.open_chat_from_overlay())
        window.update_idletasks()
        width = 340
        height = max(86, window.winfo_reqheight())
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        window.geometry(f"{width}x{height}+{screen_w - width - 24}+{screen_h - height - 70}")
        self.mention_overlay_job = self.after(6500, self.hide_mention_overlay)

    def hide_mention_overlay(self) -> None:
        self.mention_overlay_job = None
        try:
            if self.mention_overlay and self.mention_overlay.winfo_exists():
                self.mention_overlay.destroy()
        except tk.TclError:
            pass
        self.mention_overlay = None

    def open_chat_from_overlay(self) -> None:
        self.hide_mention_overlay()
        if hasattr(self.app, "open_chat_from_overlay"):
            self.app.open_chat_from_overlay()

    def app_setting(self, key: str, default: bool = True) -> bool:
        try:
            return bool(load_settings().get("app", {}).get(key, default))
        except Exception:
            return default

    def play_mention_sound(self) -> None:
        if not self.app_setting("chat_mention_sound_enabled", True):
            return
        try:
            if os.name == "nt":
                import winsound

                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                self.bell()
        except Exception as exc:
            self.log(f"mention sound failed: {exc}")

    def is_own_message(self, message: dict[str, Any]) -> bool:
        user = message.get("user") or {}
        local_steam_id = str(self.chat_user.get("steamId") or getattr(self.app.profile, "steam_id", "") or "")
        if local_steam_id and str(user.get("steamId") or "") == local_steam_id:
            return True
        local_name = str(self.user_name_var.get() or "").strip().casefold()
        remote_name = str(user.get("personaname") or user.get("nickname") or "").strip().casefold()
        return bool(local_name and remote_name and local_name == remote_name)

    def format_message_time(self, value: str) -> str:
        try:
            normalized = value.strip()
            if normalized.endswith("Z"):
                normalized = f"{normalized[:-1]}+00:00"
            moment = datetime.fromisoformat(normalized)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            local_moment = moment.astimezone()
            offset = local_moment.strftime("%z")
            if offset:
                offset = f" GMT{offset[:3]}:{offset[3:]}"
            return local_moment.strftime("%Y-%m-%d %H:%M:%S") + offset
        except Exception:
            return value[:19].replace("T", " ")

    def message_wraplength(self) -> int:
        try:
            width = self.messages_canvas.winfo_width()
        except tk.TclError:
            width = 650
        return max(260, width - 150)

    def visible_message_text(self, content: str) -> str:
        text = content.strip()
        for url in self.extract_media_urls(content):
            text = text.replace(url, " ")
        return " ".join(text.split())

    def render_message_previews(self, parent: tk.Widget, content: str, *, align_right: bool = False) -> None:
        urls = self.extract_media_urls(content)
        for url in urls[:2]:
            is_gif = self.is_gif_url(url)
            parent_bg = str(parent.cget("bg"))
            preview = tk.Frame(parent, bg=parent_bg)
            preview.pack(fill="x", padx=10, pady=(2, 10), anchor="e" if align_right else "w")
            media_box = tk.Frame(preview, bg="#101e33", highlightthickness=1, highlightbackground="#203857")
            media_box.pack(side="right" if align_right else "left", anchor="e" if align_right else "w")
            if is_gif:
                badge_row = tk.Frame(media_box, bg="#101e33")
                badge_row.pack(fill="x", padx=6, pady=(5, 0))
                tk.Label(
                    badge_row,
                    text=self.tr.t("home.chat.gif_playing"),
                    bg="#172844",
                    fg="#5eead4",
                    font=("Segoe UI", 7, "bold"),
                    padx=7,
                    pady=2,
                ).pack(side="right")
            photo = self.preview_cache.get(url)
            if photo:
                label = tk.Label(media_box, image=photo, bg="#101e33", bd=0)
                label.image = photo
                label.pack(anchor="e" if align_right else "w", padx=6, pady=6)
                self.preview_image_refs.append(photo)
                self.preview_labels_by_url.setdefault(url, []).append(label)
                if url in self.gif_preview_frames:
                    self.start_preview_animation(url)
            else:
                label = tk.Label(
                    media_box,
                    text=self.tr.t("home.chat.media_loading"),
                    bg="#13233b",
                    fg="#99abc4",
                    font=("Segoe UI", 8, "bold"),
                    padx=10,
                    pady=7,
                )
                label.pack(anchor="e" if align_right else "w", padx=6, pady=6)
                self.preview_labels_by_url.setdefault(url, []).append(label)
                if url not in self.pending_preview_requests:
                    self.pending_preview_requests.add(url)
                    threading.Thread(target=self.load_preview_async, args=(url,), daemon=True).start()

    def extract_media_urls(self, content: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for match in IMAGE_URL_RE.finditer(content):
            url = match.group(0).rstrip(").,;]")
            if url not in seen:
                seen.add(url)
                urls.append(url)
        return urls

    def is_gif_url(self, url: str) -> bool:
        return urllib.parse.urlparse(url).path.lower().endswith(".gif")

    def load_preview_async(self, url: str) -> None:
        if not Image or not ImageTk:
            self.after(0, self.preview_failed, url)
            return
        try:
            self.log(f"media preview request {url}")
            request = urllib.request.Request(url, headers={"User-Agent": "GG Coalition/1.0", "Accept": "image/*,*/*;q=0.8"})
            with urllib.request.urlopen(request, timeout=12) as response:
                data = response.read(8 * 1024 * 1024)
            image = Image.open(io.BytesIO(data))
            if getattr(image, "is_animated", False) and ImageSequence is not None:
                frames, delays = self.prepare_gif_frames(image)
                self.after(0, self.store_animated_preview, url, frames, delays)
                return
            image = image.convert("RGBA")
            image.thumbnail((340, 200))
            self.after(0, self.store_preview_image, url, image)
        except Exception as exc:
            self.log(f"media preview failed {url}: {exc}")
            self.after(0, self.preview_failed, url)

    def prepare_gif_frames(self, image) -> tuple[list[Any], list[int]]:
        frames: list[Any] = []
        delays: list[int] = []
        for index, frame in enumerate(ImageSequence.Iterator(image)):
            if index >= 48:
                break
            item = frame.convert("RGBA")
            item.thumbnail((340, 200))
            frames.append(item.copy())
            delay = int(frame.info.get("duration") or image.info.get("duration") or 80)
            delays.append(min(220, max(35, delay)))
        if not frames:
            first = image.convert("RGBA")
            first.thumbnail((340, 200))
            frames.append(first)
            delays.append(100)
        return frames, delays

    def store_preview_image(self, url: str, image) -> None:
        photo = ImageTk.PhotoImage(image)
        self.store_preview(url, photo)

    def store_animated_preview(self, url: str, frame_images: list[Any], delays: list[int]) -> None:
        frames = [ImageTk.PhotoImage(image) for image in frame_images]
        if not frames:
            self.preview_failed(url)
            return
        self.gif_preview_frames[url] = frames
        self.gif_preview_delays[url] = delays
        self.store_preview(url, frames[0])
        self.start_preview_animation(url)

    def store_preview(self, url: str, photo: tk.PhotoImage) -> None:
        was_pinned = self.keep_messages_pinned_to_bottom or self.is_messages_near_bottom()
        self.preview_cache[url] = photo
        self.pending_preview_requests.discard(url)
        for label in self.preview_labels_by_url.get(url, []):
            try:
                label.configure(image=photo, text="", padx=0, pady=0, bg="#101e33")
                label.image = photo
            except tk.TclError:
                pass
        if was_pinned:
            self.after(0, self.scroll_messages_to_bottom)
            self.after(120, self.scroll_messages_to_bottom)

    def start_preview_animation(self, url: str) -> None:
        if url in self.gif_animation_jobs:
            return
        if url not in self.gif_preview_frames:
            return
        self.animate_preview(url, 0)

    def animate_preview(self, url: str, index: int) -> None:
        frames = self.gif_preview_frames.get(url)
        labels = self.preview_labels_by_url.get(url, [])
        if not frames or not labels:
            self.gif_animation_jobs.pop(url, None)
            return
        photo = frames[index % len(frames)]
        for label in labels:
            try:
                label.configure(image=photo, text="")
                label.image = photo
            except tk.TclError:
                pass
        delays = self.gif_preview_delays.get(url) or [80]
        delay = delays[index % len(delays)]
        self.gif_animation_jobs[url] = self.after(delay, self.animate_preview, url, index + 1)

    def preview_failed(self, url: str) -> None:
        self.pending_preview_requests.discard(url)
        for label in self.preview_labels_by_url.get(url, []):
            try:
                label.configure(text=self.tr.t("home.chat.media_failed"), fg="#fca5a5")
            except tk.TclError:
                pass

    def message_avatar_url(self, message: dict[str, Any]) -> str:
        user = message.get("user") or {}
        return str(user.get("avatarmedium") or user.get("avatarfull") or user.get("avatar") or "")

    def draw_avatar_placeholder(self, canvas: tk.Canvas, size: int) -> None:
        canvas.delete("all")
        canvas.create_rectangle(0, 0, size, size, fill="#1d3353", outline="#5eead4")
        canvas.create_oval(size * 0.30, size * 0.16, size * 0.70, size * 0.52, fill="#8ab4ff", outline="")
        canvas.create_rectangle(size * 0.22, size * 0.56, size * 0.78, size * 0.82, fill="#8ab4ff", outline="")

    def get_avatar_image(self, url: str, size: int = 32) -> tk.PhotoImage:
        if not url:
            return self.placeholder_avatar(size)
        cached = self.avatar_cache.get(url)
        if cached:
            return cached
        if url not in self.pending_avatar_requests:
            self.pending_avatar_requests.add(url)
            threading.Thread(target=self.load_avatar_async, args=(url,), daemon=True).start()
        return self.placeholder_avatar(size)

    def placeholder_avatar(self, size: int) -> tk.PhotoImage:
        key = f"placeholder:{size}"
        cached = self.avatar_cache.get(key)
        if cached:
            return cached
        try:
            if Image and ImageTk:
                image = Image.new("RGBA", (size, size), COLORS["card_2"])
                draw = ImageDraw.Draw(image)
                draw.ellipse((size * 0.28, size * 0.15, size * 0.72, size * 0.55), fill=COLORS["accent_2"])
                draw.rounded_rectangle((size * 0.20, size * 0.56, size * 0.80, size * 0.84), radius=int(size * 0.10), fill=COLORS["accent_2"])
                photo = ImageTk.PhotoImage(image)
            else:
                photo = tk.PhotoImage(width=size, height=size)
                photo.put(COLORS["card_2"], to=(0, 0, size, size))
        except Exception:
            photo = tk.PhotoImage(width=size, height=size)
            photo.put(COLORS["card_2"], to=(0, 0, size, size))
        self.avatar_cache[key] = photo
        return photo

    def load_avatar_async(self, url: str) -> None:
        if not url:
            self.log("avatar skipped: empty url")
            return
        try:
            self.log(f"avatar request {url}")
            with urllib.request.urlopen(url, timeout=12) as response:
                data = response.read()
            if Image and ImageTk:
                image = Image.open(io.BytesIO(data)).convert("RGBA")
                image = image.resize((36, 36))
                photo = ImageTk.PhotoImage(image)
            else:
                photo = tk.PhotoImage(data=data)
            self.after(0, self.store_avatar, url, photo)
        except Exception as exc:
            self.log(f"avatar load failed {url}: {exc}")
            self.pending_avatar_requests.discard(url)

    def store_avatar(self, url: str, photo: tk.PhotoImage) -> None:
        self.log(f"avatar stored {url}")
        self.avatar_cache[url] = photo
        self.pending_avatar_requests.discard(url)
        if self.chat_user.get("avatarfull") == url or self.chat_user.get("avatarmedium") == url or self.chat_user.get("avatar") == url:
            self.avatar_canvas.delete("all")
            self.avatar_canvas.create_image(18, 18, image=photo)
            self.avatar_canvas.image = photo
        for label in self.avatar_labels_by_url.get(url, []):
            try:
                label.configure(image=photo)
                label.image = photo
            except tk.TclError:
                pass

    def stop(self) -> None:
        self.log("panel stopped")
        self.cancel_refresh()
        self.cancel_presence()
        self.cancel_mention_notifications()
        self.hide_mention_hover_card()
        self.hide_mention_overlay()
