import re

with open('qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

profile_property = '''
    @Property("QVariantMap", notify=changed)
    def userProfile(self) -> dict:
        return getattr(self, "_profile", {})

    @Slot()
    def logout(self) -> None:
        self._token = ""
        self._discord_user_settings.clear()
        save_settings(self.settings)
        self._ws.close()
        self._discord_login_required = True
        self._current_user_id = ""
        self._profile = {}
        self._status = "Disconnected"
        self.changed.emit()

'''

code = re.sub(r'(    @Property\(str, notify=changed\)\n    def status\(self\) -> str:)', profile_property + r'\1', code)

with open('qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched profile successfully')
