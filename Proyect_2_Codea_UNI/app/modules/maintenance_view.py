import customtkinter as ctk
from app.ui.shared_widgets import make_title, make_subtitle


class MaintenanceView(ctk.CTkFrame):
    def __init__(self, parent, app_state):
        super().__init__(parent, fg_color="transparent")
        make_title(self, "Maintenance Module").pack(anchor="w", padx=20, pady=(20, 6))
        make_subtitle(self, "Base lista para implementar analisis de fallas y metricas de sensores.").pack(anchor="w", padx=20)