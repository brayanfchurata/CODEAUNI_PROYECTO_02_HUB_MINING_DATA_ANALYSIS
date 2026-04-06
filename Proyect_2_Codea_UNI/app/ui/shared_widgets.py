import customtkinter as ctk
from tkinter import ttk
from app.ui.styles import PALETTE


def make_title(parent, text):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=PALETTE["text"],
    )


def make_subtitle(parent, text):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=12),
        text_color=PALETTE["muted"],
    )


def make_button(parent, text, command, width=150):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        fg_color=PALETTE["primary"],
        hover_color=PALETTE["primary_hover"],
        corner_radius=12,
    )


def make_card(parent):
    return ctk.CTkFrame(
        parent,
        corner_radius=16,
        fg_color=PALETTE["panel"],
        border_width=1,
        border_color=PALETTE["border"],
    )


def configure_treeview_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "Treeview",
        background="#111827",
        foreground="#f8fafc",
        fieldbackground="#111827",
        rowheight=28,
    )
    style.configure(
        "Treeview.Heading",
        background="#1f2937",
        foreground="#f8fafc",
        font=("Segoe UI", 10, "bold"),
    )