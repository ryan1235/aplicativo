class ChatController(QObject):
    changed = Signal()
    resultFromWorker = Signal(str, object)

    def __init__(
        self,
        steam: SteamController,
        settings: dict[str, Any],
        i18n: I18nController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.steam = steam
        self.settings = settings
        self.i18n = i18n
        self._token = ""
        self._status = "Disconnected"
        self._selected_room = ""
        self._selected_room_label = ""
        self._next_message_cursor = ""
        self._loading_older_messages = False
        self._auth_in_flight = False
        self._rooms_in_flight = False
        self._messages_in_flight = False
        self._auth_retry_after = 0.0
        self._current_user_id = ""
        self._current_user_name = ""
        self._current_user_avatar = ""
        self._current_user_provider = ""
        self._current_user_discord_id = ""
        self._current_user_steam_id = ""
        self._discord_configuration_checked = False
        self._discord_login_required = False
        self._mention_overlay_visible = False
        self._mention_overlay_title = ""
        self._mention_overlay_body = ""
        app_settings = self.settings.setdefault("app", {})
        self._discord_user_settings = self.settings.setdefault("discord", {})
        self._discord_settings = app_settings.setdefault("chat_discord", {})
        seen_message_mentions = app_settings.get("chat_seen_message_mentions", [])
        self._known_message_ids: set[str] = set()
        self._notified_message_ids: set[str] = {str(item) for item in seen_message_mentions if str(item)}
        self._seeded_message_rooms: set[str] = set()
        seen_mentions = app_settings.get("chat_seen_mentions", [])
        self._known_mentions: set[str] = {str(item) for item in seen_mentions if str(item)}
        seen_whispers = app_settings.get("chat_seen_whispers", [])
        self._known_whispers: set[str] = {str(item) for item in seen_whispers if str(item)}
        self._notifications_seeded = False
        self._all_user_rows: list[dict[str, Any]] = []
        self._online_rows: list[dict[str, Any]] = []
        self.rooms = DictListModel(["slug", "label", "unread"], self)
        self.messages = DictListModel(
            ["id", "author", "body", "meta", "rawTime", "sortKey", "mine", "avatar", "mediaUrl", "isGif", "mentioned"],
            self,
        )
        self.onlineUsers = DictListModel(["name", "detail", "avatar", "mention"], self)
        self.mentionSuggestions = DictListModel(["name", "detail", "avatar", "mention"], self)
        self.resultFromWorker.connect(self._apply_result)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(15000)
        self._refresh_timer.timeout.connect(self.refreshCurrent)
        self._notification_timer = QTimer(self)
        self._notification_timer.setInterval(22000)
        self._notification_timer.timeout.connect(self.refreshNotifications)
        self._presence_timer = QTimer(self)
        self._presence_timer.setInterval(30000)
        self._presence_timer.timeout.connect(self.refreshPresence)
        self._auto_connect_timer = QTimer(self)
        self._auto_connect_timer.setInterval(2500)
        self._auto_connect_timer.timeout.connect(self._maybe_auto_connect)
        self.steam.changed.connect(self._maybe_auto_connect)
        self._auto_connect_timer.start()
        QTimer.singleShot(0, self._maybe_auto_connect)

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def selectedRoom(self) -> str:
        return self._selected_room

    @Property(str, notify=changed)
    def selectedRoomLabel(self) -> str:
        return self._selected_room_label

    @Property(bool, notify=changed)
    def hasOlderMessages(self) -> bool:
        return bool(self._next_message_cursor)

    @Property(bool, notify=changed)
    def loadingOlderMessages(self) -> bool:
        return self._loading_older_messages

    @Property(str, notify=changed)
    def currentUserName(self) -> str:
        return self._current_user_name or self._saved_discord_name() or self.steam.personaName

    @Property(str, notify=changed)
    def currentUserAvatar(self) -> str:
        return self._current_user_avatar or self._saved_discord_avatar() or self.steam.avatarUrl

    @Property(str, notify=changed)
    def currentProvider(self) -> str:
        return self._current_user_provider or ("discord" if self._saved_discord_id() else "steam")

    @Property(str, notify=changed)
    def discordId(self) -> str:
        return self._current_user_discord_id or self._saved_discord_id()

    @Property("QVariantList", notify=changed)
    def roomsRows(self) -> list[dict[str, Any]]:
        return self.rooms.items()

    @Property("QVariantList", notify=changed)
    def messagesRows(self) -> list[dict[str, Any]]:
        return self.messages.items()

    @Property("QVariantList", notify=changed)
    def onlineRows(self) -> list[dict[str, Any]]:
        return self.onlineUsers.items()

    @Property("QVariantList", notify=changed)
    def mentionSuggestionRows(self) -> list[dict[str, Any]]:
        return self.mentionSuggestions.items()

    @Property(bool, notify=changed)
    def connected(self) -> bool:
        return bool(self._token and (self._current_user_discord_id or self._saved_discord_id()))

    @Property(bool, notify=changed)
    def discordOAuthConfigured(self) -> bool:
        return bool(self._discord_client_id())

    @Property(str, notify=changed)
    def discordRedirectUri(self) -> str:
        return discord_redirect_uri(self._discord_redirect_port())

    @Property(bool, notify=changed)
    def discordConfigurationChecked(self) -> bool:
        return self._discord_configuration_checked

    @Property(bool, notify=changed)
    def discordLoginRequired(self) -> bool:
        return self._discord_login_required

    @Property(bool, notify=changed)
    def authInFlight(self) -> bool:
        return self._auth_in_flight

    @Property(bool, notify=changed)
    def mentionOverlayVisible(self) -> bool:
        return self._mention_overlay_visible

    @Property(str, notify=changed)
    def mentionOverlayTitle(self) -> str:
        return self._mention_overlay_title

    @Property(str, notify=changed)
    def mentionOverlayBody(self) -> str:
        return self._mention_overlay_body

    @Property("QStringList", constant=True)
    def quickEmojis(self) -> list[str]:
        return list(QUICK_EMOJIS)

    def _t(self, key: str, **kwargs: Any) -> str:
        return self.i18n.translator.t(key, **kwargs)

    def _saved_discord_id(self) -> str:
        return deobfuscate_string(str(self._discord_user_settings.get("id") or "").strip())

    def _saved_discord_name(self) -> str:
        return deobfuscate_string(str(self._discord_user_settings.get("displayName") or self._discord_user_settings.get("username") or "").strip())

    def _saved_discord_avatar(self) -> str:
        return deobfuscate_string(str(self._discord_user_settings.get("avatar") or "").strip())

    def _discord_client_id(self) -> str:
        return str(os.environ.get("DISCORD_CLIENT_ID") or self._discord_settings.get("clientId") or "").strip()

    def _discord_client_secret(self) -> str:
        return str(os.environ.get("DISCORD_CLIENT_SECRET") or self._discord_settings.get("clientSecret") or "").strip()

    def _discord_redirect_port(self) -> int:
        try:
            port = int(os.environ.get("DISCORD_REDIRECT_PORT") or self._discord_settings.get("redirectPort") or DISCORD_DEFAULT_REDIRECT_PORT)
        except (TypeError, ValueError):
            return DISCORD_DEFAULT_REDIRECT_PORT
        return port if 1024 <= port <= 65535 else DISCORD_DEFAULT_REDIRECT_PORT

    def _save_discord_profile(self, user: dict[str, Any]) -> None:
        discord_id = str(user.get("discordId") or self._current_user_discord_id or self._saved_discord_id()).strip()
        if not discord_id:
            return
        self._discord_user_settings["id"] = obfuscate_string(discord_id)
        name = str(
            user.get("displayName")
            or user.get("globalName")
            or user.get("username")
            or user.get("name")
            or user.get("personaname")
            or self._current_user_name
            or self.steam.personaName
        ).strip()
        if name:
            self._discord_user_settings["displayName"] = obfuscate_string(name)
        username = str(user.get("username") or "").strip()
        if username:
            self._discord_user_settings["username"] = obfuscate_string(username)
        avatar = user_avatar_url(user).strip()
        if avatar:
            self._discord_user_settings["avatar"] = obfuscate_string(avatar)
        save_settings(self.settings)

    def _discord_oauth_profile(self) -> dict[str, Any]:
        client_id = self._discord_client_id()
        if not client_id:
            raise RuntimeError(self._t("home.chat.discord_config_missing", uri=self.discordRedirectUri))
        port = self._discord_redirect_port()
        redirect_uri = discord_redirect_uri(port)
        state = secrets.token_urlsafe(24)
        verifier = secrets.token_urlsafe(64)
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify",
            "state": state,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
        auth_url = f"{DISCORD_AUTHORIZE_URL}?{urllib.parse.urlencode(query)}"
        code = wait_for_discord_oauth_code(state, port, auth_url=auth_url, language=self.i18n.translator.language)
        form = {
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        }
        client_secret = self._discord_client_secret()
        if client_secret:
            form["client_secret"] = client_secret
        token_result = http_json_url("POST", DISCORD_TOKEN_URL, form=form, timeout=20)
        access_token = str(token_result.get("access_token") or "")
        if not access_token:
            raise RuntimeError("Discord OAuth did not return an access token.")
        user = http_json_url("GET", DISCORD_USER_URL, token=access_token, timeout=20)
        if not user.get("id"):
            raise RuntimeError("Discord OAuth did not return a user profile.")
        avatar_url = discord_avatar_url(user)
        if avatar_url:
            user["avatarUrl"] = avatar_url
            user["avatarfull"] = avatar_url
            user["avatarmedium"] = avatar_url
        user["discordId"] = str(user.get("id") or "")
        user["displayName"] = str(user.get("global_name") or user.get("username") or "")
        user["globalName"] = str(user.get("global_name") or "")
        user["discriminator"] = str(user.get("discriminator") or "")
        user["discordAvatar"] = str(user.get("avatar") or "")
        return user

    def _discord_auth_payload(self, discord_id: str) -> dict[str, str]:
        payload: dict[str, str] = {"discordId": discord_id}
        steam_id = self.steam.steamId
        if steam_id:
            payload["steamId"] = steam_id
        display_name = self._saved_discord_name() or self.steam.personaName
        if display_name:
            payload["displayName"] = display_name
            payload["personaname"] = display_name
        username = str(self._discord_settings.get("username") or "").strip()
        if username:
            payload["username"] = username
        avatar = self._saved_discord_avatar()
        if avatar:
            payload["avatar"] = avatar
            payload["avatarmedium"] = avatar
            payload["avatarfull"] = avatar
        return payload

    def _discord_auth_payload_from_profile(self, user: dict[str, Any]) -> dict[str, str]:
        discord_id = str(user.get("discordId") or user.get("id") or "").strip()
        payload = self._discord_auth_payload(discord_id)
        field_map = {
            "username": "username",
            "globalName": "globalName",
            "displayName": "displayName",
            "discriminator": "discriminator",
            "avatar": "avatar",
            "avatarfull": "avatarfull",
            "avatarmedium": "avatarmedium",
            "discordAvatar": "discordAvatar",
        }
        for target, source in field_map.items():
            value = str(user.get(source) or "").strip()
            if value:
                payload[target] = value
        return payload

    def _auth_with_discord(self, payload: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_DISCORD_AUTH_PATHS:
            try:
                return http_json("POST", path, payload=payload, timeout=12)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat auth failed")

    def _auth_with_steam(self, payload: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_STEAM_AUTH_PATHS:
            try:
                return http_json("POST", path, payload=payload, timeout=12)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat auth failed")

    def _request_users(self) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in CHAT_USERS_PATHS:
            try:
                return http_json("GET", path, token=self._token)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat users failed")

    def _request_online_users(self) -> dict[str, Any]:
        discord_id = self._current_user_discord_id or self._saved_discord_id()
        if discord_id:
            try:
                return http_json("POST", "/chat/presence/ping", token=self._token, payload={"discordId": discord_id}, timeout=10)
            except Exception:
                pass
        if self._current_user_id:
            try:
                return http_json("POST", "/chat/presence/ping", token=self._token, payload={"userId": self._current_user_id}, timeout=10)
            except Exception:
                pass
        steam_id = self._current_user_steam_id or self.steam.steamId
        if steam_id:
            try:
                return http_json("POST", "/chat/presence/ping", token=self._token, payload={"steamId": steam_id}, timeout=10)
            except Exception:
                pass
        last_error: Exception | None = None
        for path in CHAT_ONLINE_PATHS:
            try:
                return http_json("GET", path, token=self._token, timeout=10)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(str(last_error) if last_error else "chat online users failed")

    def _request_messages(self, slug: str, cursor: str = "") -> dict[str, Any]:
        path = f"/chat/chats/{urllib.parse.quote(slug)}/messages?take=50"
        if cursor:
            path = f"{path}&cursor={urllib.parse.quote(cursor)}"
        return http_json("GET", path, token=self._token)

    @Slot()
    def connectWithDiscord(self) -> None:
        self._connect_with_discord(allow_oauth=True)

    @Slot()
    def autoConnectWithSavedDiscord(self) -> None:
        if self._saved_discord_id():
            self._discord_configuration_checked = True
            self._discord_login_required = False
            self.changed.emit()
            self._connect_with_discord(allow_oauth=False)
            return
        self._discord_configuration_checked = True
        self._discord_login_required = True
        self._status = self._t("home.chat.no_discord")
        self.changed.emit()

    def _connect_with_discord(self, *, allow_oauth: bool = False) -> None:
        if self._auth_in_flight:
            return
        if self._token:
            self.refreshRooms()
            self.refreshPresence()
            self.refreshNotifications()
            return
        now = time.monotonic()
        if now < self._auth_retry_after:
            retry_seconds = int(max(1, self._auth_retry_after - now))
            self._status = self._t("home.chat.auth_needed") + f" ({retry_seconds}s)"
            self.changed.emit()
            return
        discord_id = self._saved_discord_id()
        if not discord_id:
            self._discord_configuration_checked = True
            self._discord_login_required = True
            if not allow_oauth:
                self._status = self._t("home.chat.no_discord")
                self.changed.emit()
                return
            if not self._discord_client_id():
                self._status = self._t("home.chat.discord_config_missing", uri=self.discordRedirectUri)
                self.changed.emit()
                return

        def worker() -> None:
            try:
                if discord_id:
                    result = self._auth_with_discord(self._discord_auth_payload(discord_id))
                else:
                    profile = self._discord_oauth_profile()
                    self._save_discord_profile(profile)
                    result = self._auth_with_discord(self._discord_auth_payload_from_profile(profile))
                self.resultFromWorker.emit("auth", result)
            except Exception as exc:
                message = str(exc)
                if "access_denied" in message or "oauth_cancelled" in message:
                    message = self._t("home.chat.discord_cancelled")
                self.resultFromWorker.emit("auth-error", self._t("home.chat.auth_error", message=message))

        self._auth_in_flight = True
        if discord_id:
            self._discord_login_required = False
        self._status = self._t("home.chat.authenticating_discord") if discord_id else self._t("home.chat.discord_opening")
        self.changed.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def connectWithSteam(self) -> None:
        if self._auth_in_flight:
            return
        if self._token:
            self.refreshRooms()
            self.refreshPresence()
            self.refreshNotifications()
            return
        now = time.monotonic()
        if now < self._auth_retry_after:
            retry_seconds = int(max(1, self._auth_retry_after - now))
            self._status = self._t("home.chat.auth_needed") + f" ({retry_seconds}s)"
            self.changed.emit()
            return
        profile_name = self.steam.personaName
        steam_id = self.steam.steamId
        if not steam_id:
            self._status = self._t("home.chat.no_steam")
            self.changed.emit()
            return

        def worker() -> None:
            try:
                payload = {"steamId": steam_id, "name": profile_name}
                result = self._auth_with_steam(payload)
                self.resultFromWorker.emit("auth", result)
            except Exception as exc:
                self.resultFromWorker.emit("auth-error", self._t("home.chat.auth_error", message=str(exc)))

        self._auth_in_flight = True
        self._status = self._t("home.chat.authenticating")
        self.changed.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def _maybe_auto_connect(self) -> None:
        if self._token:
            if self._auto_connect_timer.isActive():
                self._auto_connect_timer.stop()
            return
        if self._auth_in_flight:
            return
        if self._saved_discord_id():
            self._connect_with_discord(allow_oauth=False)
            return
        self._discord_configuration_checked = True
        self._discord_login_required = True
        self._status = self._t("home.chat.no_discord")
        self.changed.emit()

    @Slot()
    def refreshRooms(self) -> None:
        if not self._token:
            self.connectWithDiscord()
            return
        if self._rooms_in_flight:
            return
        self._rooms_in_flight = True

        def worker() -> None:
            try:
                self.resultFromWorker.emit("rooms", http_json("GET", "/chat/chats", token=self._token))
            except Exception as exc:
                self.resultFromWorker.emit("error", self._t("home.chat.chat_error", message=str(exc)))
                return
            try:
                self.resultFromWorker.emit("users", self._request_users())
            except Exception as exc:
                self.resultFromWorker.emit("users-error", str(exc))
            try:
                self.resultFromWorker.emit("online", self._request_online_users())
            except Exception as exc:
                self.resultFromWorker.emit("online-error", str(exc))
            finally:
                self.resultFromWorker.emit("rooms-finished", {})

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def refreshPresence(self) -> None:
        if not self._token:
            return

        def worker() -> None:
            try:
                self.resultFromWorker.emit("online", self._request_online_users())
            except Exception as exc:
                self.resultFromWorker.emit("online-error", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def refreshCurrent(self) -> None:
        if not self._token:
            return
        if self._selected_room:
            self.selectRoom(self._selected_room)
        else:
            self.refreshRooms()

    @Slot()
    def refreshNotifications(self) -> None:
        if not self._token:
            return

        def worker() -> None:
            try:
                result = http_json("GET", "/chat/notifications?unreadOnly=true&take=50", token=self._token, timeout=10)
                self.resultFromWorker.emit("notifications", result)
            except Exception:
                try:
                    result = http_json("GET", "/chat/mentions/notifications?unreadOnly=true&take=50", token=self._token, timeout=10)
                    self.resultFromWorker.emit("notifications", {"mentions": result.get("mentions") or []})
                except Exception as exc:
                    self.resultFromWorker.emit("notification-error", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def selectRoom(self, slug: str) -> None:
        room_changed = slug != self._selected_room
        self._selected_room = slug
        self._selected_room_label = self._room_label(slug)
        if room_changed:
            self._next_message_cursor = ""
            self._loading_older_messages = False
            self.messages.set_items([])
        self.changed.emit()
        if not self._token or not slug:
            return
        if self._messages_in_flight:
            return
        self._messages_in_flight = True

        def worker() -> None:
            try:
                self.resultFromWorker.emit(
                    "messages",
                    {
                        "slug": slug,
                        "appendOlder": False,
                        "result": self._request_messages(slug),
                    },
                )
            except Exception as exc:
                self.resultFromWorker.emit("error", self._t("home.chat.message_error", message=str(exc)))
            finally:
                self.resultFromWorker.emit("messages-finished", {})

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def loadOlderMessages(self) -> None:
        if not self._token or not self._selected_room or not self._next_message_cursor or self._loading_older_messages:
            return
        if self._messages_in_flight:
            return
        slug = self._selected_room
        cursor = self._next_message_cursor
        self._loading_older_messages = True
        self._messages_in_flight = True
        self._status = self._t("home.chat.loading_older")
        self.changed.emit()

        def worker() -> None:
            try:
                self.resultFromWorker.emit(
                    "messages",
                    {
                        "slug": slug,
                        "appendOlder": True,
                        "result": self._request_messages(slug, cursor),
                    },
                )
            except Exception as exc:
                self.resultFromWorker.emit("message-error", self._t("home.chat.message_error", message=str(exc)))
            finally:
                self.resultFromWorker.emit("messages-finished", {})

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def sendMessage(self, body: str) -> None:
        if not self._token or not self._selected_room or not body.strip():
            return
        self._status = self._t("home.chat.sending")
        self.changed.emit()

        def worker() -> None:
            try:
                path = f"/chat/chats/{urllib.parse.quote(self._selected_room)}/messages"
                result = http_json("POST", path, token=self._token, payload={"content": body.strip()})
                self.resultFromWorker.emit("sent", result)
            except Exception as exc:
                self.resultFromWorker.emit("error", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def sendGif(self, url: str) -> None:
        self.sendMessage(url)

    @Slot(str)
    def updateMentionSuggestions(self, text: str) -> None:
        token = self._mention_token(text)
        if token is None:
            self.mentionSuggestions.set_items([])
            self.changed.emit()
            return
        token_lower = token.casefold()
        rows = [
            row
            for row in self._online_rows
            if token_lower in str(row.get("name", "")).casefold() or token_lower in str(row.get("mention", "")).casefold()
        ][:8]
        self.mentionSuggestions.set_items(rows)
        self.changed.emit()

    @Slot(str, str, result=str)
    def applyMention(self, text: str, mention: str) -> str:
        match = None
        for candidate in MENTION_RE.finditer(text):
            match = candidate
        if match and match.end() == len(text):
            prefix = text[: match.start()]
            suffix = text[match.end() :]
            return f"{prefix}@{mention} {suffix}"
        spacer = "" if not text or text.endswith(" ") else " "
        return f"{text}{spacer}@{mention} "

    @Slot()
    def dismissMentionOverlay(self) -> None:
        self._mention_overlay_visible = False
        self.changed.emit()

    @Slot(str, object)
    def _apply_result(self, kind: str, payload: object) -> None:
        if kind == "auth" and isinstance(payload, dict):
            self._auth_in_flight = False
            self._auth_retry_after = 0.0
            self._discord_configuration_checked = True
            self._discord_login_required = False
            self._token = str(payload.get("token") or payload.get("accessToken") or "")
            user = payload.get("user") or payload.get("profile") or {}
            if isinstance(user, dict):
                self._current_user_id = str(user.get("id") or "")
                self._current_user_provider = str(user.get("provider") or ("discord" if user.get("discordId") else "steam"))
                self._current_user_discord_id = str(user.get("discordId") or self._saved_discord_id())
                self._current_user_steam_id = str(user.get("steamId") or self.steam.steamId)
                self._current_user_name = str(
                    user.get("displayName")
                    or user.get("globalName")
                    or user.get("name")
                    or user.get("personaName")
                    or user.get("personaname")
                    or user.get("nickname")
                    or user.get("username")
                    or self._saved_discord_name()
                    or self.steam.personaName
                )
                self._current_user_avatar = user_avatar_url(user)
                if self._current_user_discord_id:
                    self._save_discord_profile(user)
            else:
                self._current_user_id = ""
                self._current_user_provider = "discord" if self._saved_discord_id() else "steam"
                self._current_user_discord_id = self._saved_discord_id()
                self._current_user_name = self._saved_discord_name() or self.steam.personaName
                self._current_user_avatar = self._saved_discord_avatar() or self.steam.avatarUrl
                self._current_user_steam_id = self.steam.steamId
            self._status = self._t("home.chat.connected") if self._token else "Connected without token"
            if self._token:
                if self._auto_connect_timer.isActive():
                    self._auto_connect_timer.stop()
                self._notifications_seeded = False
                self._seeded_message_rooms.clear()
                self._refresh_timer.start()
                self._notification_timer.start()
                self._presence_timer.start()
                self.refreshNotifications()
            self.refreshRooms()
        elif kind == "auth-error":
            self._auth_in_flight = False
            self._discord_configuration_checked = True
            self._discord_login_required = not bool(self._saved_discord_id())
            self._auth_retry_after = time.monotonic() + 30
            self._status = str(payload)
        elif kind == "rooms" and isinstance(payload, dict):
            rooms = payload.get("chats") or payload.get("rooms") or []
            self.rooms.set_items([self._room_to_row(room) for room in rooms])
            self._status = f"{len(rooms)} chat rooms loaded"
            if not self._selected_room and rooms:
                first = self._room_to_row(rooms[0])
                self.selectRoom(str(first["slug"]))
        elif kind == "rooms-finished":
            self._rooms_in_flight = False
        elif kind == "users" and isinstance(payload, dict):
            users = payload.get("users") or []
            rows = [self._user_to_row(user) for user in users]
            self._all_user_rows = rows
            self._online_rows = self._merge_user_rows(self._online_rows, rows)
        elif kind == "online" and isinstance(payload, dict):
            users = payload.get("onlineUsers") or payload.get("users") or []
            online_rows = [self._user_to_row(user) for user in users]
            self._online_rows = self._merge_user_rows(online_rows, self._all_user_rows)
            self.onlineUsers.set_items(online_rows)
        elif kind == "messages" and isinstance(payload, dict):
            slug = str(payload.get("slug") or self._selected_room)
            if slug != self._selected_room:
                return
            result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
            append_older = bool(payload.get("appendOlder"))
            messages = (result.get("messages") or []) if isinstance(result, dict) else []
            rows = normalize_messages(
                messages,
                self._current_user_name or self._saved_discord_name() or self.steam.personaName,
                self._current_user_steam_id or self.steam.steamId,
                self._current_user_discord_id or self._saved_discord_id(),
            )
            current_rows = [self.messages.get(index) for index in range(self.messages.count())]
            if append_older or current_rows:
                rows = merge_message_rows(rows, current_rows)
            seed_mentions = append_older or slug not in self._seeded_message_rooms
            self._notify_mentions(rows, slug=slug, seed=seed_mentions)
            self._seeded_message_rooms.add(slug)
            if not same_message_rows(rows, current_rows):
                self.messages.set_items(rows)
            self._next_message_cursor = str(result.get("nextCursor") or "") if isinstance(result, dict) else ""
            self._loading_older_messages = False
            self._status = self._t("home.chat.ready")
        elif kind == "messages-finished":
            self._messages_in_flight = False
        elif kind == "sent":
            self._status = self._t("home.chat.sent")
            self.selectRoom(self._selected_room)
        elif kind == "notifications" and isinstance(payload, dict):
            self._apply_notifications(payload)
        elif kind == "notification-error":
            pass
        elif kind == "users-error":
            pass
        elif kind == "online-error":
            pass
        elif kind == "message-error":
            self._messages_in_flight = False
            self._loading_older_messages = False
            self._status = str(payload)
        elif kind == "error":
            self._messages_in_flight = False
            self._loading_older_messages = False
            self._status = str(payload)
        self.changed.emit()

    def _room_to_row(self, room: dict[str, Any]) -> dict[str, Any]:
        slug = str(room.get("slug") or room.get("id") or "")
        return {
            "slug": slug,
            "label": str(room.get("name") or room.get("label") or slug or "Room"),
            "unread": int(room.get("unreadCount") or room.get("unread") or 0),
        }

    def _room_label(self, slug: str) -> str:
        for index in range(self.rooms.count()):
            row = self.rooms.get(index)
            if row.get("slug") == slug:
                return str(row.get("label") or slug)
        return slug

    @staticmethod
    def _merge_user_rows(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in [*primary, *secondary]:
            key = str(row.get("mention") or row.get("name") or row.get("detail") or "").casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(row)
        return merged

    @staticmethod
    def _user_to_row(user: dict[str, Any]) -> dict[str, Any]:
        name = user_display_name(user)
        mention = str(user.get("mention") or user.get("username") or user.get("globalName") or name).strip().lstrip("@")
        detail = str(user.get("status") or "").strip()
        if not detail and user.get("provider") == "discord":
            detail = f"@{mention}" if mention else str(user.get("discordId") or "")
        if not detail:
            detail = str(user.get("steamId") or user.get("discordId") or "")
        return {
            "name": name,
            "detail": detail,
            "avatar": str(user.get("avatarUrl") or user.get("avatar") or user.get("avatarfull") or user.get("avatarmedium") or ""),
            "mention": mention,
        }

    @staticmethod
    def _mention_token(text: str) -> str | None:
        match = None
        for candidate in MENTION_RE.finditer(text):
            match = candidate
        if not match or match.end() != len(text):
            return None
        return match.group(1)

    def _notify_mentions(self, rows: list[dict[str, Any]], *, slug: str = "", seed: bool = False) -> None:
        seen_changed = False
        for row in rows:
            identity = str(row.get("id") or "")
            if not identity:
                continue
            new_message = identity not in self._known_message_ids
            if new_message:
                self._known_message_ids.add(identity)
            if row.get("mine") or not row.get("mentioned"):
                continue
            if seed or identity in self._notified_message_ids:
                if identity not in self._notified_message_ids:
                    self._notified_message_ids.add(identity)
                    seen_changed = True
                continue
            if not new_message:
                continue
            self._notified_message_ids.add(identity)
            seen_changed = True
            self._show_mention(
                self._t("home.chat.mention_title"),
                self._t("home.chat.mention_body", user=row.get("author") or "User", room=self._room_label(slug) or self._selected_room_label or self._selected_room or "-"),
            )
        if seen_changed:
            self._persist_seen_message_mentions()

    def _apply_notifications(self, payload: dict[str, Any]) -> None:
        mentions = payload.get("mentions") or []
        whispers = payload.get("whispers") or []
        if not self._notifications_seeded:
            mentions_changed = False
            whispers_changed = False
            for mention in mentions:
                mention_id = self._notification_identity(mention)
                if not mention_id:
                    continue
                if mention_id not in self._known_mentions:
                    self._known_mentions.add(mention_id)
                    mentions_changed = True
                threading.Thread(target=lambda mid=mention_id: self._mark_mention_read(mid), daemon=True).start()
            for whisper in whispers:
                whisper_id = self._notification_identity(whisper)
                if whisper_id and whisper_id not in self._known_whispers:
                    self._known_whispers.add(whisper_id)
                    whispers_changed = True
            self._notifications_seeded = True
            if mentions_changed:
                self._persist_seen_mentions()
            if whispers_changed:
                self._persist_seen_whispers()
            return

        self._notifications_seeded = True
        seen_changed = False
        for mention in mentions:
            mention_id = self._notification_identity(mention)
            if mention_id and mention_id in self._known_mentions:
                continue
            if mention_id:
                self._known_mentions.add(mention_id)
                seen_changed = True
            user = mention.get("mentionedBy") or mention.get("fromUser") or mention.get("user") or {}
            chat = mention.get("chat") or {}
            user_name = self._user_to_row(user if isinstance(user, dict) else {})["name"]
            room = str(chat.get("name") or chat.get("slug") or self._selected_room_label or "-") if isinstance(chat, dict) else self._selected_room_label
            self._show_mention(self._t("home.chat.mention_title"), self._t("home.chat.mention_body", user=user_name, room=room))
            if mention_id:
                threading.Thread(target=lambda mid=mention_id: self._mark_mention_read(mid), daemon=True).start()
        if seen_changed:
            self._persist_seen_mentions()
        whispers_changed = False
        for whisper in whispers:
            whisper_id = self._notification_identity(whisper)
            if whisper_id and whisper_id in self._known_whispers:
                continue
            if whisper_id:
                self._known_whispers.add(whisper_id)
                whispers_changed = True
            sender = whisper.get("fromUser") or whisper.get("sender") or whisper.get("user") or {}
            user_name = self._user_to_row(sender if isinstance(sender, dict) else {})["name"]
            self._show_mention(self._t("home.chat.whisper_title"), self._t("home.chat.whisper_body", user=user_name))
            break
        if whispers_changed:
            self._persist_seen_whispers()

    @staticmethod
    def _notification_identity(notification: dict[str, Any]) -> str:
        return str(notification.get("id") or notification.get("_id") or notification.get("messageId") or notification.get("notificationId") or "")

    def _mark_mention_read(self, mention_id: str) -> None:
        try:
            http_json("PATCH", f"/chat/mentions/{urllib.parse.quote(mention_id)}/read", token=self._token, timeout=8)
        except Exception:
            pass

    def _persist_seen_mentions(self) -> None:
        app_settings = self.settings.setdefault("app", {})
        app_settings["chat_seen_mentions"] = list(self._known_mentions)[-250:]
        save_settings(self.settings)

    def _persist_seen_whispers(self) -> None:
        app_settings = self.settings.setdefault("app", {})
        app_settings["chat_seen_whispers"] = list(self._known_whispers)[-250:]
        save_settings(self.settings)

    def _persist_seen_message_mentions(self) -> None:
        app_settings = self.settings.setdefault("app", {})
        app_settings["chat_seen_message_mentions"] = list(self._notified_message_ids)[-500:]
        save_settings(self.settings)

    def _show_mention(self, title: str, body: str) -> None:
        app_settings = self.settings.get("app", {})
        if app_settings.get("chat_mention_sound_enabled", True):
            self._play_mention_sound()
        if not app_settings.get("chat_mention_overlay_enabled", True):
            return
        self._mention_overlay_title = title
        self._mention_overlay_body = body
        self._mention_overlay_visible = True
        QTimer.singleShot(6500, self.dismissMentionOverlay)

    @staticmethod
    def _play_mention_sound() -> None:
        try:
            if os.name == "nt":
                import winsound

                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

    @Slot()
    def shutdown(self) -> None:
        self._refresh_timer.stop()
        self._notification_timer.stop()
        self._presence_timer.stop()
        self._auto_connect_timer.stop()


