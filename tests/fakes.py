"""Minimal fake Selenium driver for unit tests. No browser, no network."""
from selenium.common.exceptions import NoSuchElementException


class FakeElement:
    def __init__(self, text="", displayed=True, on_click=None, attrs=None, children=None):
        self.text = text
        self._displayed = displayed
        self._on_click = on_click
        self.attrs = attrs or {}
        self.children = children or {}   # selector -> list[FakeElement], for element-scoped lookups
        self.clicks = 0

    def is_displayed(self):
        return self._displayed

    def get_attribute(self, name):
        return self.attrs.get(name)

    def click(self):
        self.clicks += 1
        if self._on_click:
            self._on_click()

    def find_elements(self, by, value):
        out = []
        for sel in value.split(","):
            out.extend(self.children.get(sel.strip(), []))
        return out

    def find_element(self, by, value):
        found = self.find_elements(by, value)
        if not found:
            raise NoSuchElementException(value)
        return found[0]


class FakeDriver:
    """A page is a dict: selector -> list[FakeElement]. 'body' is the body text.

    Selectors are matched literally; comma lists are split and each part
    looked up on its own. Extra windows opened with `open_window` carry their
    own page; lookups follow `current_window_handle`. `on_get(url)` runs on
    every navigation so a test can rebuild the page like the site would.
    """

    def __init__(self, body="", elements=None, alive=True):
        self.body = body
        self.elements = elements or {}
        self.alive = alive
        self.visited = []
        self.url = ""
        self.pages = {}             # handle -> {"elements", "body", "url"} for extra windows
        self.on_get = None
        self.window_handles = ["main"]
        self.current_window_handle = "main"
        self.switch_to = self

    # navigation
    def get(self, url):
        self.visited.append(url)
        self.url = url
        if self.on_get:
            self.on_get(url)

    def refresh(self):
        self.visited.append("refresh")

    @property
    def current_url(self):
        page = self.pages.get(self.current_window_handle)
        return page["url"] if page else self.url

    # lookup (in the current window)
    def _page_elements(self):
        page = self.pages.get(self.current_window_handle)
        return page["elements"] if page else self.elements

    def _page_body(self):
        page = self.pages.get(self.current_window_handle)
        return page["body"] if page else self.body

    def find_element(self, by, value):
        if value == "body":
            return FakeElement(text=self._page_body())
        elements = self._page_elements()
        for sel in value.split(","):
            found = elements.get(sel.strip())
            if found:
                return found[0]
        raise NoSuchElementException(value)

    def find_elements(self, by, value):
        elements = self._page_elements()
        out = []
        for sel in value.split(","):
            out.extend(elements.get(sel.strip(), []))
        return out

    # windows
    def open_window(self, handle, elements=None, body="", url=""):
        """A popup with its own page (what a trusted click on the site opens)."""
        self.pages[handle] = {"elements": elements or {}, "body": body, "url": url}
        self.window_handles.append(handle)

    def window(self, handle):
        self.current_window_handle = handle

    def close(self):
        if self.current_window_handle in self.window_handles:
            self.window_handles.remove(self.current_window_handle)

    def quit(self):
        self.alive = False

    def __getattribute__(self, name):
        if name == "window_handles" and not object.__getattribute__(self, "alive"):
            raise RuntimeError("invalid session id")
        return object.__getattribute__(self, name)


def logged_in(points="45"):
    """Elements the live site renders only for a logged-in session."""
    return {"#logoutlink": [FakeElement("Logout")], "#currentpoints": [FakeElement(points)]}
