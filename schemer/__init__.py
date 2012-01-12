#!/usr/bin/python

from gi.repository import GObject, Gedit, Gtk
import os

from schemer import GUI

UI_XML = """<ui>
<menubar name="MenuBar">
  <menu name="ToolsMenu" action="Tools">
    <placeholder name="ToolsOps_3">
    <menuitem name="menuItemLaunchGui" action="LaunchGuiAction"/>
    </placeholder>
  </menu>
</menubar>
</ui>"""

class AppActivatable(GObject.Object, Gedit.WindowActivatable):
  __gtype_name__ = "SchemerWindowActivatable"

  window = GObject.property(type=Gedit.Window)

  def __init__(self):
    GObject.Object.__init__(self)

  def _add_ui(self):
    manager = self.window.get_ui_manager()
    self._actions = Gtk.ActionGroup("SchemerActions")
    self._actions.add_actions([
      ('LaunchGuiAction', Gtk.STOCK_INFO, "Edit current scheme", 
        None, "Launch color scheme editor for the current loaded scheme", 
        self.on_example_action_activate),
    ])
    manager.insert_action_group(self._actions)
    self._ui_merge_id = manager.add_ui_from_string(UI_XML)
    manager.ensure_update()

  def on_example_action_activate(self, action, data=None):
    schemer.GUI(self.window.get_active_view())

  def do_activate(self):
    self._add_ui()
