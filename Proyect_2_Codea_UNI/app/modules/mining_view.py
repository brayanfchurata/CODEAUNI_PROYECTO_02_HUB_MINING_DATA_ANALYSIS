import customtkinter as ctk
from app.ui.shared_widgets import make_title, make_subtitle


class MiningView(ctk.CTkFrame):
    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color="transparent")
        make_title(self, "Mining Module").pack(anchor="w", padx=20, pady=(20, 6))
        make_subtitle(self, "Base lista para implementar carga, KPIs y graficos de perforacion.").pack(anchor="w", padx=20)