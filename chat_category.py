from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

try:
    from PIL import Image, ImageDraw, ImageTk
except Exception:  # pragma: no cover - avatar rendering degrades to placeholders.
    Image = None
    ImageDraw = None
    ImageTk = None


CHAT_API_BASE = "https://archpixel.squareweb.app"
CHAT_LOG_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GG Coalition" / "chat_debug.log"
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
        self.user_name_var = tk.StringVar(value=self.tr.t("home.chat.no_user"))
        self.user_detail_var = tk.StringVar(value="")
        self.refresh_job: str | None = None
        self.refresh_in_flight = False
        self.auth_in_flight = False
        self.messages_in_flight = False
        self.pending_message_slug: str | None = None
        self.avatar_cache: dict[str, tk.PhotoImage] = {}
        self.pending_avatar_requests: set[str] = set()
        self.message_image_refs: list[tk.PhotoImage] = []
        self.chat_tab_buttons: dict[str, tk.Button] = {}
        self.active = False

        self.columnconfigure(0, weight=1)
        self.build()
        self.log("panel initialized")
        self.log("waiting for steam profile refresh before authenticate")

    def build(self) -> None:
        panel = tk.Frame(self, bg="#08111f", highlightthickness=1, highlightbackground="#203857")
        panel.grid(row=0, column=0, sticky="nsew", padx=24, pady=(0, 24))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)
        header = tk.Frame(panel, bg="#08111f")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header.columnconfigure(1, weight=1)

        tk.Label(
            header,
            text=self.tr.t("home.chat.title"),
            bg="#08111f",
            fg=COLORS["text"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text=self.tr.t("home.chat.subtitle"),
            bg="#08111f",
            fg="#8fa3bd",
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        status_row = tk.Frame(header, bg="#08111f")
        status_row.grid(row=0, column=1, rowspan=2, sticky="e")
        tk.Label(status_row, textvariable=self.status_var, bg="#10233a", fg="#dce8f7", font=("Segoe UI", 9, "bold"), padx=10, pady=4).pack(side="right")

        account_row = tk.Frame(panel, bg="#0d1729", highlightthickness=1, highlightbackground="#182d49")
        account_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        account_row.columnconfigure(1, weight=1)
        self.avatar_canvas = tk.Canvas(account_row, width=36, height=36, bg="#14243b", highlightthickness=0)
        self.avatar_canvas.grid(row=0, column=0, rowspan=2, sticky="w", padx=(10, 8), pady=8)
        self.draw_avatar_placeholder(self.avatar_canvas, 36)
        self.connected_label = tk.Label(account_row, text=self.tr.t("home.chat.connected_as"), bg="#0d1729", fg="#7f90aa", font=("Segoe UI", 8, "bold"))
        self.connected_label.grid(row=0, column=1, sticky="w", pady=(8, 0))
        tk.Label(account_row, textvariable=self.user_name_var, bg="#0d1729", fg="#edf6ff", font=("Segoe UI", 10, "bold")).grid(row=1, column=1, sticky="w", pady=(0, 8))
        tk.Label(account_row, textvariable=self.user_detail_var, bg="#0d1729", fg="#7f90aa", font=("Segoe UI", 8)).grid(row=0, column=2, rowspan=2, sticky="e", padx=10)

        top_controls = tk.Frame(panel, bg="#08111f")
        top_controls.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        top_controls.columnconfigure(0, weight=1)

        tabs_header = tk.Frame(top_controls, bg="#08111f")
        tabs_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        tabs_header.columnconfigure(1, weight=1)
        self.rooms_label = tk.Label(tabs_header, text=self.tr.t("home.chat.rooms"), bg="#08111f", fg="#8ab4ff", font=("Segoe UI", 9, "bold"))
        self.rooms_label.grid(row=0, column=0, sticky="w")
        self.room_title_label = tk.Label(tabs_header, textvariable=self.room_title_var, bg="#08111f", fg="#7f90aa", font=("Segoe UI", 9))
        self.room_title_label.grid(row=0, column=1, sticky="e")

        tabs_shell = tk.Frame(top_controls, bg="#08111f")
        tabs_shell.grid(row=1, column=0, sticky="ew")
        tabs_shell.columnconfigure(0, weight=1)
        self.chat_tabs_canvas = tk.Canvas(tabs_shell, bg="#08111f", height=33, highlightthickness=0, bd=0)
        self.chat_tabs_canvas.grid(row=0, column=0, sticky="ew")
        self.chat_tabs_scrollbar = ttk.Scrollbar(tabs_shell, orient="horizontal", command=self.chat_tabs_canvas.xview, style="Horizontal.TScrollbar")
        self.chat_tabs_scrollbar.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.chat_tabs_canvas.configure(xscrollcommand=self.chat_tabs_scrollbar.set)
        self.chat_tabs_frame = tk.Frame(self.chat_tabs_canvas, bg="#08111f")
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

        messages_shell = tk.Frame(panel, bg="#08111f")
        messages_shell.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 10))
        messages_shell.columnconfigure(0, weight=1)
        messages_shell.rowconfigure(0, weight=1)
        self.messages_canvas = tk.Canvas(messages_shell, bg="#0b1424", highlightthickness=1, highlightbackground="#182d49", height=320)
        self.messages_canvas.grid(row=0, column=0, sticky="nsew")
        self.messages_scrollbar = ttk.Scrollbar(messages_shell, orient="vertical", command=self.messages_canvas.yview, style="Vertical.TScrollbar")
        self.messages_scrollbar.grid(row=0, column=1, sticky="ns")
        self.messages_canvas.configure(yscrollcommand=self.messages_scrollbar.set)
        self.messages_inner = tk.Frame(self.messages_canvas, bg="#0b1424")
        self.messages_window = self.messages_canvas.create_window((0, 0), window=self.messages_inner, anchor="nw")
        self.messages_inner.bind("<Configure>", lambda _event: self.messages_canvas.configure(scrollregion=self.messages_canvas.bbox("all")))
        self.messages_canvas.bind("<Configure>", lambda event: self.messages_canvas.itemconfigure(self.messages_window, width=event.width))
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

        send_label_row = tk.Frame(panel, bg="#08111f")
        send_label_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 5))
        self.message_label = tk.Label(send_label_row, text=self.tr.t("home.chat.message"), bg="#08111f", fg="#8ab4ff", font=("Segoe UI", 9, "bold"))
        self.message_label.pack(side="left")

        send_row = tk.Frame(panel, bg="#0b1424", highlightthickness=1, highlightbackground="#24486d")
        send_row.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 16))
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

    def bind_messages_mousewheel(self, widget: tk.Widget) -> None:
        def on_mousewheel(event) -> str:
            self.messages_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        if not getattr(widget, "_chat_mousewheel_bound", False):
            widget.bind("<MouseWheel>", on_mousewheel, add="+")
            setattr(widget, "_chat_mousewheel_bound", True)
        for child in widget.winfo_children():
            self.bind_messages_mousewheel(child)

    def on_chat_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.chats):
            self.log(f"chat selection ignored index={index} chats={len(self.chats)}")
            return
        chat = self.chats[index]
        self.selected_chat_slug.set(str(chat.get("slug") or ""))
        self.selected_chat_label.set(self.format_chat_label(chat))
        self.update_chat_tab_styles()
        self.log(f"chat selected slug={self.selected_chat_slug.get()} label={self.selected_chat_label.get()}")
        self.load_messages()

    def set_active(self, active: bool) -> None:
        self.active = active
        if active:
            self.refresh_now()
        else:
            self.cancel_refresh()

    def refresh_language(self, translator) -> None:
        self.tr = translator
        self.log("language refreshed")
        self.apply_current_user_labels()
        self.messages_empty_label.configure(text=self.tr.t("home.chat.empty"))
        self.send_button.configure(text=self.tr.t("home.chat.send"))
        self.refresh_button.configure(text=self.tr.t("home.chat.refresh"))
        self.connected_label.configure(text=self.tr.t("home.chat.connected_as"))
        self.rooms_label.configure(text=self.tr.t("home.chat.rooms"))
        self.message_label.configure(text=self.tr.t("home.chat.message"))
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
            if self.selected_chat_slug.get():
                self.load_messages()

    def cancel_refresh(self) -> None:
        if self.refresh_job:
            try:
                self.after_cancel(self.refresh_job)
            except tk.TclError:
                pass
            self.refresh_job = None

    def schedule_refresh(self) -> None:
        self.cancel_refresh()
        if self.active:
            self.refresh_job = self.after(3000, self.poll_refresh)

    def poll_refresh(self) -> None:
        self.refresh_job = None
        if not self.active:
            return
        if self.selected_chat_slug.get():
            self.load_messages()
        self.schedule_refresh()

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
                self.after(0, self.set_error, self.tr.t("home.chat.auth_error", message=str(exc)))
            finally:
                self.auth_in_flight = False

        threading.Thread(target=worker, daemon=True).start()

    def apply_auth_result(self, result: dict[str, Any]) -> None:
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
        self.load_chats()

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
        self.chats = sorted(chats, key=lambda item: int(item.get("order") or 0))
        self.render_chat_tabs()
        if not self.chats:
            self.log("no chats available")
            self.status_var.set(self.tr.t("home.chat.no_chats"))
            self.selected_chat_slug.set("")
            self.selected_chat_label.set("")
            return
        current = self.selected_chat_slug.get()
        valid_slugs = {str(chat.get("slug") or "") for chat in self.chats}
        if current not in valid_slugs:
            current = str(self.chats[0].get("slug") or "")
            self.selected_chat_slug.set(current)
            self.log(f"default chat selected slug={current}")
        self.sync_selected_chat_label()
        self.status_var.set(self.tr.t("home.chat.ready"))
        self.load_messages()

    def format_chat_label(self, chat: dict[str, Any]) -> str:
        name = str(chat.get("name") or chat.get("slug") or "-")
        count = chat.get("_count", {}).get("messages")
        if isinstance(count, int):
            return f"{name} ({count})"
        return name

    def format_chat_tab_label(self, chat: dict[str, Any]) -> str:
        return str(chat.get("name") or chat.get("slug") or "-")

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
        self.update_chat_tab_styles()
        self.after(0, self.refresh_chat_tabs_scroll)

    def update_chat_tab_styles(self) -> None:
        current = self.selected_chat_slug.get().strip()
        for slug, button in self.chat_tab_buttons.items():
            if slug == current:
                button.configure(bg="#5eead4", fg="#041014", activebackground="#8ab4ff", activeforeground="#041014", font=("Segoe UI", 9, "bold"))
            else:
                button.configure(bg="#0f1b2e", fg="#cbd8ea", activebackground="#182d49", activeforeground="#edf6ff", font=("Segoe UI", 9))

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
        for index, chat in enumerate(self.chats):
            if str(chat.get("slug") or "") == slug:
                label = self.format_chat_label(chat)
                self.selected_chat_label.set(label)
                self.room_title_var.set(self.tr.t("home.chat.current_room", room=label))
                self.update_chat_tab_styles()
                return
        if self.chats:
            label = self.format_chat_label(self.chats[0])
            self.selected_chat_label.set(label)
            self.room_title_var.set(self.tr.t("home.chat.current_room", room=label))
            self.update_chat_tab_styles()
        else:
            self.room_title_var.set("")

    def load_messages(self) -> None:
        slug = self.selected_chat_slug.get().strip()
        if not slug:
            self.log(f"load messages skipped slug={slug!r} inflight={self.messages_in_flight}")
            return
        if self.messages_in_flight:
            self.pending_message_slug = slug
            self.status_var.set(self.tr.t("home.chat.loading"))
            self.log(f"load messages queued slug={slug!r}")
            return
        self.messages_in_flight = True
        self.pending_message_slug = None
        self.status_var.set(self.tr.t("home.chat.loading"))
        self.log(f"load messages started slug={slug}")

        def worker() -> None:
            try:
                path = f"/chat/chats/{urllib.parse.quote(slug)}/messages?take=50"
                self.log(f"messages request GET {path}")
                result = _http_json("GET", path, token=self.chat_token)
                messages = list(result.get("messages") or [])
                self.log(f"messages response slug={slug} count={len(messages)}")
                self.after(0, self.apply_messages_result, messages, slug)
            except Exception as exc:
                self.log(f"messages error slug={slug}: {exc}")
                self.after(0, self.set_error, self.tr.t("home.chat.message_error", message=str(exc)))
            finally:
                self.messages_in_flight = False
                pending = self.pending_message_slug
                if pending and pending != slug:
                    self.after(0, self.load_messages)
                elif self.active and self.selected_chat_slug.get().strip() == slug:
                    self.after(0, self.schedule_refresh)

        threading.Thread(target=worker, daemon=True).start()

    def apply_messages_result(self, messages: list[dict[str, Any]], slug: str) -> None:
        if self.selected_chat_slug.get() != slug:
            self.log(f"message result ignored slug={slug} current={self.selected_chat_slug.get()}")
            return
        self.log(f"apply messages slug={slug} count={len(messages)}")
        self.messages = messages
        self.render_messages()
        self.status_var.set(self.tr.t("home.chat.ready"))
        if self.active:
            self.schedule_refresh()

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
        slug = self.selected_chat_slug.get().strip()
        if not slug:
            self.log("send aborted: no selected chat")
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
                self.after(0, self.set_error, self.tr.t("home.chat.send_error", message=str(exc)))
            finally:
                self.after(0, lambda: self.send_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def after_send_message(self, message: dict[str, Any], fallback_content: str) -> None:
        self.input_var.set("")
        if message:
            self.log("send applied from response")
            self.messages.append(message)
            self.render_messages()
        else:
            self.log("send response empty, reloading messages")
            self.load_messages()
        self.status_var.set(self.tr.t("home.chat.sent"))
        if self.active:
            self.schedule_refresh()

    def set_error(self, text: str) -> None:
        self.log(f"ui error: {text}")
        self.status_var.set(text)

    def render_messages(self) -> None:
        for child in self.messages_inner.winfo_children():
            child.destroy()
        self.message_image_refs = []
        if not self.messages:
            tk.Label(
                self.messages_inner,
                text=self.tr.t("home.chat.empty"),
                bg="#0b1424",
                fg="#99abc4",
                font=("Segoe UI", 10, "bold"),
                pady=12,
            ).pack(fill="x", padx=8, pady=8)
            return

        for message in self.messages:
            self.render_message_row(message)
        self.bind_messages_mousewheel(self.messages_inner)
        self.after(0, lambda: self.messages_canvas.yview_moveto(1.0))

    def render_message_row(self, message: dict[str, Any]) -> None:
        row = tk.Frame(self.messages_inner, bg="#0b1424")
        row.pack(fill="x", padx=10, pady=(8, 0), anchor="w")
        accent = tk.Frame(row, bg="#24486d", width=3)
        accent.pack(side="left", fill="y", padx=(0, 8))
        avatar_url = self.message_avatar_url(message)
        avatar = self.get_avatar_image(avatar_url, size=28)
        avatar_label = tk.Label(row, image=avatar, bg="#0b1424")
        avatar_label.image = avatar
        avatar_label.pack(side="left", anchor="n", padx=(0, 8), pady=8)
        self.message_image_refs.append(avatar)

        body = tk.Frame(row, bg="#0f1b2e", highlightthickness=1, highlightbackground="#182d49")
        body.pack(side="left", fill="x", expand=True)
        header = tk.Frame(body, bg="#0f1b2e")
        header.pack(fill="x", padx=10, pady=(7, 1))
        user = message.get("user") or {}
        name = str(user.get("personaname") or user.get("nickname") or self.tr.t("home.chat.no_user"))
        created = str(message.get("createdAt") or message.get("created_at") or "")
        edited = message.get("editedAt") or message.get("edited_at")
        tk.Label(header, text=name, bg="#0f1b2e", fg="#8ab4ff", font=("Segoe UI", 9, "bold")).pack(side="left")
        meta_text = created[:19].replace("T", " ") if created else ""
        if edited:
            meta_text = f"{meta_text}  {self.tr.t('home.chat.edited')}"
        tk.Label(header, text=meta_text, bg="#0f1b2e", fg="#7f90aa", font=("Segoe UI", 8)).pack(side="right")
        content = str(message.get("content") or "")
        tk.Label(
            body,
            text=content,
            bg="#0f1b2e",
            fg="#edf6ff",
            font=("Segoe UI", 10),
            wraplength=520,
            justify="left",
        ).pack(fill="x", padx=10, pady=(0, 9))

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
        self.render_messages()

    def stop(self) -> None:
        self.log("panel stopped")
        self.cancel_refresh()
