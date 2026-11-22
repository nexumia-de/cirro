"""Save Mobile Data (issue #34): the setting and the metered state."""

from gi.repository import GObject

from cirro.data_saver import DataSaver, load_enabled, save_enabled


class FakeMonitor(GObject.Object):
    network_metered = GObject.Property(type=bool, default=False)

    def get_network_metered(self):
        return self.network_metered


def test_setting_defaults_to_on_and_is_kept(tmp_path):
    path = tmp_path / "settings.ini"
    assert load_enabled(path)
    save_enabled(False, path)
    assert not load_enabled(path)
    assert "[network]" in path.read_text()


def test_saving_only_when_metered_and_enabled():
    monitor = FakeMonitor()
    saver = DataSaver(True, monitor)
    assert not saver.saving
    monitor.network_metered = True
    assert saver.saving
    saver.set_enabled(False)
    assert not saver.saving
    saver.set_enabled(True)
    monitor.network_metered = False
    assert not saver.saving
