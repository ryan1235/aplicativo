import re

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\auto_clicker.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add to __init__
init_target = '''        self.last_pilot_until = 0.0'''
init_add = '''        self.last_pilot_until = 0.0

        # Artilharia: R + Left Click
        self.artillery_hotkey_name = "F7"
        self.artillery_hotkey_vk = ACTION_KEYS[self.artillery_hotkey_name]
        self.artillery_enabled = False'''
code = code.replace(init_target, init_add)

# Add to configure_action_hotkeys
config_target = '''    def configure_action_hotkeys(self, move_hotkey: str, fixed_hotkey: str, pilot_hotkey: str) -> None:'''
config_add = '''    def configure_action_hotkeys(self, move_hotkey: str, fixed_hotkey: str, pilot_hotkey: str, artillery_hotkey: str = "F7") -> None:'''
code = code.replace(config_target, config_add)

config2_target = '''        self.pilot_hotkey_name = pilot_hotkey if pilot_hotkey in ACTION_KEYS else "F4"'''
config2_add = '''        self.pilot_hotkey_name = pilot_hotkey if pilot_hotkey in ACTION_KEYS else "F4"
        self.artillery_hotkey_name = artillery_hotkey if artillery_hotkey in ACTION_KEYS else "F7"'''
code = code.replace(config2_target, config2_add)

config3_target = '''        self.pilot_hotkey_vk = ACTION_KEYS[self.pilot_hotkey_name]'''
config3_add = '''        self.pilot_hotkey_vk = ACTION_KEYS[self.pilot_hotkey_name]
        self.artillery_hotkey_vk = ACTION_KEYS[self.artillery_hotkey_name]'''
code = code.replace(config3_target, config3_add)

# Stop event
stop_target = '''        self.disable_move_click("stop")'''
stop_add = '''        self.disable_move_click("stop")
        self.disable_artillery("stop")'''
code = code.replace(stop_target, stop_add)

# Status text
status1_target = '''        running = self.enabled or self.fixed_click_enabled'''
status1_add = '''        running = self.enabled or self.fixed_click_enabled or self.artillery_enabled'''
code = code.replace(status1_target, status1_add)

status2_target = '''        if time.monotonic() < self.last_pilot_until:
            mode.append(self.pilot_hotkey_name)'''
status2_add = '''        if time.monotonic() < self.last_pilot_until:
            mode.append(self.pilot_hotkey_name)
        if self.artillery_enabled:
            mode.append(self.artillery_hotkey_name)'''
code = code.replace(status2_target, status2_add)

# Watch keys
watch_target = '''            self.fixed_hotkey_vk,'''
watch_add = '''            self.fixed_hotkey_vk,
            self.artillery_hotkey_vk,'''
code = code.replace(watch_target, watch_add)

# Check loop keys
loopkeys_target = '''            self.handle_key_press(self.pilot_hotkey_vk, self.run_forward_sequence)'''
loopkeys_add = '''            self.handle_key_press(self.pilot_hotkey_vk, self.run_forward_sequence)
            self.handle_key_press(self.artillery_hotkey_vk, self.toggle_artillery)'''
code = code.replace(loopkeys_target, loopkeys_add)

# Cancel shortcuts
cancel_target = '''        if self.fixed_click_enabled and (esc or lbtn or rbtn or mbtn or wasd):
            self.disable_fixed_click("cancel: mouse/wasd/esc")'''
cancel_add = '''        if self.fixed_click_enabled and (esc or lbtn or rbtn or mbtn or wasd):
            self.disable_fixed_click("cancel: mouse/wasd/esc")

        if self.artillery_enabled and (esc or rbtn or mbtn or wasd):
            self.disable_artillery("cancel: mouse/wasd/esc")'''
code = code.replace(cancel_target, cancel_add)

# Add toggle functions and update click_loop
# Wait, click_loop needs the new artillery branch
loop_target = '''            else:
                time.sleep(0.05)'''
loop_add = '''            elif self.artillery_enabled:
                self.refresh_target_if_needed()
                if self.target_hwnd and self.user32.IsWindow(self.target_hwnd):
                    self.waiting_for_foxhole = False
                    self.artillery_step()
                    now = time.monotonic()
                    if now - self.last_status_update >= 1:
                        self.last_status_update = now
                        self.status_callback(self.status_text())
                    time.sleep(self.interval)
                else:
                    if not self.waiting_for_foxhole:
                        self.waiting_for_foxhole = True
                        self.log("Aguardando Foxhole: target inexistente ou janela fechada")
                        self.status_callback(self.status_text())
                    time.sleep(0.12)
            else:
                time.sleep(0.05)'''
code = code.replace(loop_target, loop_add)

methods_add = '''

    def toggle_artillery(self) -> None:
        if self.artillery_enabled:
            self.disable_artillery(f"{self.artillery_hotkey_name} off")
        else:
            self.enable_artillery()

    def enable_artillery(self) -> None:
        self.pause()
        self.disable_fixed_click("artillery on")
        self.use_foxhole_window()
        self.artillery_enabled = True
        self.waiting_for_foxhole = False
        self.log(f"{self.artillery_hotkey_name} on: artilharia ativa")
        self.status_callback(self.status_text())

    def disable_artillery(self, reason: str) -> None:
        if not self.artillery_enabled:
            return
        self.artillery_enabled = False
        self.waiting_for_foxhole = False
        self.log(f"{self.artillery_hotkey_name} off: {reason}")
        self.status_callback(self.status_text())

    def artillery_step(self) -> None:
        # Press R
        vk_r = 0x52
        hwnd = self.click_hwnd or self.target_hwnd
        if not hwnd:
            return
        self.send_key_pair(vk_r)
        time.sleep(0.02)
        # Click left
        self.click_at(hwnd, self.click_x, self.click_y, "Esquerdo")

    def run_forward_sequence(self) -> None:'''
code = code.replace('''    def run_forward_sequence(self) -> None:''', methods_add)

with open(r'c:\Users\ryanl\OneDrive\Desktop\aplicativo\auto_clicker.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("auto_clicker.py patched!")
