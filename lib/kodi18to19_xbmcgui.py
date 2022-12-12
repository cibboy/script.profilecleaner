# -*- coding: UTF-8 -*-
#
# Copyright (C) 2022, Palindrones
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
kodi version 18 to 19 (matrix)  xbmcgui wrapper classes
'''
import xbmcgui


class Dialog(xbmcgui.Dialog):

    def __init__(self) -> None:
        pass

    def yesno(self, heading: str, line1: str = None, line2: str = None, line3: str = None,
              nolabel: str = "", yeslabel: str = "", autoclose: int = 0) -> bool:
        message = '\n'.join(filter(None, [line1, line2, line3]))
        return super().yesno(heading, message, nolabel, yeslabel, autoclose)

    def ok(self, heading: str, line1: str = None, line2: str = None, line3: str = None) -> bool:
        message = '\n'.join(filter(None, [line1, line2, line3]))
        return super().ok(heading, message)


class DialogProgress(xbmcgui.DialogProgress):

    def __init__(self) -> None:
        pass

    def create(self, heading: str, line1: str = None, line2: str = None, line3: str = None) -> bool:
        message = '\n'.join(filter(None, [line1, line2, line3]))
        return super().create(heading, message)

    def update(self, percent: any, line1: str = None, line2: str = None, line3: str = None) -> bool:
        message = '\n'.join(filter(None, [line1, line2, line3]))
        if not isinstance(percent, int):
            percent = int(percent)
        return super().update(percent, message)


if (__name__ == "__main__"):
    Dialog().ok("heading", "line1")
    Dialog().ok("heading", "line1", "")
    Dialog().ok("heading", "line1", "line2", None)

    response = Dialog().yesno("heading", "line1")
    response = Dialog().yesno("heading", "line1", "")
    response = Dialog().yesno("heading", "line1", "line2", None)

    DialogProgress().create("heading", "line1")
    DialogProgress().create("heading", "line1", "")
    DialogProgress().create("heading", "line1", "line2", None)

    progress = (1 * 100) / 121
    DialogProgress().update(progress, "line1")
    DialogProgress().update(progress, "line1", "")
    DialogProgress().update(progress, "line1", "line2", None)
