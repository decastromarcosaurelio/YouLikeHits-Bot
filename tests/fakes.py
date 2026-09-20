"""Minimal fake Selenium driver for unit tests. No browser, no network."""
from selenium.common.exceptions import NoSuchElementException


class FakeElement:
    def __init__(self, text="", displayed=True, on_click=None):
        self.text = text
        self._displayed = displayed
        self._on_click = on_click
        self.clicks = 0

    def is_displayed(self):
        return self._displayed

    def click(self):
        self.clicks += 1
        if self._on_click:
            self._on_click()


class FakeDriver:
    """A page is a dict: selector -> list[FakeElement]. 'body' is the body text."""

    def __init__(self, body="", elements=None, alive=True):
        self.body = body
        self.elements = elements or {}
        self.alive = alive
        self.visited = []
        self.window_handles = ["main"]
        self.current_window_handle = "main"
        self.switch_to = self

    # navigation
    def get(self, url):
        self.visited.append(url)

    def refresh(self):
        self.visited.append("refresh")

    # lookup
    def find_element(self, by, value):
        if value == "body":
            return FakeElement(text=self.body)
        for sel in value.split(","):
            found = self.elements.get(sel.strip())
            if found:
                return found[0]
        raise NoSuchElementException(value)

    def find_elements(self, by, value):
        out = []
        for sel in value.split(","):
            out.extend(self.elements.get(sel.strip(), []))
        return out

    # windows
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
