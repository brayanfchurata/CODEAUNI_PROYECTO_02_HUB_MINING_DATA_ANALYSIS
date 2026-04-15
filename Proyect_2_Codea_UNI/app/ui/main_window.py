import customtkinter as ctk
from PIL import Image

from app.core.constants import APP_TITLE, APP_SIZE, MODULE_CONFIG, APP_ICON
from app.core.app_state import AppState
from app.ui.styles import THEMES
from app.modules.home_view import HomeView
from app.modules.mining_view import MiningView
from app.modules.geology_view import GeologyView
from app.modules.metallurgy_view import MetallurgyView
from app.modules.maintenance_view import MaintenanceView


class Proyect2CodeaUNI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.module_icons = {}
        self.nav_buttons = {}
        self.app_state = AppState()
        self.palette = THEMES[self.app_state.current_theme]

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)

        try:
            self.iconbitmap(APP_ICON)
        except Exception:
            pass

        self.geometry(APP_SIZE)
        self.configure(fg_color=self.palette["bg"])

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = None
        self.content = None
        self.current_view = None
        self.views = {}

        self.build_sidebar()
        self.build_content()
        self.show_view("Inicio")

    def load_module_icon(self, icon_path, size=(18, 18)):
        try:
            image = Image.open(icon_path)
            return ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=size
            )
        except Exception:
            return None

    def build_sidebar(self):
        if self.sidebar is not None:
            self.sidebar.destroy()

        self.nav_buttons = {}

        self.sidebar = ctk.CTkFrame(
            self,
            width=248,
            corner_radius=0,
            fg_color=self.palette["surface"],
            border_width=1,
            border_color=self.palette["border"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text=APP_TITLE,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.palette["text"],
        ).pack(anchor="w", padx=18, pady=(22, 8))

        ctk.CTkLabel(
            self.sidebar,
            text="Analítica minera integrada",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=14),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        ctk.CTkLabel(
            self.sidebar,
            text="Tema visual",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=18, pady=(6, 6))

        theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=list(THEMES.keys()),
            command=self.change_theme,
            fg_color=self.palette["panel"],
            button_color=self.palette["primary"],
            button_hover_color=self.palette["primary_hover"],
            text_color=self.palette["text"],
            font=ctk.CTkFont(size=11),
            dropdown_fg_color=self.palette["panel"],
            dropdown_text_color=self.palette["text"],
        )
        theme_menu.set(self.app_state.current_theme)
        theme_menu.pack(fill="x", padx=14, pady=(0, 14))

        # =========================
        # PERFIL / WORKSPACE
        # =========================
        profile_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["panel"],
            corner_radius=14,
            border_width=1,
            border_color=self.palette["border"],
        )
        profile_card.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkLabel(
            profile_card,
            text="Información del Proyecto",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.palette["text"],
        ).pack(anchor="w", padx=12, pady=(10, 6))

        profile_rows = [
            ("Autor", "  Brayan Churata"),
            ("Programa", "  CODEa UNI"),
            ("Rol", "  Analítica minera"),
            ("Versión", "  2.73"),
            ("Correo", "  bchurata3@mail.com"),
            ("Contacto", "  +51 927 215 240"),
        ]

        for label, value in profile_rows:
            row = ctk.CTkFrame(profile_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)

            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=58,
                anchor="w",
                text_color=self.palette["muted"],
                font=ctk.CTkFont(size=12),
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value,
                anchor="w",
                justify="left",
                wraplength=145,
                text_color=self.palette["text"],
                font=ctk.CTkFont(size=12),
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(profile_card, fg_color="transparent", height=8).pack(fill="x")

        # =========================
        # NAVEGACION
        # =========================
        ctk.CTkLabel(
            self.sidebar,
            text="Módulos",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=18, pady=(2, 6))

        for module_name, cfg in MODULE_CONFIG.items():
            icon_img = self.load_module_icon(cfg.get("icon_path"))
            self.module_icons[module_name] = icon_img

            btn_text = f"  {module_name}" if icon_img else f"{cfg.get('icon_text', '•')}  {module_name}"

            btn = ctk.CTkButton(
                self.sidebar,
                text=btn_text,
                image=icon_img,
                compound="left",
                anchor="w",
                corner_radius=12,
                fg_color=self.palette["panel"],
                hover_color=self.palette["primary_hover"],
                text_color=self.palette["text"],
                height=38,
                font=ctk.CTkFont(size=12),
                command=lambda m=module_name: self.show_view(m),
            )
            btn.pack(fill="x", padx=14, pady=5)
            self.nav_buttons[module_name] = btn

    def build_content(self):
        if self.content is None:
            self.content = ctk.CTkFrame(self, fg_color="transparent")
            self.content.grid(row=0, column=1, sticky="nsew")
            self.content.grid_rowconfigure(0, weight=1)
            self.content.grid_columnconfigure(0, weight=1)

    def update_nav_state(self):
        for module_name, btn in self.nav_buttons.items():
            if module_name == self.app_state.current_module:
                btn.configure(
                    fg_color=self.palette["primary"],
                    hover_color=self.palette["primary_hover"],
                    text_color=self.palette["panel"] if self.palette["primary"] != self.palette["panel"] else self.palette["text"],
                )
            else:
                btn.configure(
                    fg_color=self.palette["panel"],
                    hover_color=self.palette["primary_hover"],
                    text_color=self.palette["text"],
                )

    def change_theme(self, theme_name: str):
        self.app_state.set_theme(theme_name)
        self.palette = THEMES[theme_name]
        self.configure(fg_color=self.palette["bg"])

        dark_themes = {"Midnight", "Emerald", "Copper", "Slate", "Carbon", "Graphite"}
        ctk.set_appearance_mode("dark" if theme_name in dark_themes else "light")

        for view in self.views.values():
            view.destroy()

        self.views = {}
        self.current_view = None

        self.build_sidebar()
        self.show_view(self.app_state.current_module)

    def create_view(self, module_name: str):
        if module_name == "Inicio":
            return HomeView(self.content, self.app_state)
        elif module_name == "Mining":
            return MiningView(self.content, self.app_state)
        elif module_name == "Geology":
            return GeologyView(self.content, self.app_state)
        elif module_name == "Metallurgy":
            return MetallurgyView(self.content, self.app_state)
        elif module_name == "Maintenance":
            return MaintenanceView(self.content, self.app_state)
        else:
            return HomeView(self.content, self.app_state)

    def show_view(self, module_name: str):
        self.app_state.set_module(module_name)

        if module_name == "Inicio" and module_name in self.views:
            self.views[module_name].destroy()
            del self.views[module_name]

        if module_name not in self.views:
            view = self.create_view(module_name)
            self.views[module_name] = view
            view.grid(row=0, column=0, sticky="nsew")

        for name, view in self.views.items():
            if name == module_name:
                view.grid()
                view.tkraise()
            else:
                view.grid_remove()

        self.current_view = self.views[module_name]
        self.update_nav_state()