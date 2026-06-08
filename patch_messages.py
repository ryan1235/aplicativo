import re

with open('qt_controllers.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Update DictListModel
old_dict_model = '''        self.messages = DictListModel(
            ["id", "author", "body", "meta", "rawTime", "sortKey", "mine", "avatar", "mediaUrl", "isGif", "mentioned"],
            self,
        )'''
new_dict_model = '''        self.messages = DictListModel(
            ["id", "author", "body", "meta", "rawTime", "sortKey", "mine", "avatar", "mediaUrl", "isGif", "mentioned", "reactions", "replyToMessageId", "replyToAuthor", "replyToBody"],
            self,
        )'''
code = code.replace(old_dict_model, new_dict_model)

# Update normalize_messages
old_normalize_end = '''                "mediaUrl": media_url,
                "isGif": media_url.lower().split("?", 1)[0].endswith(".gif"),
                "mentioned": mentioned,
            }
        )'''
new_normalize_end = '''                "mediaUrl": media_url,
                "isGif": media_url.lower().split("?", 1)[0].endswith(".gif"),
                "mentioned": mentioned,
                "reactions": message.get("reactions") or [],
                "replyToMessageId": str(message.get("replyToMessageId") or ""),
                "replyToAuthor": str((message.get("replyToMessage") or {}).get("authorName") or ""),
                "replyToBody": str((message.get("replyToMessage") or {}).get("content") or ""),
            }
        )'''
code = code.replace(old_normalize_end, new_normalize_end)

with open('qt_controllers.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Patched dict model and normalize successfully')
