"""The layer picker (issue #60): one base layer (radio buttons, the
radar first) and any overlays (switches), grouped as in the catalogue.
A layer with variants is a combo row; choosing a variant also chooses
the layer. Changes apply at once; there is nothing to confirm."""
import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk  # noqa: E402

from cirro.layers import catalogue  # noqa: E402


def _subtitle(layer):
    kind = "overlay" if layer.role == catalogue.OVERLAY else ""
    return " · ".join(part for part in (layer.note, kind) if part)


class LayerPicker(Adw.Dialog):
    def __init__(self, manager):
        super().__init__(title="Map Layers", content_width=440,
                         content_height=640)
        self._manager = manager
        self._radios = {}
        self._group = None
        page = Adw.PreferencesPage()
        for name in catalogue.GROUPS:
            group = Adw.PreferencesGroup(title=name)
            if name == "Precipitation":
                group.add(self._base_row(None))
            for layer in catalogue.in_group(name):
                group.add(self._base_row(layer) if layer.role == catalogue.BASE
                          else self._overlay_row(layer))
            page.add(group)
        view = Adw.ToolbarView(content=page)
        view.add_top_bar(Adw.HeaderBar())
        self.set_child(view)

    # Base layers

    def _base_row(self, layer):
        layer_id = layer.id if layer else catalogue.RADAR
        current = self._manager.base_id == layer_id
        radio = Gtk.CheckButton(active=current, valign=Gtk.Align.CENTER,
                                group=self._group)
        self._group = self._group or radio
        self._radios[layer_id] = radio
        if layer is None:
            row = Adw.ActionRow(title="Rain Radar",
                                subtitle="Measured and forecast to +2 h, Germany",
                                activatable_widget=radio)
        elif layer.variants:
            row = Adw.ComboRow(title=layer.title, subtitle=_subtitle(layer),
                               model=Gtk.StringList.new(
                                   [v.label for v in layer.variants]),
                               selected=self._manager.base_variant if current else 0)
            row.connect("notify::selected", lambda r, _p, l=layer:
                        self._choose_base(l.id, r.get_selected()))
        else:
            row = Adw.ActionRow(title=layer.title, subtitle=_subtitle(layer),
                                activatable_widget=radio)
        row.add_prefix(radio)

        def toggled(button):
            if button.get_active() and self._manager.base_id != layer_id:
                variant = row.get_selected() if isinstance(row, Adw.ComboRow) else 0
                self._manager.set_base(layer_id, variant)
        radio.connect("toggled", toggled)
        return row

    def _choose_base(self, layer_id, variant):
        if self._manager.base_id == layer_id and self._manager.base_variant == variant:
            return
        self._manager.set_base(layer_id, variant)
        self._radios[layer_id].set_active(True)

    # Overlays

    def _overlay_row(self, layer):
        view = self._manager.overlays.get(layer.id)
        switch = Gtk.Switch(active=view is not None, valign=Gtk.Align.CENTER)
        switch.update_property([Gtk.AccessibleProperty.LABEL], [layer.title])
        if layer.variants:
            row = Adw.ComboRow(title=layer.title, subtitle=_subtitle(layer),
                               model=Gtk.StringList.new(
                                   [v.label for v in layer.variants]),
                               selected=view.variant_index if view else 0)
            row.add_suffix(switch)
            def chosen(r, _param):
                if switch.get_active():
                    self._manager.set_overlay(layer.id, True, r.get_selected())
                else:
                    switch.set_active(True)   # adds it with this variant
            row.connect("notify::selected", chosen)
        else:
            row = Adw.ActionRow(title=layer.title, subtitle=_subtitle(layer),
                                activatable_widget=switch)
            row.add_suffix(switch)

        def switched(button, _param):
            active = button.get_active()
            if active == (layer.id in self._manager.overlays):
                return
            variant = row.get_selected() if isinstance(row, Adw.ComboRow) else 0
            self._manager.set_overlay(layer.id, active, variant)
        switch.connect("notify::active", switched)
        return row
