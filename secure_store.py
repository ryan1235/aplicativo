import os
import json
import ctypes
from ctypes import wintypes
from pathlib import Path
from app_paths import user_data_dir

# DPAPI Constants
CRYPTPROTECT_UI_FORBIDDEN = 0x01

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]

def _get_credentials_path() -> Path:
    return user_data_dir() / "felb_credentials.bin"

def secure_save_credentials(auto_login_key: str, access_password: str) -> None:
    data = json.dumps({
        "autoLoginKey": auto_login_key,
        "accessPassword": access_password
    }).encode("utf-8")
    
    blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    
    if ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        "FELB Chat Credentials",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(blob_out)
    ):
        encrypted_data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        
        path = _get_credentials_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encrypted_data)
    else:
        raise RuntimeError("Falha ao criptografar credenciais via DPAPI.")

def secure_load_credentials() -> tuple[str, str] | None:
    path = _get_credentials_path()
    if not path.exists():
        return None
        
    try:
        encrypted_data = path.read_bytes()
        blob_in = DATA_BLOB(len(encrypted_data), ctypes.cast(ctypes.c_char_p(encrypted_data), ctypes.POINTER(ctypes.c_char)))
        blob_out = DATA_BLOB()
        
        if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out)
        ):
            decrypted_data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            
            parsed = json.loads(decrypted_data.decode("utf-8"))
            return parsed.get("autoLoginKey", ""), parsed.get("accessPassword", "")
        else:
            return None
    except Exception:
        return None

def secure_clear_credentials() -> None:
    path = _get_credentials_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
