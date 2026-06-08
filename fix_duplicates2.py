import re

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

def remove_method(code, name):
    # Matches `@Slot... def method(...) ... threading.Thread(target=run, daemon=True).start()`
    # We use a non-greedy match.
    pattern = r'    @Slot\(str\)\n    def ' + name + r'\(self.*?\n        threading\.Thread\(target=run, daemon=True\)\.start\(\)\n'
    return re.sub(pattern, "", code, flags=re.DOTALL)

code = remove_method(code, "fetchProfile")
code = remove_method(code, "updateRegiment")
code = remove_method(code, "postStockpileHelp")

# Now re-insert them into ChatController
target = r'    @Slot\(\)\n    def logout\(self\) -> None:'

methods = '''    @Slot(str)
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
                res = http_json("PATCH", "/chat/profile", token=self._token, payload={"regiment": regiment})
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
                http_json("POST", "/chat/profile/stock-help", token=self._token, payload={"note": note})
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    @Slot()
    def logout(self) -> None:'''

# The target might be present multiple times! We ONLY want to replace it inside `class ChatController(QObject):`
# So let's split the code and inject.
idx = code.find("class ChatController(QObject):")
if idx != -1:
    idx_logout = code.find("    @Slot()\n    def logout(self) -> None:", idx)
    if idx_logout != -1:
        code = code[:idx_logout] + methods + code[idx_logout + len("    @Slot()\n    def logout(self) -> None:"):]

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Methods removed and injected successfully.")
