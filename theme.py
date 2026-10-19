"""Shared UI styling for the attendance desktop app."""

import tkinter as tk
from tkinter import ttk


COLORS = {
    "primary": "#1f4f8f",
    "primary_dark": "#15395f",
    "secondary": "#7c3f58",
    "accent": "#0f766e",
    "success": "#15803d",
    "error": "#b91c1c",
    "warning": "#b45309",
    "bg_primary": "#f6f8fb",
    "bg_secondary": "#ffffff",
    "bg_tertiary": "#eef2f7",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "border": "#d8dee9",
    "text_primary": "#18212f",
    "text_secondary": "#5f6b7a",
    "text_muted": "#7b8794",
    "text_light": "#ffffff",
    "hover": "#173f73",
    "disabled": "#9aa5b1",
}


FONTS = {
    "title": ("Segoe UI", 22, "bold"),
    "subtitle": ("Segoe UI", 15, "bold"),
    "heading": ("Segoe UI", 13, "bold"),
    "subheading": ("Segoe UI", 10, "bold"),
    "normal": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "button": ("Segoe UI", 10, "bold"),
    "mono": ("Consolas", 10),
}


BUTTON_STYLES = {
    "primary": (COLORS["primary"], COLORS["hover"], COLORS["text_light"]),
    "secondary": (COLORS["secondary"], "#643146", COLORS["text_light"]),
    "success": (COLORS["success"], "#11632f", COLORS["text_light"]),
    "danger": (COLORS["error"], "#991b1b", COLORS["text_light"]),
    "warning": (COLORS["warning"], "#92400e", COLORS["text_light"]),
    "outline": (COLORS["surface"], COLORS["bg_tertiary"], COLORS["primary"]),
    "ghost": (COLORS["bg_tertiary"], COLORS["border"], COLORS["text_primary"]),
}


def _parent_bg(parent, fallback=None):
    try:
        return parent.cget("bg")
    except tk.TclError:
        return fallback or COLORS["bg_primary"]


def configure_ttk(window):
    """Apply consistent ttk styles for tables, entries, comboboxes, and buttons."""
    style = ttk.Style(window)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        ".",
        font=FONTS["normal"],
        background=COLORS["bg_primary"],
        foreground=COLORS["text_primary"],
    )
    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text_primary"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=7,
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text_primary"],
        bordercolor=COLORS["border"],
        arrowcolor=COLORS["text_secondary"],
        padding=7,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["surface"])],
        selectbackground=[("readonly", COLORS["surface"])],
        selectforeground=[("readonly", COLORS["text_primary"])],
    )
    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text_primary"],
        rowheight=30,
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["primary"])],
        foreground=[("selected", COLORS["text_light"])],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["bg_tertiary"],
        foreground=COLORS["text_primary"],
        font=FONTS["subheading"],
        relief="flat",
        padding=(8, 7),
    )
    style.map("Treeview.Heading", background=[("active", COLORS["border"])])

    for name, (bg, hover, fg) in BUTTON_STYLES.items():
        style_name = f"{name.title()}.TButton"
        style.configure(
            style_name,
            background=bg,
            foreground=fg,
            bordercolor=bg if name != "outline" else COLORS["border"],
            focusthickness=1,
            focuscolor=bg,
            padding=(14, 9),
            font=FONTS["button"],
            relief="flat",
        )
        style.map(
            style_name,
            background=[("active", hover), ("disabled", COLORS["bg_tertiary"])],
            foreground=[("disabled", COLORS["disabled"])],
        )

    return style


def configure_window(window, title="", size="500x600"):
    """Configure a top-level window with the shared application styling."""
    window.title(title)
    window.geometry(size)
    window.configure(bg=COLORS["bg_primary"])
    configure_ttk(window)
    try:
        window.minsize(420, 320)
    except tk.TclError:
        pass


