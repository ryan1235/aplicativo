import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import io
import threading
from pathlib import Path

POPULAR_EMOJIS = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "🥲", "☺️", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🥸", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗", "🤔", "🫣", "🤭", "🫢", "🫡", "🤫", "🫠", "🤥", "😶", "😶‍🌫️", "😐", "😑", "😬", "🫨", "🙄", "😯", "😦", "😧", "😮", "😲", "🥱", "😴", "🤤", "😪", "😮‍💨", "😵", "😵‍💫", "🤐", "🥴", "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "😈", "👿", "👹", "👺", "🤡", "💩", "👻", "💀", "☠️", "👽", "👾", "🤖", "🎃", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾",
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❤️‍🔥", "❤️‍🩹", "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💯", "💢", "💥", "💫", "💦", "💨", "🕳️", "💣", "💬", "👁️‍🗨️", "🗨️", "🗯️", "💭", "💤",
    "👋", "🤚", "🖐️", "✋", "🖖", "🫱", "🫲", "🫳", "🫴", "👌", "🤌", "🤏", "✌️", "🤞", "🫰", "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", "👍", "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "🫶", "👐", "🤲", "🤝", "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃", "🧠", "🫀", "🫁", "🦷", "🦴", "👀", "👁️", "👅", "👄", "🫦",
    "🔥", "🌟", "✨", "⚡", "☀️", "🌤️", "⛅", "🌥️", "☁️", "🌦️", "🌧️", "⛈️", "🌩️", "🌨️", "❄️", "☃️", "⛄", "🌬️", "💨", "🌪️", "🌫️", "☂️", "☔", "💧", "💦", "🌊"
]

