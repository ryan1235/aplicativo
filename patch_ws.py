import re

with open('qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add _ws to init
init_injection = '''
        self._ws = QWebSocket()
        self._ws.connected.connect(self._on_ws_connected)
        self._ws.disconnected.connect(self._on_ws_disconnected)
        self._ws.textMessageReceived.connect(self._on_ws_text_received)
'''
code = re.sub(r'(self\._auto_connect_timer\.start\(\)\n\s+QTimer\.singleShot\(0, self\._maybe_auto_connect\))', r'\1' + init_injection, code)

# Add WS methods
ws_methods = '''
    def _connect_ws(self) -> None:
        if not self._token: return
        self._ws.close()
        url = QUrl(f"{CHAT_WS_BASE}/ws/chat?token={self._token}")
        self._ws.open(url)

    @Slot()
    def _on_ws_connected(self) -> None:
        self._status = self._t("home.chat.connected")
        self.changed.emit()
        if self._selected_room:
            self._ws.sendTextMessage(json.dumps({"type": "join_chat", "chatSlug": self._selected_room}))

    @Slot()
    def _on_ws_disconnected(self) -> None:
        if self._token:
            QTimer.singleShot(5000, self._connect_ws)

    @Slot(str)
    def _on_ws_text_received(self, text: str) -> None:
        try:
            data = json.loads(text)
        except Exception:
            return
        dtype = data.get("type")
        if dtype == "message_created":
            msg = data.get("message")
            if msg:
                self._handle_ws_message(msg)
        elif dtype == "message_updated" or dtype == "message_reaction_updated":
            msg = data.get("message")
            if msg:
                self._handle_ws_message_update(msg)
        elif dtype == "message_deleted":
            msg_id = data.get("messageId") or (data.get("message") or {}).get("id")
            if msg_id:
                self._handle_ws_message_delete(msg_id)

    def _handle_ws_message(self, msg: dict) -> None:
        rows = normalize_messages([msg], self.currentUserName, self._current_user_steam_id, self.discordId)
        if not rows: return
        row = rows[0]
        current_rows = [self.messages.get(i) for i in range(self.messages.count())]
        current_rows.append(row)
        self.messages.set_items(current_rows)
        self.changed.emit()

    def _handle_ws_message_update(self, msg: dict) -> None:
        rows = normalize_messages([msg], self.currentUserName, self._current_user_steam_id, self.discordId)
        if not rows: return
        row = rows[0]
        current_rows = [self.messages.get(i) for i in range(self.messages.count())]
        for i, r in enumerate(current_rows):
            if str(r.get("id")) == str(row["id"]):
                current_rows[i] = row
                break
        self.messages.set_items(current_rows)
        self.changed.emit()

    def _handle_ws_message_delete(self, msg_id: str) -> None:
        current_rows = [self.messages.get(i) for i in range(self.messages.count())]
        current_rows = [r for r in current_rows if str(r.get("id")) != str(msg_id)]
        self.messages.set_items(current_rows)
        self.changed.emit()

'''

target = """    @Slot()
    def shutdown(self) -> None:
        self._refresh_timer.stop()
        self._notification_timer.stop()
        self._presence_timer.stop()
        self._auto_connect_timer.stop()"""

code = code.replace(target, ws_methods + "\n" + target)

with open('qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched successfully')
