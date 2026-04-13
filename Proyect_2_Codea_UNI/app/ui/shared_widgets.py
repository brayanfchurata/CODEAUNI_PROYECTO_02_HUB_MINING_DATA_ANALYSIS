import customtkinter as ctk
from tkinter import ttk
from app.ui.styles import PALETTE


def resolve_palette(parent=None, palette=None):
    if palette is not None:
        return palette

    try:
        return parent.master.master.palette
    except Exception:
        try:
            return parent.master.palette
        except Exception:
            return PALETTE


def make_title(parent, text, palette=None, size=22):
    pal = resolve_palette(parent, palette)
    return ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=size, weight="bold"),
        text_color=pal["text"],
    )


def make_subtitle(parent, text, palette=None, size=12):
    pal = resolve_palette(parent, palette)
    return ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=size),
        text_color=pal["muted"],
    )


def make_button(parent, text, command, width=150, palette=None):
    pal = resolve_palette(parent, palette)
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=34,
        fg_color=pal["primary"],
        hover_color=pal["primary_hover"],
        text_color=pal["panel"] if pal["primary"] != pal["panel"] else pal["text"],
        corner_radius=10,
        border_width=0,
    )


def make_card(parent, palette=None, fg_key="panel", corner_radius=14, border_key="border"):
    pal = resolve_palette(parent, palette)
    return ctk.CTkFrame(
        parent,
        corner_radius=corner_radius,
        fg_color=pal.get(fg_key, pal["panel"]),
        border_width=1,
        border_color=pal.get(border_key, pal["border"]),
    )


def make_soft_panel(parent, palette=None, fg_key="card_alt", corner_radius=12):
    pal = resolve_palette(parent, palette)
    return ctk.CTkFrame(
        parent,
        corner_radius=corner_radius,
        fg_color=pal.get(fg_key, pal["card_alt"]),
        border_width=1,
        border_color=pal.get("border_soft", pal["border"]),
    )


def configure_treeview_style(palette=None):
    pal = palette or PALETTE

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "Treeview",
        background=pal.get("panel", "#111827"),
        foreground=pal.get("text", "#f8fafc"),
        fieldbackground=pal.get("panel", "#111827"),
        bordercolor=pal.get("border", "#334155"),
        rowheight=28,
        relief="flat",
        font=("Segoe UI", 9),
    )

    style.map(
        "Treeview",
        background=[("selected", pal.get("card_alt", pal.get("panel", "#1f2937")))],
        foreground=[("selected", pal.get("text", "#f8fafc"))],
    )

    style.configure(
        "Treeview.Heading",
        background=pal.get("card_alt", "#1f2937"),
        foreground=pal.get("text", "#f8fafc"),
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        borderwidth=0,
        padding=(8, 6),
    )

    style.map(
        "Treeview.Heading",
        background=[("active", pal.get("card_hover", pal.get("card_alt", "#243244")))],
        foreground=[("active", pal.get("text", "#f8fafc"))],
    )