class EmojiGifPicker(tk.Toplevel):
    def __init__(self, parent: tk.Widget, panel) -> None:
        super().__init__(parent)
        self.panel = panel
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#2b2d31", highlightthickness=1, highlightbackground="#1e1f22")
        self.geometry("360x420")
        
        self.current_tab = "emoji"
        self.gif_images = []
        self.emoji_images = []
        
        tabs_frame = tk.Frame(self, bg="#2b2d31")
        tabs_frame.pack(fill="x", padx=10, pady=10)
        
        self.emoji_tab_btn = tk.Button(tabs_frame, text="Emojis", command=lambda: self.switch_tab("emoji"), bg="#404249", fg="#ffffff", relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2", bd=0)
        self.emoji_tab_btn.pack(side="left", padx=5)
        
        self.gif_tab_btn = tk.Button(tabs_frame, text="GIFs", command=lambda: self.switch_tab("gif"), bg="#2b2d31", fg="#b5bac1", relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2", bd=0)
        self.gif_tab_btn.pack(side="left", padx=5)
        
        close_btn = tk.Button(tabs_frame, text="✖", command=self.destroy, bg="#2b2d31", fg="#b5bac1", relief="flat", font=("Segoe UI", 10), cursor="hand2", bd=0)
        close_btn.pack(side="right", padx=5)
        
        self.container = tk.Frame(self, bg="#2b2d31")
        self.container.pack(fill="both", expand=True)
        
        self.emoji_frame = tk.Frame(self.container, bg="#2b2d31")
        self.gif_frame = tk.Frame(self.container, bg="#2b2d31")
        
        self.build_emoji_tab()
        self.build_gif_tab()
        
        self.switch_tab("emoji")
        
        self.bind("<FocusOut>", self.on_focus_out)

    def on_focus_out(self, event):
        if event.widget == self:
            self.after(200, self.destroy)

    def switch_tab(self, tab):
        self.current_tab = tab
        if tab == "emoji":
            self.gif_frame.pack_forget()
            self.emoji_frame.pack(fill="both", expand=True)
            self.emoji_tab_btn.configure(bg="#404249", fg="#ffffff")
            self.gif_tab_btn.configure(bg="#2b2d31", fg="#b5bac1")
        else:
            self.emoji_frame.pack_forget()
            self.gif_frame.pack(fill="both", expand=True)
            self.emoji_tab_btn.configure(bg="#2b2d31", fg="#b5bac1")
            self.gif_tab_btn.configure(bg="#404249", fg="#ffffff")

    def build_emoji_tab(self):
        canvas = tk.Canvas(self.emoji_frame, bg="#2b2d31", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.emoji_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2b2d31")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        row, col = 0, 0
        for em in POPULAR_EMOJIS:
            photo = self.panel.get_twemoji_async(em, size=30)
            self.emoji_images.append(photo)
            btn = tk.Button(
                scrollable_frame,
                image=photo if photo else "",
                text="" if photo else em,
                bg="#2b2d31",
                activebackground="#404249",
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda e=em: self.insert_emoji(e)
            )
            if photo:
                btn.image = photo
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 7:
                col = 0
                row += 1

    def build_gif_tab(self):
        search_frame = tk.Frame(self.gif_frame, bg="#1e1f22", bd=1, relief="solid")
        search_frame.pack(fill="x", padx=10, pady=5)
        
        self.search_var = tk.StringVar()
        entry = tk.Entry(search_frame, textvariable=self.search_var, bg="#1e1f22", fg="#dbdee1", insertbackground="#dbdee1", relief="flat", font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        entry.bind("<Return>", lambda e: self.search_gifs())
        
        btn = tk.Button(search_frame, text="🔍", bg="#1e1f22", fg="#dbdee1", relief="flat", command=self.search_gifs, cursor="hand2", bd=0)
        btn.pack(side="right", padx=5)
        
        self.gif_canvas = tk.Canvas(self.gif_frame, bg="#2b2d31", highlightthickness=0)
        self.gif_scrollbar = ttk.Scrollbar(self.gif_frame, orient="vertical", command=self.gif_canvas.yview)
        self.gif_scrollable_frame = tk.Frame(self.gif_canvas, bg="#2b2d31")
        
        self.gif_scrollable_frame.bind("<Configure>", lambda e: self.gif_canvas.configure(scrollregion=self.gif_canvas.bbox("all")))
        self.gif_canvas.create_window((0, 0), window=self.gif_scrollable_frame, anchor="nw")
        self.gif_canvas.configure(yscrollcommand=self.gif_scrollbar.set)
        
        self.gif_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.gif_scrollbar.pack(side="right", fill="y")
        
        self.loading_label = tk.Label(self.gif_scrollable_frame, text="Pesquise por GIFs...", bg="#2b2d31", fg="#b5bac1", font=("Segoe UI", 10))
        self.loading_label.pack(pady=20)

    def search_gifs(self):
        query = self.search_var.get().strip()
        if not query:
            return
        
        for widget in self.gif_scrollable_frame.winfo_children():
            widget.destroy()
            
        self.loading_label = tk.Label(self.gif_scrollable_frame, text="Carregando...", bg="#2b2d31", fg="#b5bac1", font=("Segoe UI", 10))
        self.loading_label.pack(pady=20)
        self.gif_images = []
        
        def worker():
            try:
                import urllib.request, urllib.parse, json
                url = f"https://g.tenor.com/v1/search?q={urllib.parse.quote(query)}&key=LIVDSRZULELA&limit=16"
                req = urllib.request.Request(url, headers={"User-Agent": "GG Coalition/1.0"})
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read())
                
                results = []
                for item in data.get("results", []):
                    preview_url = item["media"][0]["tinygif"]["url"]
                    full_url = item["media"][0]["gif"]["url"]
                    results.append((preview_url, full_url))
                
                self.panel.after(0, self.display_gifs, results)
            except Exception as e:
                self.panel.after(0, self.display_error, str(e))
                
        threading.Thread(target=worker, daemon=True).start()

    def display_error(self, msg):
        for widget in self.gif_scrollable_frame.winfo_children():
            widget.destroy()
        tk.Label(self.gif_scrollable_frame, text=f"Erro: {msg}", bg="#2b2d31", fg="#fca5a5", wraplength=300).pack(pady=20)

    def display_gifs(self, results):
        for widget in self.gif_scrollable_frame.winfo_children():
            widget.destroy()
        if not results:
            tk.Label(self.gif_scrollable_frame, text="Nenhum GIF encontrado.", bg="#2b2d31", fg="#b5bac1").pack(pady=20)
            return
            
        row, col = 0, 0
        for preview_url, full_url in results:
            frame = tk.Frame(self.gif_scrollable_frame, bg="#2b2d31")
            frame.grid(row=row, column=col, padx=4, pady=4)
            
            lbl = tk.Label(frame, text="Carregando...", bg="#1e1f22", fg="#80848e", width=18, height=6)
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, url=full_url: self.insert_gif(url))
            
            self.load_gif_preview(preview_url, lbl)
            
            col += 1
            if col > 1:
                col = 0
                row += 1

    def load_gif_preview(self, url, label):
        def worker():
            try:
                import urllib.request, io
                req = urllib.request.Request(url, headers={"User-Agent": "GG Coalition/1.0"})
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = response.read()
                image = Image.open(io.BytesIO(data))
                image = image.convert("RGBA")
                image.thumbnail((140, 100), Image.Resampling.LANCZOS)
                self.panel.after(0, self.apply_gif_preview, image, label)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def apply_gif_preview(self, image, label):
        try:
            photo = ImageTk.PhotoImage(image)
            self.gif_images.append(photo)
            label.configure(image=photo, text="", width=140, height=100)
            label.image = photo
        except Exception:
            pass

    def insert_emoji(self, em):
        current = self.panel.input_var.get()
        if current and not current.endswith(" "):
            self.panel.input_var.set(current + " " + em)
        else:
            self.panel.input_var.set(current + em)
        self.destroy()

    def insert_gif(self, url):
        current = self.panel.input_var.get()
        if current:
            self.panel.input_var.set(current + " " + url)
        else:
            self.panel.input_var.set(url)
        self.destroy()
