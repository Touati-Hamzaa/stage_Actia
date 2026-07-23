import traceback

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

import tksheet

from comparator import compare_results
from exporter import export_results

from jira_client import JiraClient
from mention_detector import find_mentions
from team_config import (
    ALL_NAMES,
    CURRENT_USER,
    CURRENT_USER_ALIASES,
    EMAIL_DOMAINS,
    EMAIL_TO_NAME
)

import theme

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from collections import Counter


# ============================================================
# Appearance
# ============================================================

theme.apply_base_appearance("Light")


# ============================================================
# Main Application
# ============================================================

class TestComparatorApp:

    def __init__(self):

        self.root = ctk.CTk()
        self.root.title("ACTIA Test Report Comparator")
        self.root.geometry("1700x900")
        self.root.minsize(1500, 800)
        self.root.configure(fg_color=theme.c("bg"))

        #######################################################
        # Variables
        #######################################################

        self.file1 = ""
        self.file2 = ""

        self.results = []
        self.filtered_results = []

        self.jira = JiraClient()

        #######################################################
        # Filters
        #######################################################

        self.filter_vars = {}

        comparisons = [
            "PASS → PASS",
            "PASS → FAIL",
            "FAIL → PASS",
            "FAIL → FAIL",
            "PASS → NOT TESTED",
            "FAIL → NOT TESTED",
            "NOT TESTED → PASS",
            "NOT TESTED → FAIL",
            "OTHER"
        ]

        for item in comparisons:
            self.filter_vars[item] = tk.BooleanVar(value=True)

        #######################################################
        # Search Variables
        #######################################################

        self.search_test = tk.StringVar()
        self.search_issue = tk.StringVar()

        #######################################################
        # Jira ticket cache (populated in open_jira_window)
        #######################################################

        self.jira_ticket_data = {}

        #######################################################
        # Page Container (welcome / comparator / ai placeholder)
        #######################################################

        self.container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.welcome_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.comparator_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.ai_frame = ctk.CTkFrame(self.container, fg_color="transparent")

        self.comparator_built = False

        #######################################################
        # Build Pages
        #######################################################

        self.build_welcome_page()
        self.build_ai_placeholder_page()

        # Comparator page is built lazily the first time it's opened.

        self.show_welcome()

    # ========================================================
    # Run
    # ========================================================

    def run(self):
        self.root.mainloop()

    # ============================================================
    # THEME TOGGLE
    # ============================================================

    def toggle_theme(self):

        new_mode = theme.toggle_appearance()

        self.root.configure(fg_color=theme.c("bg"))

        for btn in getattr(self, "_theme_toggle_buttons", []):
            btn.configure(text="☀️  Light" if new_mode == "Dark" else "🌙  Dark")

        # Non-CTk widgets don't auto-adapt - refresh them explicitly
        if self.comparator_built and hasattr(self, "sheet"):
            self.sheet.change_theme("dark" if new_mode == "Dark" else "light blue")
            if self.filtered_results:
                self.fill_table()

    def _register_theme_toggle(self, parent):
        """Small ☀️/🌙 button that flips light/dark mode."""

        btn = ctk.CTkButton(
            parent,
            text="🌙  Dark" if theme.current_mode() == "Light" else "☀️  Light",
            width=100,
            command=self.toggle_theme,
            **theme.ghost_button_kwargs()
        )

        if not hasattr(self, "_theme_toggle_buttons"):
            self._theme_toggle_buttons = []
        self._theme_toggle_buttons.append(btn)

        return btn

    # ============================================================
    # PAGE NAVIGATION
    # ============================================================

    def _hide_all_pages(self):
        self.welcome_frame.pack_forget()
        self.comparator_frame.pack_forget()
        self.ai_frame.pack_forget()

    def show_welcome(self):
        self._hide_all_pages()
        self.welcome_frame.pack(fill="both", expand=True)

    def show_comparator(self):

        if not self.comparator_built:
            self.build_toolbar()
            self.build_filter_panel()
            self.build_table()
            self.build_status_bar()
            self.comparator_built = True

        self._hide_all_pages()
        self.comparator_frame.pack(fill="both", expand=True)

    def show_ai_placeholder(self):
        self._hide_all_pages()
        self.ai_frame.pack(fill="both", expand=True)

    # ============================================================
    # WELCOME PAGE
    # ============================================================

    def build_welcome_page(self):

        self._register_theme_toggle(self.welcome_frame).place(
            relx=1.0, rely=0.0, anchor="ne", x=-24, y=24
        )

        wrapper = ctk.CTkFrame(self.welcome_frame, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # Small eyebrow label above the title
        ctk.CTkLabel(
            wrapper,
            text="ACTIA  •  QUALITY ENGINEERING",
            font=theme.FONTS["caption"],
            text_color=theme.c("navy"),
        ).pack(pady=(0, theme.SPACE["sm"]))

        ctk.CTkLabel(
            wrapper,
            text="Test Report Comparator",
            font=theme.FONTS["hero"],
            text_color=theme.c("text_primary"),
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            wrapper,
            text="Choose what you'd like to do",
            font=theme.FONTS["subtitle"],
            text_color=theme.c("text_secondary"),
        ).pack(pady=(0, theme.SPACE["xl"]))

        btn_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        btn_frame.pack()

        self._nav_card(
            btn_frame,
            title="Compare Test Reports",
            subtitle="Diff two Excel reports, filter results,\nsync with Jira",
            icon="📊",
            command=self.show_comparator,
            primary=True,
        ).pack(side="left", padx=theme.SPACE["md"])

        self._nav_card(
            btn_frame,
            title="AI Tools",
            subtitle="Coming soon",
            icon="🤖",
            command=self.show_ai_placeholder,
            primary=False,
        ).pack(side="left", padx=theme.SPACE["md"])

    def _nav_card(self, parent, title, subtitle, icon, command, primary):
        """A large clickable card used on the welcome page."""

        card = ctk.CTkButton(
            parent,
            text="",
            width=300,
            height=160,
            command=command,
            corner_radius=theme.RADIUS["lg"],
            fg_color=theme.c("navy") if primary else theme.c("surface"),
            hover_color=theme.c("navy_hover") if primary else theme.c("surface_alt"),
            border_width=0 if primary else 1,
            border_color=theme.c("border"),
        )

        # Overlay real content on top of the button using place(),
        # since CTkButton's own layout can't do icon+title+subtitle.
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        text_color = "#FFFFFF" if primary else theme.c("text_primary")
        sub_color = ("#DCE6F0", "#DCE6F0") if primary else theme.c("text_secondary")

        ctk.CTkLabel(inner, text=icon, font=(theme.FONT, 30)).pack()
        ctk.CTkLabel(
            inner, text=title, font=theme.FONTS["section"], text_color=text_color
        ).pack(pady=(8, 4))
        ctk.CTkLabel(
            inner, text=subtitle, font=theme.FONTS["caption"], text_color=sub_color,
            justify="center"
        ).pack()

        return card

    # ============================================================
    # AI PLACEHOLDER PAGE
    # ============================================================

    def build_ai_placeholder_page(self):

        top = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
        top.pack(fill="x", padx=theme.SPACE["lg"], pady=theme.SPACE["lg"])

        ctk.CTkButton(
            top, text="←  Back", width=100, command=self.show_welcome,
            **theme.ghost_button_kwargs()
        ).pack(side="left")

        self._register_theme_toggle(top).pack(side="right")

        wrapper = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(wrapper, text="🤖", font=(theme.FONT, 40)).pack(pady=(0, 10))

        ctk.CTkLabel(
            wrapper, text="AI Tools", font=theme.FONTS["title"],
            text_color=theme.c("text_primary")
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            wrapper, text="Coming soon.", font=theme.FONTS["subtitle"],
            text_color=theme.c("text_secondary")
        ).pack()

    # ============================================================
    # Toolbar
    # ============================================================

    def build_toolbar(self):

        outer = ctk.CTkFrame(self.comparator_frame, fg_color="transparent")
        outer.pack(fill="x", padx=theme.SPACE["lg"], pady=(theme.SPACE["lg"], theme.SPACE["sm"]))

        # ---- Title row ----
        title_row = ctk.CTkFrame(outer, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, theme.SPACE["md"]))

        ctk.CTkButton(
            title_row, text="←  Back", width=90, command=self.show_welcome,
            **theme.ghost_button_kwargs()
        ).pack(side="left")

        ctk.CTkLabel(
            title_row, text="Compare Test Reports", font=theme.FONTS["title"],
            text_color=theme.c("text_primary")
        ).pack(side="left", padx=(theme.SPACE["md"], 0))

        self._register_theme_toggle(title_row).pack(side="right")

        # ---- Toolbar card ----
        self.toolbar = ctk.CTkFrame(outer, **theme.card_kwargs())
        self.toolbar.pack(fill="x", ipady=theme.SPACE["sm"])

        pad = dict(padx=(theme.SPACE["md"], 0), pady=theme.SPACE["md"])

        self.btn_file1 = ctk.CTkButton(
            self.toolbar, text="📂 Open File 1", width=150,
            command=self.browse_file1, **theme.secondary_button_kwargs()
        )
        self.btn_file1.pack(side="left", **pad)

        self.file1_label = ctk.CTkLabel(
            self.toolbar, text="No file selected", width=220, anchor="w",
            font=theme.FONTS["caption"], text_color=theme.c("text_secondary")
        )
        self.file1_label.pack(side="left", padx=(theme.SPACE["sm"], theme.SPACE["md"]))

        self.btn_file2 = ctk.CTkButton(
            self.toolbar, text="📂 Open File 2", width=150,
            command=self.browse_file2, **theme.secondary_button_kwargs()
        )
        self.btn_file2.pack(side="left", **pad)

        self.file2_label = ctk.CTkLabel(
            self.toolbar, text="No file selected", width=220, anchor="w",
            font=theme.FONTS["caption"], text_color=theme.c("text_secondary")
        )
        self.file2_label.pack(side="left", padx=(theme.SPACE["sm"], theme.SPACE["md"]))

        self.compare_button = ctk.CTkButton(
            self.toolbar, text="🔄  Compare", width=140,
            command=self.compare, **theme.primary_button_kwargs()
        )
        self.compare_button.pack(side="left", **pad)

        # Divider
        ctk.CTkFrame(self.toolbar, width=1, fg_color=theme.c("border")).pack(
            side="left", fill="y", padx=theme.SPACE["md"], pady=theme.SPACE["sm"]
        )

        self.stats_button = ctk.CTkButton(
            self.toolbar, text="📊 Statistics", width=130,
            command=self.open_statistics_window, **theme.secondary_button_kwargs()
        )
        self.stats_button.pack(side="left", **pad)

        self.jira_button = ctk.CTkButton(
            self.toolbar, text="🎫 Jira", width=110,
            command=self.open_jira_window, **theme.secondary_button_kwargs()
        )
        self.jira_button.pack(side="left", **pad)

        self.export_button = ctk.CTkButton(
            self.toolbar, text="📤 Export Excel", width=150,
            command=self.export_excel, **theme.secondary_button_kwargs()
        )
        self.export_button.pack(side="left", **pad)

        self.pdf_button = ctk.CTkButton(
            self.toolbar, text="📄 Export PDF", width=140,
            command=self.export_pdf, **theme.secondary_button_kwargs()
        )
        self.pdf_button.pack(side="left", padx=(theme.SPACE["md"], theme.SPACE["md"]), pady=theme.SPACE["md"])

    # ============================================================
    # Browse File 1 / File 2
    # ============================================================

    def browse_file1(self):

        filename = filedialog.askopenfilename(
            title="Select First Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )

        if filename:
            self.file1 = filename
            short_name = filename.split("/")[-1].split("\\")[-1]
            self.file1_label.configure(text=short_name, text_color=theme.c("text_primary"))

    def browse_file2(self):

        filename = filedialog.askopenfilename(
            title="Select Second Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )

        if filename:
            self.file2 = filename
            short_name = filename.split("/")[-1].split("\\")[-1]
            self.file2_label.configure(text=short_name, text_color=theme.c("text_primary"))

    # ============================================================
    # FILTER PANEL
    # ============================================================

    def build_filter_panel(self):

        outer = ctk.CTkFrame(self.comparator_frame, fg_color="transparent")
        outer.pack(fill="x", padx=theme.SPACE["lg"], pady=(0, theme.SPACE["sm"]))

        self.filter_frame = ctk.CTkFrame(outer, **theme.card_kwargs())
        self.filter_frame.pack(fill="x")

        ctk.CTkLabel(
            self.filter_frame, text="Filter results", font=theme.FONTS["section"],
            text_color=theme.c("text_primary")
        ).pack(anchor="w", padx=theme.SPACE["md"], pady=(theme.SPACE["md"], theme.SPACE["xs"]))

        row1 = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        row1.pack(fill="x", padx=theme.SPACE["md"], pady=(0, theme.SPACE["xs"]))

        comparisons1 = ["PASS → PASS", "PASS → FAIL", "FAIL → PASS", "FAIL → FAIL"]

        for text in comparisons1:
            ctk.CTkCheckBox(
                row1, text=text, variable=self.filter_vars[text],
                command=self.apply_filters, font=theme.FONTS["body"],
                text_color=theme.c("text_primary"),
                fg_color=theme.c("navy"), hover_color=theme.c("navy_hover"),
            ).pack(side="left", padx=(0, theme.SPACE["lg"]))

        row2 = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        row2.pack(fill="x", padx=theme.SPACE["md"], pady=(0, theme.SPACE["sm"]))

        comparisons2 = [
            "PASS → NOT TESTED", "FAIL → NOT TESTED",
            "NOT TESTED → PASS", "NOT TESTED → FAIL", "OTHER"
        ]

        for text in comparisons2:
            ctk.CTkCheckBox(
                row2, text=text, variable=self.filter_vars[text],
                command=self.apply_filters, font=theme.FONTS["body"],
                text_color=theme.c("text_primary"),
                fg_color=theme.c("navy"), hover_color=theme.c("navy_hover"),
            ).pack(side="left", padx=(0, theme.SPACE["lg"]))

        # Divider
        ctk.CTkFrame(self.filter_frame, height=1, fg_color=theme.c("border")).pack(
            fill="x", padx=theme.SPACE["md"], pady=theme.SPACE["sm"]
        )

        search = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        search.pack(fill="x", padx=theme.SPACE["md"], pady=(0, theme.SPACE["md"]))

        ctk.CTkLabel(
            search, text="Test ID", font=theme.FONTS["caption"],
            text_color=theme.c("text_secondary")
        ).pack(side="left", padx=(0, theme.SPACE["xs"]))

        self.entry_test = ctk.CTkEntry(
            search, width=200, textvariable=self.search_test,
            corner_radius=theme.RADIUS["sm"], border_color=theme.c("border"),
            fg_color=theme.c("surface_alt"), text_color=theme.c("text_primary"),
        )
        self.entry_test.pack(side="left", padx=(0, theme.SPACE["lg"]))
        self.entry_test.bind("<KeyRelease>", lambda e: self.apply_filters())

        ctk.CTkLabel(
            search, text="Issue ID", font=theme.FONTS["caption"],
            text_color=theme.c("text_secondary")
        ).pack(side="left", padx=(0, theme.SPACE["xs"]))

        self.entry_issue = ctk.CTkEntry(
            search, width=200, textvariable=self.search_issue,
            corner_radius=theme.RADIUS["sm"], border_color=theme.c("border"),
            fg_color=theme.c("surface_alt"), text_color=theme.c("text_primary"),
        )
        self.entry_issue.pack(side="left", padx=(0, theme.SPACE["lg"]))
        self.entry_issue.bind("<KeyRelease>", lambda e: self.apply_filters())

        ctk.CTkButton(
            search, text="Refresh", width=90, command=self.apply_filters,
            **theme.secondary_button_kwargs()
        ).pack(side="right")

    # ============================================================
    # APPLY FILTERS
    # ============================================================

    def apply_filters(self):

        if not self.results:
            return

        test_search = self.search_test.get().upper().strip()
        issue_search = self.search_issue.get().upper().strip()

        self.filtered_results = []

        for row in self.results:

            comparison = row.get("Comparison", "OTHER")

            if comparison not in self.filter_vars:
                comparison = "OTHER"

            if not self.filter_vars[comparison].get():
                continue

            test_id = str(row.get("Test ID") or "")

            if test_search and test_search not in test_id.upper():
                continue

            issue = row.get("Issue 2")
            if not issue:
                issue = row.get("Issue")
            issue = (issue or "").upper()

            if issue_search and issue_search not in issue:
                continue

            self.filtered_results.append(row)

        self.fill_table()

    # ============================================================
    # TABLE
    # ============================================================

    def build_table(self):

        outer = ctk.CTkFrame(self.comparator_frame, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=theme.SPACE["lg"], pady=(0, theme.SPACE["sm"]))

        self.table_frame = ctk.CTkFrame(outer, **theme.card_kwargs())
        self.table_frame.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=theme.SPACE["sm"], pady=theme.SPACE["sm"])

        headers = ["Test ID", "Result 1", "Issue 1", "Result 2", "Issue 2", "Jira Status"]

        self.sheet = tksheet.Sheet(
            inner,
            headers=headers,
            height=620,
            width=1600,
            theme="light blue" if theme.current_mode() == "Light" else "dark",
        )

        self.sheet.enable_bindings((
            "single_select", "row_select", "column_select", "arrowkeys",
            "copy", "paste", "delete", "undo", "edit_cell",
            "right_click_popup_menu", "column_width_resize",
            "double_click_column_resize", "row_height_resize", "select_all"
        ))

        self.sheet.pack(fill="both", expand=True)

    # ============================================================
    # FILL TABLE
    # ============================================================

    def fill_table(self):

        data = []

        for row in self.filtered_results:
            data.append([
                row.get("Test ID", ""),
                row.get("Result 1", ""),
                row.get("Issue 1", ""),
                row.get("Result 2", ""),
                row.get("Issue 2", ""),
                row.get("Jira Status", "")
            ])

        self.sheet.set_sheet_data(data)

        #########################################################
        # Colors - derived from the design system, mode-aware
        #########################################################

        neutral = theme.cx("neutral_bg")
        pass_c = theme.cx("success_bg")
        fail_c = theme.cx("danger_bg")
        not_tested_c = theme.cx("warning_bg")
        info_c = theme.cx("info_bg")

        for r, row in enumerate(self.filtered_results):

            value = str(row.get("Result 1") or "").upper()
            color = neutral
            if value == "PASS":
                color = pass_c
            elif value == "FAIL":
                color = fail_c
            elif value == "NOT TESTED":
                color = not_tested_c
            self.sheet.highlight_cells(row=r, column=1, bg=color)

            value = str(row.get("Result 2") or "").upper()
            color = neutral
            if value == "PASS":
                color = pass_c
            elif value == "FAIL":
                color = fail_c
            elif value == "NOT TESTED":
                color = not_tested_c
            self.sheet.highlight_cells(row=r, column=3, bg=color)

            status = str(row.get("Jira Status") or "").upper()
            color = neutral
            if status == "DONE":
                color = pass_c
            elif status == "IN PROGRESS":
                color = info_c
            elif status == "TO DO":
                color = not_tested_c
            elif status == "BLOCKED":
                color = fail_c
            self.sheet.highlight_cells(row=r, column=5, bg=color)

        self.sheet.set_all_column_widths(180)

    # ============================================================
    # COMPARE FILES
    # ============================================================

    def compare(self):

        if not self.file1:
            messagebox.showwarning("Warning", "Please select the first Excel file.")
            return

        if not self.file2:
            messagebox.showwarning("Warning", "Please select the second Excel file.")
            return

        try:

            self.status_label.configure(text="Comparing reports...")
            self.root.update()

            self.results = compare_results(self.file1, self.file2)

            try:
                jira_connected = self.jira.test_connection()
            except Exception:
                jira_connected = False

            for row in self.results:

                if jira_connected:
                    issue = (row.get("Issue 2") or "").strip()
                    if issue:
                        row["Jira Status"] = self.jira.get_ticket_status(issue)
                    else:
                        row["Jira Status"] = "No Ticket"
                else:
                    row["Jira Status"] = "Disconnected"

            self.filtered_results = self.results.copy()
            self.apply_filters()

            self.status_label.configure(text=f"{len(self.results)} comparisons loaded.")

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(
                "Comparison Error",
                f"{e}\n\n(Full details printed in the terminal/console.)"
            )
            self.status_label.configure(text="Error during comparison.")

    # ============================================================
    # EXPORT EXCEL
    # ============================================================

    def export_excel(self):

        if not self.filtered_results:
            messagebox.showwarning("Warning", "Nothing to export.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel File", "*.xlsx")],
            title="Save Comparison Report"
        )

        if filename == "":
            return

        try:
            export_results(filename, self.filtered_results)
            messagebox.showinfo("Export", "Excel report exported successfully.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ============================================================
    # EXPORT PDF
    # ============================================================

    def export_pdf(self):
        messagebox.showinfo("PDF", "PDF export will be added in a future update.")

    # ============================================================
    # STATUS BAR
    # ============================================================

    def build_status_bar(self):

        outer = ctk.CTkFrame(self.comparator_frame, fg_color="transparent")
        outer.pack(fill="x", padx=theme.SPACE["lg"], pady=(0, theme.SPACE["lg"]))

        self.status_frame = ctk.CTkFrame(outer, **theme.card_kwargs())
        self.status_frame.pack(fill="x")

        self.status_label = ctk.CTkLabel(
            self.status_frame, text="Ready", anchor="w",
            font=theme.FONTS["caption"], text_color=theme.c("text_secondary")
        )
        self.status_label.pack(side="left", padx=theme.SPACE["md"], pady=theme.SPACE["sm"])

    # ============================================================
    # STATISTICS
    # ============================================================

    def open_statistics_window(self):

        if not self.results:
            messagebox.showwarning("Statistics", "Please compare two reports first.")
            return

        stats = ctk.CTkToplevel(self.root, fg_color=theme.c("bg"))
        stats.title("Statistics Dashboard")
        stats.geometry("1400x800")

        counter = Counter()

        for row in self.results:
            counter[row.get("Comparison", "OTHER")] += 1

        total = len(self.results)

        ##########################################################
        # KPI Cards
        ##########################################################

        card_frame = ctk.CTkFrame(stats, fg_color="transparent")
        card_frame.pack(fill="x", padx=theme.SPACE["lg"], pady=theme.SPACE["lg"])

        cards = [
            ("Total", total, theme.c("navy"), theme.c("navy")),
            ("PASS → PASS", counter["PASS → PASS"], theme.c("success"), theme.c("success_bg")),
            ("PASS → FAIL", counter["PASS → FAIL"], theme.c("danger"), theme.c("danger_bg")),
            ("FAIL → PASS", counter["FAIL → PASS"], theme.c("success"), theme.c("success_bg")),
            ("FAIL → FAIL", counter["FAIL → FAIL"], theme.c("danger"), theme.c("danger_bg")),
        ]

        for i, (title, value, accent, bg) in enumerate(cards):

            is_total = (i == 0)

            card = ctk.CTkFrame(
                card_frame,
                fg_color=accent if is_total else bg,
                corner_radius=theme.RADIUS["lg"],
                border_width=0 if is_total else 1,
                border_color=theme.c("border"),
            )
            card.pack(side="left", expand=True, fill="both", padx=theme.SPACE["xs"])

            title_color = "#FFFFFF" if is_total else accent
            value_color = "#FFFFFF" if is_total else accent

            ctk.CTkLabel(
                card, text=title, font=theme.FONTS["caption"], text_color=title_color
            ).pack(pady=(theme.SPACE["lg"], theme.SPACE["xs"]))

            ctk.CTkLabel(
                card, text=str(value), font=(theme.FONT, 30, "bold"), text_color=value_color
            ).pack(pady=(0, theme.SPACE["lg"]))

        ##########################################################
        # Charts Frame
        ##########################################################

        charts_outer = ctk.CTkFrame(stats, fg_color="transparent")
        charts_outer.pack(fill="both", expand=True, padx=theme.SPACE["lg"], pady=(0, theme.SPACE["lg"]))

        charts = ctk.CTkFrame(charts_outer, **theme.card_kwargs())
        charts.pack(fill="both", expand=True)

        face = theme.cx("surface")
        text_c = theme.cx("text_primary")
        grid_c = theme.cx("border")

        palette = [
            theme.cx("navy"), theme.cx("success"), theme.cx("danger"),
            theme.cx("warning"), theme.cx("info"), theme.cx("slate"),
            theme.cx("navy_hover"), theme.cx("text_secondary"), theme.cx("text_muted"),
        ]

        fig1 = Figure(figsize=(6, 5), dpi=100)
        fig1.patch.set_facecolor(face)
        ax1 = fig1.add_subplot(111)
        ax1.set_facecolor(face)

        labels = []
        values = []

        for key, value in counter.items():
            if value > 0:
                labels.append(key)
                values.append(value)

        if values:
            wedges, texts, autotexts = ax1.pie(
                values,
                labels=[f"{l}\n({v})" for l, v in zip(labels, values)],
                autopct=lambda p: f"{p:.1f}%",
                startangle=90,
                colors=palette[:len(values)],
                textprops={"color": text_c, "fontsize": 9},
            )
            for at in autotexts:
                at.set_color("#FFFFFF")

        ax1.set_title("Comparison Distribution", color=text_c, fontsize=13, fontweight="bold")

        canvas1 = FigureCanvasTkAgg(fig1, master=charts)
        canvas1.draw()
        canvas1.get_tk_widget().pack(side="left", fill="both", expand=True, padx=theme.SPACE["md"], pady=theme.SPACE["md"])

        ##########################################################
        # Bar Chart
        ##########################################################

        fig2 = Figure(figsize=(7, 5), dpi=100)
        fig2.patch.set_facecolor(face)
        ax2 = fig2.add_subplot(111)
        ax2.set_facecolor(face)

        if values:
            bars = ax2.bar(labels, values, color=palette[:len(values)])

            for bar in bars:
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2, height, str(int(height)),
                    ha="center", fontsize=10, fontweight="bold", color=text_c
                )

        ax2.set_ylabel("Number of Tests", color=text_c)
        ax2.set_title("Comparison Statistics", color=text_c, fontsize=13, fontweight="bold")
        ax2.tick_params(axis="x", rotation=30, colors=text_c)
        ax2.tick_params(axis="y", colors=text_c)
        for spine in ax2.spines.values():
            spine.set_color(grid_c)
        ax2.grid(axis="y", color=grid_c, linewidth=0.5, alpha=0.5)

        canvas2 = FigureCanvasTkAgg(fig2, master=charts)
        canvas2.draw()
        canvas2.get_tk_widget().pack(side="right", fill="both", expand=True, padx=theme.SPACE["md"], pady=theme.SPACE["md"])

    # ============================================================
    # JIRA WINDOW
    # ============================================================

    def open_jira_window(self):

        if not self.results:
            messagebox.showwarning("Jira", "Compare two reports first.")
            return

        if not self.jira.test_connection():
            messagebox.showerror("Jira", "Cannot connect to Jira.\nCheck jira_config.py")
            return

        window = ctk.CTkToplevel(self.root, fg_color=theme.c("bg"))
        window.title("Jira Dashboard")
        window.geometry("1300x750")

        self.jira_ticket_data = {}

        ########################################################
        # Connection
        ########################################################

        top = ctk.CTkFrame(window, **theme.card_kwargs())
        top.pack(fill="x", padx=theme.SPACE["lg"], pady=theme.SPACE["lg"], ipady=theme.SPACE["xs"])

        header_row = ctk.CTkFrame(top, fg_color="transparent")
        header_row.pack(fill="x", padx=theme.SPACE["md"], pady=(theme.SPACE["md"], theme.SPACE["xs"]))

        ctk.CTkLabel(
            header_row, text="Jira Connection", font=theme.FONTS["section"],
            text_color=theme.c("text_primary")
        ).pack(side="left")

        ctk.CTkLabel(
            header_row, text="●  Connected", text_color=theme.c("success"),
            font=theme.FONTS["body_bold"],
        ).pack(side="right")

        import ner_detector as _ner_check
        detection_mode = "NER + regex" if _ner_check.is_available() else "regex only"

        self.jira_scan_status = ctk.CTkLabel(
            top,
            text=f"Watching for mentions of: {CURRENT_USER}  •  detection: {detection_mode}",
            font=theme.FONTS["caption"],
            text_color=theme.c("text_secondary")
        )
        self.jira_scan_status.pack(anchor="w", padx=theme.SPACE["md"], pady=(0, theme.SPACE["md"]))

        ########################################################
        # Middle
        ########################################################

        middle = ctk.CTkFrame(window, fg_color="transparent")
        middle.pack(fill="both", expand=True, padx=theme.SPACE["lg"], pady=(0, theme.SPACE["lg"]))

        ########################################################
        # Ticket List (left)
        ########################################################

        left = ctk.CTkFrame(middle, **theme.card_kwargs())
        left.pack(side="left", fill="y", padx=(0, theme.SPACE["md"]))

        ctk.CTkLabel(
            left, text="Tickets", font=theme.FONTS["section"], text_color=theme.c("text_primary")
        ).pack(pady=(theme.SPACE["md"], theme.SPACE["xs"]))
        ctk.CTkLabel(
            left, text="🔔 = you're mentioned", font=theme.FONTS["caption"],
            text_color=theme.c("text_secondary")
        ).pack(pady=(0, theme.SPACE["sm"]))

        self.ticket_list = tk.Listbox(
            left, width=34, height=32, exportselection=False,
            bg=theme.cx("surface"), fg=theme.cx("text_primary"),
            selectbackground=theme.cx("navy"), selectforeground="#FFFFFF",
            highlightthickness=0, borderwidth=0, font=(theme.FONT, 11),
        )
        self.ticket_list.pack(fill="both", expand=True, padx=theme.SPACE["sm"], pady=(0, theme.SPACE["sm"]))
        self.ticket_list.bind("<<ListboxSelect>>", lambda e: self.show_ticket_information())

        ########################################################
        # Ticket Details (right)
        ########################################################

        right = ctk.CTkFrame(middle, **theme.card_kwargs())
        right.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            right, text="Details", font=theme.FONTS["section"], text_color=theme.c("text_primary")
        ).pack(anchor="w", padx=theme.SPACE["md"], pady=(theme.SPACE["md"], theme.SPACE["xs"]))

        self.info = ctk.CTkTextbox(
            right, wrap="word", font=theme.FONTS["mono"],
            fg_color=theme.c("surface_alt"), text_color=theme.c("text_primary"),
            corner_radius=theme.RADIUS["md"],
        )
        self.info.pack(fill="both", expand=True, padx=theme.SPACE["md"], pady=(0, theme.SPACE["md"]))
        self.info.insert("1.0", "Select a ticket on the left to see details.")
        self.info.configure(state="disabled")

        ########################################################
        # Populate + scan
        ########################################################

        issue_keys = sorted({
            (row.get("Issue 2") or "").strip()
            for row in self.results
            if (row.get("Issue 2") or "").strip()
        })

        if not issue_keys:
            self.ticket_list.insert("end", "No linked tickets found.")
            return

        for i, key in enumerate(issue_keys, start=1):

            self.jira_scan_status.configure(
                text=f"Scanning for mentions... ({i}/{len(issue_keys)})"
            )
            window.update()

            info = self.jira.get_ticket_info(key) or {}
            comments = self.jira.get_ticket_comments(key)

            combined_text = " ".join([
                info.get("Summary", ""),
                info.get("Description", ""),
                *[c["text"] for c in comments]
            ])

            mentions = find_mentions(
                combined_text,
                ALL_NAMES,
                email_domains=EMAIL_DOMAINS,
                email_to_name=EMAIL_TO_NAME
            )

            mentions_me = any(
                m["name"].lower() in [a.lower() for a in CURRENT_USER_ALIASES]
                for m in mentions
            )

            self.jira_ticket_data[key] = {
                "info": info,
                "comments": comments,
                "mentions": mentions,
                "mentions_me": mentions_me
            }

            status = info.get("Status", "Unknown")
            bell = "🔔 " if mentions_me else "    "
            self.ticket_list.insert("end", f"{bell}{key} - {status}")

            if mentions_me:
                self.ticket_list.itemconfig("end", fg=theme.cx("warning"))

        self.jira_scan_status.configure(
            text=f"Watching for mentions of: {CURRENT_USER}  •  scan complete"
        )

    # ============================================================
    # JIRA TICKET SELECTION -> DETAILS PANEL
    # ============================================================

    def show_ticket_information(self):

        selection = self.ticket_list.curselection()
        if not selection:
            return

        raw = self.ticket_list.get(selection[0])
        key = raw.replace("🔔", "").strip().split(" - ")[0].strip()

        data = self.jira_ticket_data.get(key)

        self.info.configure(state="normal")
        self.info.delete("1.0", "end")

        if not data:
            self.info.insert("1.0", "No details available for this ticket.")
            self.info.configure(state="disabled")
            return

        info = data["info"]
        mentions = data["mentions"]
        comments = data.get("comments") or []

        text = ""
        text += f"Ticket: {key}\n\n"
        text += f"Status: {info.get('Status', 'Unknown')}\n\n"
        text += f"Priority: {info.get('Priority', '')}\n\n"
        text += f"Assignee: {info.get('Assignee', 'Unassigned')}\n\n"
        text += f"Reporter: {info.get('Reporter', '')}\n\n"
        text += f"Created: {info.get('Created', '')}\n\n"
        text += f"Updated: {info.get('Updated', '')}\n\n"

        description = info.get("Description", "").strip()
        if description:
            text += f"Description:\n\n{description}\n\n"

        text += f"Summary:\n\n{info.get('Summary', '')}\n\n"

        if mentions:
            text += f"Mentions detected ({len(mentions)}):\n"
            for m in mentions:
                is_me = m["name"].lower() in [a.lower() for a in CURRENT_USER_ALIASES]
                flag = " <- YOU" if is_me else ""
                text += f"  - {m['name']} ({m['type']}): \"{m['matched_text']}\"{flag}\n"
        else:
            text += "No mentions detected in summary/description/comments.\n"

        if comments:
            text += f"\nComments ({len(comments)}):\n\n"
            for c in comments:
                text += f"[{c['author']}] {c['text']}\n\n"

        self.info.insert("1.0", text)
        self.info.configure(state="disabled")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    app = TestComparatorApp()
    app.run()
