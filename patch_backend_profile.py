import re

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add endpoints to ChatController
endpoints_target = '''    @Property(str, notify=changed)
    def status(self) -> str:'''

endpoints_replacement = '''    @Slot(str)
    def fetchProfile(self, user_id: str = "") -> None:
        if not self._token:
            return
        def run():
            try:
                if user_id:
                    res = http_json("GET", f"/chat/users/{user_id}/profile", token=self._token)
                else:
                    res = http_json("GET", "/chat/profile", token=self._token)
                self.resultFromWorker.emit("profile-fetched", res.get("profile", {}))
            except Exception as e:
                self.resultFromWorker.emit("profile-error", str(e))
        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def updateRegiment(self, regiment: str) -> None:
        if not self._token:
            return
        def run():
            try:
                res = http_json("PATCH", "/chat/profile", token=self._token, data={"regiment": regiment})
                self.resultFromWorker.emit("profile-updated", res.get("profile", {}))
            except Exception as e:
                self.resultFromWorker.emit("profile-error", str(e))
        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def postStockpileHelp(self, note: str) -> None:
        if not self._token:
            return
        def run():
            try:
                http_json("POST", "/chat/profile/stock-help", token=self._token, data={"note": note})
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    @Property(str, notify=changed)
    def status(self) -> str:'''

code = code.replace(endpoints_target, endpoints_replacement)

# Update StockpileController to trigger postStockpileHelp
stockpile_hook_target = '''            if message.get("kind") == "api_snapshot":
                self._status = "API data loaded."
            else:
                self._status = f"{self._report_count} reports, {self._item_count} items"
            self._append_log(self._last_response)'''

stockpile_hook_replacement = '''            if message.get("kind") == "api_snapshot":
                self._status = "API data loaded."
            else:
                self._status = f"{self._report_count} reports, {self._item_count} items"
                if message.get("payload_changed") and self.parent():
                    # Attempt to invoke postStockpileHelp on the chat controller
                    try:
                        app = QApplication.instance()
                        for obj in app.children():
                            if type(obj).__name__ == "ControllerRegistry":
                                obj.chatController.postStockpileHelp("Estoque atualizado")
                                break
                    except Exception:
                        pass
            self._append_log(self._last_response)'''

code = code.replace(stockpile_hook_target, stockpile_hook_replacement)


# Also in _handle_auth (where resultFromWorker receives stuff for ChatController)
handle_auth_target = '''        elif kind == "sent":
            self._status = self._t("home.chat.sent")
            self.selectRoom(self._selected_room)'''

handle_auth_replacement = '''        elif kind == "sent":
            self._status = self._t("home.chat.sent")
            self.selectRoom(self._selected_room)
        elif kind == "profile-fetched" or kind == "profile-updated":
            if isinstance(payload, dict):
                # If it's my own profile (no ID passed, or ID matches me), save to self._profile
                if not payload.get("id") or payload.get("id") == self._current_user_id or kind == "profile-updated":
                    self._profile = payload
                    self.changed.emit()
                else:
                    # Notify UI about someone else's profile
                    self.resultFromWorker.emit("other-profile-ready", payload)'''

code = code.replace(handle_auth_target, handle_auth_replacement)

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Backend patched")
