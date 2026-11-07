"""Disk cache of layer images."""
from cirro.layers.cache import ImageCache


def test_put_get(tmp_path):
    cache = ImageCache(tmp_path)
    assert cache.get("https://x/a") is None
    cache.put("https://x/a", b"png")
    assert cache.get("https://x/a") == b"png"


def test_prune_keeps_the_newest(tmp_path):
    cache = ImageCache(tmp_path, limit=1000)
    for i in range(10):
        cache.put(f"https://x/{i}", bytes(300))
    kept = [i for i in range(10) if cache.get(f"https://x/{i}") is not None]
    assert 9 in kept and len(kept) <= 3
