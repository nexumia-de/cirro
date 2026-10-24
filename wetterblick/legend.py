from gi.repository import Gtk

from wetterblick.colors import ALPHA, SCALE

_CSS = "\n".join(
    f".radar-swatch-{i} {{ background-color: rgba({r}, {g}, {b}, {ALPHA / 255:.2f}); "
    "min-height: 10px; border-radius: 2px; }"
    for i, (_, (r, g, b)) in enumerate(SCALE))


def _number(value):
    return f"{value:g}"


class Legend(Gtk.Box):
    """Colour scale of the radar overlay: one swatch per class, labelled
    with its lower bound in mm/h. Fits 360 px."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                         margin_start=12, margin_end=12, margin_top=6,
                         margin_bottom=6)
        provider = Gtk.CssProvider()
        provider.load_from_string(_CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        scale = Gtk.Box(spacing=2, homogeneous=True, hexpand=True)
        for i, (bound, _) in enumerate(SCALE):
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            cell.append(Gtk.Box(css_classes=[f"radar-swatch-{i}"]))
            cell.append(Gtk.Label(label=_number(bound), xalign=0,
                                  css_classes=["caption", "numeric"]))
            scale.append(cell)
        self.append(scale)
        self.append(Gtk.Label(label="mm/h", valign=Gtk.Align.END,
                              css_classes=["caption", "dim-label"]))
        self.update_property([Gtk.AccessibleProperty.LABEL],
                             ["Rain rate legend in millimetres per hour"])