def center_window(window):
    """Center a window on the current screen."""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def create_header(parent, title, subtitle="", meta_text=""):
    """Create a compact, branded header."""
    header = tk.Frame(parent, bg=COLORS["primary_dark"], height=96)
    header.pack(fill=tk.X)
    header.pack_propagate(False)

    inner = tk.Frame(header, bg=COLORS["primary_dark"])
    inner.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

    text_frame = tk.Frame(inner, bg=COLORS["primary_dark"])
    text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tk.Label(
        text_frame,
        text=title,
        font=FONTS["title"],
        bg=COLORS["primary_dark"],
        fg=COLORS["text_light"],
        anchor="w",
    ).pack(anchor="w")

    if subtitle:
        tk.Label(
            text_frame,
            text=subtitle,
            font=FONTS["small"],
            bg=COLORS["primary_dark"],
            fg="#dce6f2",
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    if meta_text:
        tk.Label(
            inner,
            text=meta_text,
            font=FONTS["subheading"],
            bg=COLORS["primary_dark"],
            fg="#dce6f2",
            anchor="e",
        ).pack(side=tk.RIGHT)

    return header


def create_button(parent, text, command=None, style="primary", width=20, icon=""):
    """Create a flat Tk button with hover states."""
    bg, hover_bg, fg = BUTTON_STYLES.get(style, BUTTON_STYLES["ghost"])
    border = COLORS["border"] if style == "outline" else bg
    button_text = f"{icon} {text}" if icon else text

    btn = tk.Button(
        parent,
        text=button_text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=hover_bg,
        activeforeground=fg,
        font=FONTS["button"],
        width=width,
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
        padx=14,
        pady=10,
        cursor="hand2",
    )

    def on_enter(_event):
        btn.configure(bg=hover_bg)

    def on_leave(_event):
        btn.configure(bg=bg)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


def create_ttk_button(parent, text, command=None, style="primary"):
    """Create a ttk button using the shared named styles."""
    return ttk.Button(
        parent,
        text=text,
        command=command,
        style=f"{style.title()}.TButton",
    )


def create_card(parent, title="", content_frame_height=None):
    """Create a bordered content panel."""
    card = tk.Frame(
        parent,
        bg=COLORS["surface"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
        bd=0,
    )

    if title:
        title_frame = tk.Frame(card, bg=COLORS["surface_alt"])
        title_frame.pack(fill=tk.X)
        tk.Label(
            title_frame,
            text=title,
            font=FONTS["heading"],
            bg=COLORS["surface_alt"],
            fg=COLORS["text_primary"],
            padx=16,
            pady=11,
            anchor="w",
        ).pack(fill=tk.X)

    content = tk.Frame(card, bg=COLORS["surface"])
    if content_frame_height:
        content.configure(height=content_frame_height)
        content.pack_propagate(False)
    content.pack(fill=tk.BOTH, expand=True)
    return card, content


def create_entry(parent, label_text="", placeholder="", width=25, is_password=False):
    """Create a labeled Entry with placeholder support."""
    parent_bg = _parent_bg(parent)
    frame = tk.Frame(parent, bg=parent_bg)

    if label_text:
        tk.Label(
            frame,
            text=label_text,
            font=FONTS["subheading"],
            bg=parent_bg,
            fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))

    border = tk.Frame(frame, bg=COLORS["border"], height=42)
    border.pack(fill=tk.X)
    border.pack_propagate(False)

    entry = tk.Entry(
        border,
        font=FONTS["normal"],
        width=width,
        bg=COLORS["surface"],
        fg=COLORS["text_primary"],
        insertbackground=COLORS["primary"],
        relief=tk.FLAT,
        borderwidth=0,
    )
    entry.pack(fill=tk.BOTH, expand=True, padx=1, pady=1, ipady=8)

    placeholder_visible = {"value": False}
    original_get = entry.get

    def set_placeholder():
        if placeholder and not original_get():
            placeholder_visible["value"] = True
            entry.configure(fg=COLORS["text_muted"], show="")
            entry.insert(0, placeholder)

    def clear_placeholder():
        if placeholder_visible["value"]:
            entry.delete(0, tk.END)
            entry.configure(fg=COLORS["text_primary"], show="*" if is_password else "")
            placeholder_visible["value"] = False

    def restore_placeholder(_event=None):
        if not original_get():
            set_placeholder()

    def focus_in(_event=None):
        border.configure(bg=COLORS["primary"])
        clear_placeholder()

    def focus_out(_event=None):
        border.configure(bg=COLORS["border"])
        restore_placeholder()

    def patched_get():
        return "" if placeholder_visible["value"] else original_get()

    entry.get = patched_get
    entry.bind("<FocusIn>", focus_in)
    entry.bind("<FocusOut>", focus_out)

    if is_password:
        entry.configure(show="*")
    set_placeholder()

    return frame, entry


def create_toggle_button(parent, text1, text2, command=None):
    """Create a segmented two-option selector."""
    container = tk.Frame(
        parent,
        bg=COLORS["surface"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )
    var = tk.StringVar(value=text1)
    buttons = []

    def refresh():
        for button, value in buttons:
            selected = var.get() == value
            button.configure(
                bg=COLORS["primary"] if selected else COLORS["surface"],
                fg=COLORS["text_light"] if selected else COLORS["text_primary"],
                activebackground=COLORS["primary"] if selected else COLORS["bg_tertiary"],
                activeforeground=COLORS["text_light"] if selected else COLORS["text_primary"],
            )
        if command:
            command()

    for value in (text1, text2):
        button = tk.Radiobutton(
            container,
            text=value,
            variable=var,
            value=value,
            indicatoron=False,
            command=refresh,
            font=FONTS["button"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=9,
            cursor="hand2",
        )
        button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        buttons.append((button, value))

    refresh()
    return container, var


def create_info_label(parent, text, fg=None, bg=None):
    bg = bg or _parent_bg(parent)
    label = tk.Label(
        parent,
        text=text,
        font=FONTS["small"],
        fg=fg or COLORS["text_secondary"],
        bg=bg,
        wraplength=520,
        justify=tk.LEFT,
        anchor="w",
    )
    return label


def create_success_label(parent, text=""):
    bg = _parent_bg(parent)
    return tk.Label(
        parent,
        text=text,
        font=FONTS["normal"],
        fg=COLORS["success"],
        bg=bg,
        anchor="w",
    )


def create_error_label(parent, text=""):
    bg = _parent_bg(parent)
    return tk.Label(
        parent,
        text=text,
        font=FONTS["normal"],
        fg=COLORS["error"],
        bg=bg,
        anchor="w",
    )


def create_separator(parent, height=1):
    sep = tk.Frame(parent, bg=COLORS["border"], height=height)
    sep.pack(fill=tk.X, pady=14)
    return sep


def create_badge(parent, text, color="primary"):
    color_map = {
        "primary": COLORS["primary"],
        "success": COLORS["success"],
        "error": COLORS["error"],
        "warning": COLORS["warning"],
        "secondary": COLORS["secondary"],
    }
    return tk.Label(
        parent,
        text=text,
        font=FONTS["small"],
        bg=color_map.get(color, COLORS["primary"]),
        fg=COLORS["text_light"],
        padx=10,
        pady=4,
    )


def create_status_strip(parent, text, tone="primary"):
    """Create a compact full-width status panel."""
    tones = {
        "primary": ("#eaf2ff", COLORS["primary"]),
        "success": ("#eaf7ef", COLORS["success"]),
        "warning": ("#fff5df", COLORS["warning"]),
        "error": ("#fdecec", COLORS["error"]),
    }
    bg, fg = tones.get(tone, tones["primary"])
    frame = tk.Frame(parent, bg=bg, padx=12, pady=10)
    tk.Label(
        frame,
        text=text,
        bg=bg,
        fg=fg,
        font=FONTS["small"],
        justify=tk.LEFT,
        anchor="w",
    ).pack(fill=tk.X)
    return frame


def apply_rounded_corner_effect(frame, bg_color=None):
    """Compatibility helper retained for older modules."""
    frame.configure(bg=bg_color or COLORS["surface"], padx=5, pady=5)
