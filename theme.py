import customtkinter as ctk


# ============================================================
# ACTIA Test Comparator - Design System
# Corporate navy / slate palette. Supports light + dark mode.
#
# Every color is a (light, dark) tuple. Pass it straight into any
# CTk widget's color parameters (fg_color, text_color, etc.) and it
# will automatically switch when ctk.set_appearance_mode() changes -
# no manual re-theming needed for CTk widgets.
#
# Non-CTk widgets (tksheet, tk.Listbox, matplotlib) don't auto-adapt
# and need their colors read explicitly - use current_mode() below.
# ============================================================

COLORS = {
    # Backgrounds
    "bg":             ("#F3F5F8", "#0F1720"),
    "surface":        ("#FFFFFF", "#182533"),
    "surface_alt":    ("#EAEEF3", "#1F2E3D"),
    "border":         ("#D6DDE6", "#2B3B4D"),

    # Text
    "text_primary":   ("#1B2733", "#E8EDF2"),
    "text_secondary": ("#5C6B7C", "#93A3B5"),
    "text_muted":     ("#8B97A6", "#5C6B7C"),

    # Primary brand accent - navy
    "navy":           ("#1E3A5F", "#4A7FB5"),
    "navy_hover":     ("#16304F", "#3A6D9E"),
    "navy_soft":      ("#E3EBF3", "#22364B"),
    "navy_soft_text": ("#1E3A5F", "#8FB4DC"),

    # Secondary accent - slate (for secondary actions)
    "slate":          ("#5C6B7C", "#3A4C5E"),
    "slate_hover":    ("#495667", "#4A5F73"),

    # Semantic status colors (desaturated, corporate-appropriate)
    "success":        ("#2E7D5B", "#4CAF7D"),
    "success_bg":     ("#E4F3EC", "#173325"),
    "danger":         ("#B3453D", "#E0796F"),
    "danger_bg":      ("#FBEAE8", "#3A1F1C"),
    "warning":        ("#966616", "#E0B84D"),
    "warning_bg":     ("#FBF1D9", "#3A2F0F"),
    "info":           ("#3B6E91", "#6FA8C9"),
    "info_bg":        ("#E4EEF4", "#1B2E3B"),
    "neutral_bg":     ("#E9EDF3", "#243547"),
}


def c(key):
    """Shorthand accessor: c('navy') -> ('#1E3A5F', '#4A7FB5')."""
    return COLORS[key]


def current_mode():
    """'Light' or 'Dark' - use this to pick a single hex for widgets
    (tksheet, tk.Listbox, matplotlib) that don't accept (light, dark)
    tuples and don't auto-update on appearance change."""
    return ctk.get_appearance_mode()


def cx(key):
    """
    Resolve a color tuple to a single hex string for the CURRENT
    appearance mode. Use for non-CTk widgets (tksheet, tk.Listbox,
    matplotlib figures) which need a plain string, not a tuple.
    """
    light, dark = COLORS[key]
    return dark if current_mode() == "Dark" else light


# ============================================================
# Typography
# ============================================================

FONT = "Segoe UI"
FONT_MONO = "Consolas"

FONTS = {
    "hero":      (FONT, 32, "bold"),
    "title":     (FONT, 20, "bold"),
    "subtitle":  (FONT, 14),
    "section":   (FONT, 15, "bold"),
    "body":      (FONT, 13),
    "body_bold": (FONT, 13, "bold"),
    "caption":   (FONT, 11),
    "button":    (FONT, 13, "bold"),
    "mono":      (FONT_MONO, 13),
}


# ============================================================
# Spacing / radius scale
# ============================================================

SPACE = {"xs": 4, "sm": 8, "md": 14, "lg": 22, "xl": 34}
RADIUS = {"sm": 6, "md": 10, "lg": 16}


# ============================================================
# Appearance mode
# ============================================================

def apply_base_appearance(mode="Light"):
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("blue")


def toggle_appearance():
    """Flip Light <-> Dark and return the new mode string."""
    new_mode = "Dark" if current_mode() == "Light" else "Light"
    ctk.set_appearance_mode(new_mode)
    return new_mode


# ============================================================
# Reusable widget helpers
# ============================================================

def primary_button_kwargs():
    """Filled navy button - the ONE primary action per screen."""
    return dict(
        fg_color=c("navy"),
        hover_color=c("navy_hover"),
        text_color=("#FFFFFF", "#FFFFFF"),
        font=FONTS["button"],
        corner_radius=RADIUS["md"],
    )


def secondary_button_kwargs():
    """Soft/outline-style button for secondary actions."""
    return dict(
        fg_color=c("surface_alt"),
        hover_color=c("border"),
        text_color=c("text_primary"),
        font=FONTS["button"],
        corner_radius=RADIUS["md"],
    )


def ghost_button_kwargs():
    """Minimal button - back links, dismiss actions."""
    return dict(
        fg_color="transparent",
        hover_color=c("surface_alt"),
        text_color=c("text_secondary"),
        font=FONTS["body_bold"],
        corner_radius=RADIUS["md"],
    )


def card_kwargs():
    """Elevated card container."""
    return dict(
        fg_color=c("surface"),
        corner_radius=RADIUS["lg"],
        border_width=1,
        border_color=c("border"),
    )
