"""Warnings of the selected place below the nowcast, and a dialog with
their list and a detail page per warning (issue #21, docs/warnings.md).
The dialog has its own navigation view, so the detail page has a back
button and swipe back; on the phone it opens as a bottom sheet."""

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from cirro.layers.legend import swatch_class  # noqa: E402
from cirro.warnings import cap, text  # noqa: E402

SOURCE_NOTE = "Source: Deutscher Wetterdienst"


def _swatch(warning):
    """DWD's colour of the warning (data colour), next to its level in
    words."""
    if warning.colour is None:
        return Gtk.Image(
            icon_name="dialog-warning-symbolic", accessible_role=Gtk.AccessibleRole.PRESENTATION
        )
    chip = Gtk.Box(
        css_classes=[swatch_class(warning.colour)],
        valign=Gtk.Align.CENTER,
        accessible_role=Gtk.AccessibleRole.PRESENTATION,
    )
    chip.set_size_request(16, 16)
    return chip


def _label(content, classes=()):
    return Gtk.Label(label=content, xalign=0, wrap=True, css_classes=list(classes))


class WarningsButton(Gtk.Button):
    """One line under the nowcast: "⚠ 2 warnings: Frost, icy surfaces";
    hidden without warnings. Opens the dialog."""

    def __init__(self):
        super().__init__(
            css_classes=["flat", "cirro-warnings"], visible=False, tooltip_text="Show Warnings"
        )
        box = Gtk.Box(spacing=6)
        box.append(Gtk.Image(icon_name="dialog-warning-symbolic"))
        self._label = Gtk.Label(xalign=0, hexpand=True, wrap=True)
        box.append(self._label)
        box.append(Gtk.Image(icon_name="go-next-symbolic"))
        self.set_child(box)
        self._warnings = []
        self._position = None
        self.connect("clicked", self._on_clicked)

    def set_warnings(self, warnings, position):
        self._warnings = list(warnings)
        self._position = position
        line = cap.short(self._warnings)
        self._label.set_label(line)
        self.update_property([Gtk.AccessibleProperty.LABEL], [line])
        self.set_visible(bool(self._warnings))

    def _on_clicked(self, _):
        if self._warnings:
            WarningsDialog(self._warnings, self._position).present(self)


class WarningsDialog(Adw.Dialog):
    def __init__(self, warnings, position=None):
        super().__init__(title="Warnings", content_width=460, content_height=560)
        self._now = text.now()
        self._position = position
        self._nav = Adw.NavigationView()
        self._nav.add(self._list_page(warnings))
        self.set_child(self._nav)
        if len(warnings) == 1:
            self._nav.push(self._detail_page(warnings[0]))

    def _page(self, title, content):
        view = Adw.ToolbarView(content=content)
        view.add_top_bar(Adw.HeaderBar())
        return Adw.NavigationPage(title=title, child=view)

    def _list_page(self, warnings):
        rows = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        for warning in warnings:
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(warning.headline or warning.event),
                subtitle=GLib.markup_escape_text(
                    f"{text.level(warning)}\n{text.period(warning, self._now)}"
                ),
                activatable=True,
            )
            row.add_prefix(_swatch(warning))
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated", lambda _, w=warning: self._nav.push(self._detail_page(w)))
            rows.append(row)
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        box.append(rows)
        box.append(_label(SOURCE_NOTE, ["caption", "dim-label"]))
        return self._page(
            "Warnings",
            Gtk.ScrolledWindow(
                child=Adw.Clamp(child=box), hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True
            ),
        )

    def _detail_page(self, warning):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        title = Gtk.Box(spacing=8)
        title.append(_swatch(warning))
        title.append(_label(warning.headline or warning.event, ["title-3"]))
        box.append(title)
        facts = [text.level(warning), text.period(warning, self._now)]
        if self._position:
            areas = warning.areas_at(*self._position)
            limits = [text.heights(a) for a in areas]
            if limits and all(limits):
                facts.append(limits[0])
        box.append(_label("\n".join(facts), ["heading"]))
        if warning.description:
            box.append(_label(warning.description))
        if warning.instruction:
            box.append(_label(warning.instruction, ["dim-label"]))
        note = SOURCE_NOTE
        if warning.sender and warning.sender != "Deutscher Wetterdienst":
            note = f"{warning.sender}\n{note}"
        box.append(_label(note, ["caption", "dim-label"]))
        return self._page(
            warning.event.capitalize() or "Warning",
            Gtk.ScrolledWindow(
                child=Adw.Clamp(child=box), hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True
            ),
        )
