"""Legend of a DWD base layer below the map: a colour scale with its
lower bounds, or coloured classes with names (cirro/layers/legend_data.py).
Data colours are fixed (docs/design.md allows them for data); the labels
use the theme."""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from cirro.layers.legend_data import thin  # noqa: E402

# A scale shows at most this many labels at 360 px.
LABELS = 8

_provider = None
_known = set()


def _swatch_class(color):
    """CSS class with this background colour, defined once per colour."""
    global _provider
    name = "cirro-swatch-%02x%02x%02x" % color
    if name not in _known:
        _known.add(name)
        if _provider is None:
            _provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), _provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        _provider.load_from_string("\n".join(
            ".%s { background-color: rgb(%d, %d, %d); min-height: 10px; "
            "border-radius: 2px; }"
            % (n, int(n[-6:-4], 16), int(n[-4:-2], 16), int(n[-2:], 16))
            for n in sorted(_known)))
    return name


class LayerLegend(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
                         margin_start=12, margin_end=12, margin_top=6,
                         margin_bottom=6)
        self.set_visible(False)

    def set_legend(self, legend, title=""):
        while (child := self.get_first_child()):
            self.remove(child)
        if legend is None:
            self.set_visible(False)
            return
        self.set_visible(True)
        if legend.kind == "scale":
            self._scale(legend)
        else:
            self._classes(legend)
        self.update_property([Gtk.AccessibleProperty.LABEL],
                             [f"Legend of {title}" if title else "Legend"])

    def _scale(self, legend):
        """Swatches in equal columns; each label spans the columns up to
        the next label, so long scales still fit 360 px."""
        row = Gtk.Box(spacing=6)
        grid = Gtk.Grid(column_homogeneous=True, column_spacing=2,
                        row_spacing=2, hexpand=True)
        # About 40 caption characters fit next to each other at 360 px.
        longest = max(len(e.label) for e in legend.entries)
        labels = thin(legend.entries, max(2, min(LABELS, 40 // (longest + 1))))
        for column, entry in enumerate(legend.entries):
            grid.attach(Gtk.Box(css_classes=[_swatch_class(entry.color)]),
                        column, 0, 1, 1)
        starts = [i for i, label in enumerate(labels) if label] + [len(labels)]
        share = len(labels) / max(1, len(starts) - 1)
        for start, end in zip(starts, starts[1:]):
            # A label squeezed into fewer columns would widen them all.
            if end - start < share * 0.75:
                continue
            grid.attach(Gtk.Label(label=labels[start], xalign=0,
                                  css_classes=["caption", "numeric"]),
                        start, 1, end - start, 1)
        row.append(grid)
        if legend.unit:
            row.append(Gtk.Label(label=legend.unit, valign=Gtk.Align.END,
                                 wrap=True, max_width_chars=10,
                                 css_classes=["caption", "dim-label"]))
        self.append(row)

    def _classes(self, legend):
        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                           max_children_per_line=4, min_children_per_line=2,
                           column_spacing=12, row_spacing=2,
                           homogeneous=False)
        for entry in legend.entries:
            chip = Gtk.Box(spacing=4)
            chip.append(Gtk.Box(css_classes=[_swatch_class(entry.color),
                                             "cirro-legend-chip"],
                                valign=Gtk.Align.CENTER))
            chip.append(Gtk.Label(label=entry.label, xalign=0,
                                  css_classes=["caption"]))
            flow.append(chip)
        self.append(flow)
