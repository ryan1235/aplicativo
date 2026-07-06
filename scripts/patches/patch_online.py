import re

with open('qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_online_model = '''        self.onlineUsers = DictListModel(["name", "detail", "avatar", "mention"], self)
        self.mentionSuggestions = DictListModel(["name", "detail", "avatar", "mention"], self)'''
new_online_model = '''        self.onlineUsers = DictListModel(["name", "detail", "avatar", "mention", "discordId"], self)
        self.mentionSuggestions = DictListModel(["name", "detail", "avatar", "mention", "discordId"], self)'''
code = code.replace(old_online_model, new_online_model)

old_user_row = '''            "name": name,
            "detail": detail,
            "avatar": str(user.get("avatarUrl") or user.get("avatar") or user.get("avatarfull") or user.get("avatarmedium") or ""),
            "mention": mention,
        }'''
new_user_row = '''            "name": name,
            "detail": detail,
            "avatar": str(user.get("avatarUrl") or user.get("avatar") or user.get("avatarfull") or user.get("avatarmedium") or ""),
            "mention": mention,
            "discordId": str(user.get("discordId") or ""),
        }'''
code = code.replace(old_user_row, new_user_row)

with open('qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched online models')
