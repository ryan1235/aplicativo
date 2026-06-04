import tkinter as tk

def make_window_frameless(window: tk.Toplevel):
    window.overrideredirect(True)
    
    def start_move(event):
        # Ignorar cliques em widgets específicos, como Text e Entry
        if isinstance(event.widget, (tk.Text, tk.Entry)):
            window._drag_active = False
            return
            
        window._drag_active = True
        window._drag_x = event.x
        window._drag_y = event.y

    def stop_move(event):
        window._drag_active = False
        window._drag_x = None
        window._drag_y = None

    def do_move(event):
        if getattr(window, '_drag_active', False) and getattr(window, '_drag_x', None) is not None and getattr(window, '_drag_y', None) is not None:
            deltax = event.x - window._drag_x
            deltay = event.y - window._drag_y
            x = window.winfo_x() + deltax
            y = window.winfo_y() + deltay
            window.geometry(f"+{x}+{y}")

    # Configura a janela para ter fundo transparente nas bordas
    transparent_color = "#000001"
    try:
        # Para Tkinter padrão
        window.configure(bg=transparent_color)
        if hasattr(window, "config"):
            window.config(background=transparent_color)
        # Para CustomTkinter (evita o erro list -> string)
        if hasattr(window, "configure"):
            try:
                window.configure(fg_color=transparent_color)
            except Exception:
                pass
        window.attributes("-transparentcolor", transparent_color)
    except Exception:
        pass

    window.bind("<ButtonPress-1>", start_move)
    window.bind("<ButtonRelease-1>", stop_move)
    window.bind("<B1-Motion>", do_move)

    close_btn = tk.Button(
        window,
        text="✕",
        command=window.destroy,
        bg="#111c31",          # Mesma cor do 'card'
        fg="#99abc4",          # Cor 'muted' para não chamar tanta atenção
        activebackground="#111c31", # Mantém a cor de fundo sem bloco sólido ao clicar
        activeforeground="#ff7a90", # Fica avermelhado suave ao clicar (danger)
        relief="flat",
        bd=0,
        highlightthickness=0,
        font=("Segoe UI", 12, "bold"),
        cursor="hand2",
    )
    # Adiciona o botão mais para dentro, alinhado com o padding (padx=16, pady=16) do painel principal
    close_btn.place(relx=1.0, x=-24, y=24, anchor="ne")
    
    # Garante que o botão fique sempre no topo das outras views
    def bring_to_front():
        try:
            close_btn.lift()
        except Exception:
            pass
    window.after(100, bring_to_front)
    window.after(500, bring_to_front)
