import re

with open('qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace sendMessage
send_message_code = '''    @Slot(str)
    def sendMessage(self, body: str) -> None:
        if not self._token or not self._selected_room or not body.strip():
            return
        self._ws.sendTextMessage(json.dumps({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": body.strip()
        }))

    @Slot(str, str)
    def sendMessageReply(self, body: str, replyToMessageId: str) -> None:
        if not self._token or not self._selected_room or not body.strip():
            return
        self._ws.sendTextMessage(json.dumps({
            "type": "send_message",
            "chatSlug": self._selected_room,
            "content": body.strip(),
            "replyToMessageId": replyToMessageId
        }))

    @Slot(str, str)
    def reactMessage(self, messageId: str, emoji: str) -> None:
        if not self._token or not messageId or not emoji: return
        self._ws.sendTextMessage(json.dumps({
            "type": "react_message",
            "messageId": messageId,
            "emoji": emoji
        }))

    @Slot(str, str)
    def sendWhisperToUser(self, targetDiscordId: str, body: str) -> None:
        if not self._token or not targetDiscordId or not body.strip(): return
        self._ws.sendTextMessage(json.dumps({
            "type": "send_whisper",
            "targetDiscordId": targetDiscordId,
            "content": body.strip()
        }))
'''

code = re.sub(r'    @Slot\(str\)\n    def sendMessage\(self, body: str\) -> None:(?:.*?(?=    @Slot\(str\)\n    def sendGif))', send_message_code, code, flags=re.DOTALL)

# Add fetchProfile inside _apply_result when auth succeeds
auth_patch = '''            self._status = self._t("home.chat.connected") if self._token else "Connected without token"
            if self._token:
                try:
                    profile_res = http_json("GET", "/chat/profile", token=self._token)
                    self._profile = profile_res.get("profile", {})
                    self.changed.emit()
                except Exception:
                    pass
                self._connect_ws()
'''
code = re.sub(r'            self\._status = self\._t\("home\.chat\.connected"\) if self\._token else "Connected without token"\n            if self\._token:', auth_patch, code)

with open('qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched actions successfully')
