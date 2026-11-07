"""Swipe from the places list back to the map (docs/places.md, phone
layout): a right-to-left swipe on the collapsed split view's sidebar
shows its content again, the reverse of the back swipe that opened the
list.

`AdwNavigationSplitView` has no forward swipe of its own. When it is
collapsed, its only child is an `AdwNavigationView` holding the sidebar
and content pages (libadwaita `adw-navigation-split-view.c`); that view
offers the forward swipe, Alt+→ and the forward mouse button through
its `get-next-page` signal. A new navigation view is made each time the
split view collapses, so the handler is connected again then."""
import gi

gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402


class ForwardSwipe:
    def __init__(self, split):
        self._split = split
        self._view = None
        split.connect("notify::collapsed", lambda *_: self._attach())
        self._attach()

    def _attach(self):
        view = self._split.get_first_child() if self._split.get_collapsed() else None
        if not isinstance(view, Adw.NavigationView):
            view = None
        if view is self._view:
            return
        self._view = view
        if view:
            view.connect("get-next-page", self._next_page)

    def _next_page(self, view):
        # Only from the sidebar: the content is then out of the stack
        # but still added to the navigation view, so it can be pushed.
        content = self._split.get_content()
        if view.get_visible_page() is self._split.get_sidebar() and content:
            return content
        return None
