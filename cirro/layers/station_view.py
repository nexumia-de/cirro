"""A station layer (WFS `dwd:RBSN_*`): the time steps come from the
layer's WMS capabilities like any other layer; the data is one GeoJSON
per time step for all stations, drawn by Cirro (station_layer.py)."""
from cirro.layers import info, wfs
from cirro.layers.station_layer import StationLayer
from cirro.layers.view import LayerView


class StationView(LayerView):
    needs_view = False

    def _make_drawing(self, viewport):
        value = self.layer.value
        kind = "wind" if value is not None and value.kind == "wind" else "value"
        unit = value.unit if value is not None and kind == "value" else ""
        decimals = value.decimals if value is not None else 0
        return StationLayer(viewport, kind, unit, decimals)

    def _url(self, time_, view):
        url = wfs.features_url(self.name, time_)
        if time_ is not None:
            self._time_of[url] = time_
        return url

    def _job(self, url):
        name, field = self.name, self.layer.field
        time_ = self._time_of.get(url)
        return lambda: wfs.fetch(name, field, time_)

    def _present(self, result, bounds):
        self.stations = result
        self.drawing.set_stations(result)

    stations = ()

    def describe_at(self, latitude, longitude):
        """Text of the nearest shown station within 30 km, or None."""
        return info.station_text(self.layer.value, self.stations,
                                 latitude, longitude)
