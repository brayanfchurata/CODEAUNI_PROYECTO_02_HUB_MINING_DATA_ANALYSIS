import customtkinter as ctk

from app.ui.shared_widgets import make_title, make_subtitle, make_card
from app.core.constants import MODULE_CONFIG
from app.ui.styles import PALETTE


class HomeView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        title = make_title(self, "MineData Hub")
        title.pack(anchor="w", padx=20, pady=(20, 6))

        subtitle = make_subtitle(
            self,
            "Plataforma integrada de analitica minera con modulos de Mining, Geology, Metallurgy y Maintenance.",
        )
        subtitle.pack(anchor="w", padx=20, pady=(0, 18))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=14, pady=10)
        grid.grid_columnconfigure((0, 1), weight=1)

        modules = [m for m in MODULE_CONFIG.keys() if m != "Inicio"]
        for i, module_name in enumerate(modules):
            row = i // 2
            col = i % 2
            cfg = MODULE_CONFIG[module_name]

            card = make_card(grid)
            card.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)

            ctk.CTkLabel(
                card,
                text=f"{cfg['icon']} {module_name}",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=PALETTE["text"],
            ).pack(anchor="w", padx=16, pady=(16, 8))

            ctk.CTkLabel(
                card,
                text=cfg["description"],
                wraplength=400,
                justify="left",
                text_color=PALETTE["muted"],
            ).pack(anchor="w", padx=16, pady=(0, 16))