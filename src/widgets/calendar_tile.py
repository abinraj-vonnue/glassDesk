import calendar
from datetime import date, timedelta

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from .base import Tile, every, make_label

ICONS = ("x-office-calendar-symbolic", "office-calendar-symbolic")
WEEKDAYS = ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa")


class CalendarTile(Tile):
    def __init__(self, width=None):
        super().__init__(icons=ICONS, width=width)

        self.title = make_label("", "tile-title")
        self.header.pack_start(self.title, True, True, 0)
        self.add_header_end(self._nav_button("›", +1))
        self.add_header_end(self._nav_button("‹", -1))

        self.grid = Gtk.Grid(column_homogeneous=True, row_spacing=2)
        self.pack_start(self.grid, False, False, 0)

        self._today = None
        self._view = None
        every(60, self._tick)

    def _nav_button(self, glyph, delta):
        button = Gtk.Button(label=glyph)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_can_focus(False)
        button.get_style_context().add_class("nav-button")
        button.connect("clicked", lambda *_: self._shift(delta))
        return button

    def _tick(self):
        """Re-render when the day rolls over."""
        today = date.today()
        if today != self._today:
            self._today = today
            self._view = (today.year, today.month)
            self._render()

    def _shift(self, delta):
        year, month = self._view
        month += delta
        if month == 0:
            year, month = year - 1, 12
        elif month == 13:
            year, month = year + 1, 1
        self._view = (year, month)
        self._render()

    def _cell(self, text, css_class):
        label = Gtk.Label(label=text)
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        label.set_size_request(28, 28)
        label.get_style_context().add_class(css_class)
        return label

    def _render(self):
        for child in self.grid.get_children():
            child.destroy()

        year, month = self._view
        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
        while len(weeks) < 6:  # constant height when switching months
            last = weeks[-1][-1]
            weeks.append([last + timedelta(days=i + 1) for i in range(7)])

        for col, name in enumerate(WEEKDAYS):
            self.grid.attach(self._cell(name, "cal-head"), col, 0, 1, 1)

        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                cell = self._cell(str(day.day), "cal-day")
                ctx = cell.get_style_context()
                if day.month != month:
                    ctx.add_class("outside")
                if day == self._today:
                    ctx.add_class("today")
                self.grid.attach(cell, col, row, 1, 1)

        self.title.set_text(date(year, month, 1).strftime("%B %Y"))
        self.grid.show_all()
