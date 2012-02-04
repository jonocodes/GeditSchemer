#!/usr/bin/python
#
# Gedit Scheme Editor
# https://github.com/jonocodes/GeditSchemer
#
# Copyright (C) Jono Finger 2012 <jono@foodnotblogs.com>
# 
# The program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# The program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.


from gi.repository import GObject, Gedit, Gtk
import os

from schemer import GUI

UI_XML = """<ui>
<menubar name="MenuBar">
  <menu name="EditMenu" action="Edit">
    <placeholder name="EditOps_5">
      <menuitem name="menuItemLaunchGui" action="LaunchGuiAction"/>
    </placeholder>
  </menu>
</menubar>
</ui>"""

class WindowActivatable(GObject.Object, Gedit.WindowActivatable):

  window = GObject.property(type=Gedit.Window)

  def __init__(self):
    GObject.Object.__init__(self)

  def _add_ui(self):

    manager = self.window.get_ui_manager()
    self._actions = Gtk.ActionGroup("SchemerActions")
    self._actions.add_actions([
      ('LaunchGuiAction', Gtk.STOCK_INFO, "Color Scheme Editor", 
        None, "Launch color scheme editor for the current loaded scheme", 
        self.on_example_action_activate),
    ])
    manager.insert_action_group(self._actions)
    self._ui_merge_id = manager.add_ui_from_string(UI_XML)
    manager.ensure_update()

  def on_example_action_activate(self, action, data=None):
    schemer.GUI(Gedit.App)

  def do_activate(self):
    self._add_ui()
