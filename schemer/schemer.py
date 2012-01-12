#!/usr/bin/python
#
# GeditSchemer
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

import os
import sys
import collections
import tempfile
from xml.etree import ElementTree as ET

from gi.repository import Gtk, GdkPixbuf, Gdk, GtkSource

from languages import samples


# Holds style properties for a GtkSourceStyle element
class Props:

  def __init__(self):
  
    self.background = None  # str
    self.foreground = None  # str
    self.italic = False
    self.bold = False
    self.strikethrough = False
    self.underline = False
    
  def fromGtkSourceStyle(self, gtkStyle):
  
    self.background = gtkStyle.props.background
    self.foreground = gtkStyle.props.foreground
    self.italic = gtkStyle.props.italic
    self.bold = gtkStyle.props.bold
    self.underline = gtkStyle.props.underline
    self.strikethrough = gtkStyle.props.strikethrough
    
    # here we make sure every color starts with a hash
    # maybe this is a workaround for a bug that I should file
    # or maybe this is a false assumption
    if self.foreground and self.foreground[0] != '#':
      self.foreground = '#' + self.foreground
      
    if self.background and self.background[0] != '#':
      self.background = '#' + self.background
    
  def toString(self):
    return ('FG=%s BG=%s Ital=%s Bold=%s Strike=%s Under=%s' %
      (self.foreground, self.background, self.italic, self.bold,
      self.strikethrough,self.underline))
    

class GUI:
  
  def __init__(self, geditView):

    # constants

    self.colorBlack = Gdk.color_parse('#000000');
    
    # we set this explicitly since the API does not give us a method for it
    self.guiStyleIds = ['bracket-match', 'bracket-mismatch',
      'current-line', 'cursor', 'line-numbers', 'secondary-cursor',
      'selection', 'selection-unfocused', 'text']

    # set up GUI widgets and signals
    
    GtkSource.View() # hack to get GtkSourceView widget to run from glade file

    self.builder = Gtk.Builder()

    uiFile = os.path.join(os.path.dirname(__file__), 'schemer.ui')

    if (os.path.isfile(uiFile)):
      self.builder.add_from_file(uiFile)
    else:
      print('unable to find UI file')
      sys.exit(1)
    
    self.builder.connect_signals(self)
    
    self.window = self.builder.get_object('window')
    self.aboutDialog = self.builder.get_object('aboutdialog')
    
    self.sourceBuffer = GtkSource.Buffer(max_undo_levels=0)
    self.sourceView = self.builder.get_object('gtksourceviewSample')
    self.sourceView.set_buffer(self.sourceBuffer)
    
    self.liststoreStyles = self.builder.get_object('liststoreStyles')
    self.liststoreLanguages = self.builder.get_object('liststoreLanguages')
    self.comboboxLanguages = self.builder.get_object('comboboxLanguages')
    self.treeviewStyles = self.builder.get_object('treeviewStyles')
    
    self.colorbuttonForeground = self.builder.get_object('colorbuttonForeground')
    self.colorbuttonBackground = self.builder.get_object('colorbuttonBackground')
    self.togglebuttonItalic = self.builder.get_object('togglebuttonItalic')
    self.togglebuttonBold = self.builder.get_object('togglebuttonBold')
    self.togglebuttonUnderline = self.builder.get_object('togglebuttonUnderline')
    self.togglebuttonStrikethrough = self.builder.get_object('togglebuttonStrikethrough')
    self.checkbuttonForeground = self.builder.get_object('checkbuttonForeground')
    self.checkbuttonBackground = self.builder.get_object('checkbuttonBackground')
    self.resetButton = self.builder.get_object('resetButton')
    
    self.entryName = self.builder.get_object('entryName')
    self.entryAuthor = self.builder.get_object('entryAuthor')
    self.entryDescription = self.builder.get_object('entryDescription')
    self.entryId = self.builder.get_object('entryId')
    self.labelSample = self.builder.get_object('labelSample')
    
    self.colorbuttonBackground.connect('color-set', self.on_style_changed)
    self.colorbuttonForeground.connect('color-set', self.on_style_changed)

    self.builder.get_object('buttonCancel').connect('clicked', self.closeWindow)
    self.builder.get_object('buttonSave').connect('clicked', self.on_save_clicked)
    
    self.togglebuttonItalicHandler = self.togglebuttonItalic.connect(
      'toggled', self.on_style_changed)
    self.togglebuttonBoldHandler = self.togglebuttonBold.connect(
      'toggled', self.on_style_changed)
    self.togglebuttonUnderlineHandler = self.togglebuttonUnderline.connect(
      'toggled', self.on_style_changed)
    self.togglebuttonStrikethroughHandler = self.togglebuttonStrikethrough.connect(
      'toggled', self.on_style_changed)
    
    self.checkbuttonBackgroundHandler =  self.checkbuttonBackground.connect(
      'toggled', self.on_background_toggled)
    self.checkbuttonForegroundHandler = self.checkbuttonForeground.connect(
      'toggled', self.on_foreground_toggled)
    
    self.resetButton.connect('clicked', self.on_reset_clicked)
    
    self.schemeManager = GtkSource.StyleSchemeManager()
    self.languageManager = GtkSource.LanguageManager()
    
    self.dictAllStyles = collections.OrderedDict()
    
    languages = self.languageManager.get_language_ids()
    languages.sort()

    self.geditView = geditView

    self.defaultLanguageId = 'c'
    self.defaultLanguageName = 'C'
    self.defaultLanguage = self.languageManager.get_language(self.defaultLanguageId)

    # guess the language from the current buffer
    if geditView.get_buffer():
      bufferLanguage = geditView.get_buffer().get_language()

      if bufferLanguage and bufferLanguage.get_id() in languages:
        self.defaultLanguageId = bufferLanguage.get_id()
        self.defaultLanguageName = bufferLanguage.get_name()
        self.defaultLanguage = bufferLanguage

    self.currentLanguageId = self.defaultLanguageId
    self.currentLanguadeName = self.defaultLanguageName
        
    # watch temp directory to help the sample viewer
    self.schemeManager.append_search_path(tempfile.gettempdir())

    self.origSchemeFile = None

    # TODO figure out how to deal with a non existant buffer
    self.load_scheme(geditView.get_buffer().get_style_scheme().get_filename())
    
    for langStyleId in self.guiStyleIds:
      self.liststoreStyles.append([langStyleId])
    
    self.langMapNameToId = {}
    
    # make a special case for Defaults which is moved to the top and includes GUI styles
    self.liststoreLanguages.append(['  Default styles'])
    self.langMapNameToId['  Default styles'] = 'def'
    
    for thisLanguage in languages:
      langName = self.languageManager.get_language(thisLanguage).get_name()
      self.langMapNameToId[langName] = thisLanguage
      
      if langName != 'Defaults':
        self.liststoreLanguages.append([langName])

    renderer_text = Gtk.CellRendererText()
    self.comboboxLanguages.pack_start(renderer_text, True)
    self.comboboxLanguages.connect('changed', self.on_language_selected)
    self.comboboxLanguages.add_attribute(renderer_text, 'text', 0)

    self.treeviewStylesSelection = self.treeviewStyles.get_selection()
    self.treeviewStylesSelection.connect('changed', self.on_style_selected)
    
    # select the first language
    self.comboboxLanguages.set_active(0)
    
    # select the first style
    treeIter = self.treeviewStyles.get_model().get_iter_first()
    self.treeviewStylesSelection.select_iter(treeIter)
    model = self.treeviewStyles.get_model()
    self.selectedStyleId = model[treeIter][0]
  
  def closeWindow(self, data):
    self.window.destroy()

  def destroy(self, window):
    self.window.destroy()
    

  def on_save_clicked(self, param):

    inFile = self.origSchemeFile

    tempDirectory = tempfile.gettempdir()

    outFile = None

    if os.access(inFile, os.W_OK) and (str(os.path.dirname(inFile)) != tempDirectory):
      outFile = inFile
    else:
      possibleDirs = self.schemeManager.get_search_path()

      for thisDir in possibleDirs:

        if thisDir == tempDirectory:
          continue

        # create the directory if it does not exist
        if not os.path.isdir(thisDir):
          try:
            os.makedirs(thisDir)
          except:
            pass

        if (os.access(thisDir, os.W_OK)):
          outFile = os.path.join(thisDir, self.entryId.get_text() + '.xml')
          break

    if outFile:

      if inFile != outFile:

        schemeIds = self.schemeManager.get_scheme_ids()

        for thisSchemeId in schemeIds:
          if self.entryId.get_text() == thisSchemeId or self.entryName.get_text() == self.schemeManager.get_scheme(thisSchemeId).get_name():

            text = '<span weight="bold" size="larger">There was a problem saving the scheme</span>' \
              '\n\nYou not have permission to overwrite the scheme you have choosen.' \
              '\nInstead a copy will be created.' \
              '\n\nPlease be sure to choose a Name and ID that are not already in use.\n'
            messagedialog(Gtk.MessageType.ERROR, text, parent=self.window, buttons=Gtk.ButtonsType.NONE,
              additional_buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))

            return

      if not self.write_scheme(outFile, self.entryId.get_text()):
        messagedialog(Gtk.MessageType.ERROR, 'Error saving theme', parent=self.window, buttons=Gtk.ButtonsType.NONE,
              additional_buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
      else:

        # TODO as of gedit 3.2.5 there is no way to refresh the Gedit buffer
        # https://bugzilla.gnome.org/show_bug.cgi?id=667706
        updatedScheme = self.schemeManager.get_scheme(self.entryId.get_text())
        self.schemeManager.force_rescan()

        # viewManager = Gedit.View.StyleSchemeManager()
        # viewManager.force_rescan()
        # self.schemeManager.get_default().force_rescan()
        self.geditView.get_buffer().set_style_scheme(updatedScheme)

        # for now we tell the user to restart the program
        messagedialog(Gtk.MessageType.INFO, 'Restart Gedit to use the updated scheme', 
              parent=self.window, buttons=Gtk.ButtonsType.NONE,
              additional_buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK))

    else:
      messagedialog(Gtk.MessageType.ERROR, 'Error saving theme', buttons=Gtk.ButtonsType.NONE,
            parent=self.window, additional_buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
      pass

    self.window.destroy()


  def load_scheme(self, schemeIdOrFile):
    """ Load a scheme from a file or an existing scheme ID """

    if os.path.isfile(schemeIdOrFile):
      
      directory = os.path.dirname(schemeIdOrFile)
    
      if directory not in self.schemeManager.get_search_path():
        self.schemeManager.prepend_search_path(directory)
      
      fp = open(schemeIdOrFile, 'r')
      xmlTree = ET.parse(fp)
      fp.close()

      if xmlTree.getroot().tag == 'style-scheme':
        thisScheme = self.schemeManager.get_scheme(xmlTree.getroot().attrib['id'])
      
      if thisScheme == None:
        return False
        
      testFilename = thisScheme.get_filename()
      
      if testFilename != schemeIdOrFile:
        # there must have been some conflict, since it opened the wrong file

        text = '<span weight="bold" size="larger">There was a problem opening the file</span>\n\nYou appear to have schemes with the same IDs in different directories\n'
        messagedialog(Gtk.MessageType.ERROR, text,
          parent=self.window, buttons=Gtk.ButtonsType.NONE,
          additional_buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        
        return False
        
      self.origSchemeFile = schemeIdOrFile

    else:

      thisScheme = self.schemeManager.get_scheme(schemeIdOrFile)
    
      if thisScheme == None:
        return False
    
    self.currentScheme = thisScheme
    
    self.entryName.set_text( thisScheme.get_name() )
    self.entryAuthor.set_text(', '.join(thisScheme.get_authors()))
    self.entryDescription.set_text(thisScheme.get_description())
    self.entryId.set_text(thisScheme.get_id())
    
    # get all the style elements
    # since there are no API calls to do this, we parse the XML file for now
    # also works around this https://bugzilla.gnome.org/show_bug.cgi?id=667194
    self.origSchemeFile = self.currentScheme.get_filename()
    
    fp = open(self.origSchemeFile, 'r')
    xmlTree = ET.parse(fp)
    fp.close()
    styleElements = xmlTree.findall('style')
    
    self.dictAllStyles.clear()
    
    for styleElement in styleElements:
      thisStyle = self.currentScheme.get_style(styleElement.attrib['name'])
      styleProps = Props()
      styleProps.fromGtkSourceStyle(thisStyle)
      self.dictAllStyles[styleElement.attrib['name']] = styleProps;
            
    self.sourceBuffer.set_style_scheme(self.currentScheme);
    
    # set up temp file so the sample view can be updated
    self.tempSchemeId = thisScheme.get_id() + '_temp'
    self.tempSchemeFile = tempfile.gettempdir() + '/' + self.tempSchemeId + '.xml'
    
    return True
    
  def clear_and_disable_style_buttons(self):
    self.colorbuttonForeground.set_color(self.colorBlack)
    self.colorbuttonBackground.set_color(self.colorBlack)
    self.colorbuttonForeground.set_sensitive(False)
    self.checkbuttonForeground.set_active(False)
    self.colorbuttonBackground.set_sensitive(False)
    self.checkbuttonBackground.set_active(False)
    
    self.togglebuttonItalic.set_active(False)
    self.togglebuttonBold.set_active(False)
    self.togglebuttonStrikethrough.set_active(False)
    self.togglebuttonUnderline.set_active(False)
    
    self.resetButton.set_sensitive(False)
    
  def update_sample_view(self):
    """
    Update the sample shown in the GUI.
    To do this we must write the scheme to disk and reload it from there.
    """
    
    # write it to disk
    self.write_scheme(self.tempSchemeFile, self.tempSchemeId)
    
    # and reload it from disk
    self.schemeManager.force_rescan()
    
    newScheme = self.schemeManager.get_scheme(self.tempSchemeId)
    self.sourceBuffer.set_style_scheme(newScheme);
    
  def write_scheme(self, location, schemeId):
    """Write the scheme to disk
    
    location -- the file location to write to
    schemeId -- the ID of the scheme
    """

    output = '<style-scheme name="'+ self.entryName.get_text() \
      + '" id="'+ schemeId +'" version="1.0">\n'
    
    output += '  <author>'+ self.entryAuthor.get_text() +'</author>\n'
    output += '  <description>'+ self.entryDescription.get_text() +'</description>\n\n'
    
    for k, v in self.dictAllStyles.items():
      output += '  <style name="'+k+'"\t'
      
      if (v.foreground): output += 'foreground="'+ v.foreground +'" '
      if (v.background): output += 'background="'+ v.background +'" '
      if (v.italic): output += 'italic="true" '
      if (v.bold): output += 'bold="true" '
      if (v.underline):  output += 'underline="true" '
      if (v.strikethrough):  output += 'strikethrough="true" '
      
      output += '/>\n'
    
    output  += '</style-scheme>\n'
    
    try:
      fp = open(location, 'w')
      fp.write(output)
      fp.close()
    except:
      return False

    return True

    
  def on_reset_clicked(self, param):
    
    if self.selectedStyleId in self.dictAllStyles:
    
      del self.dictAllStyles[self.selectedStyleId]
    
      # reset the GUI
      self.clear_and_disable_style_buttons()
      
      self.update_sample_view()
      
  def on_background_toggled(self, param):
    
    if param.get_active():
      self.colorbuttonBackground.set_sensitive(True)
      self.colorbuttonBackground.activate()
    else:
      self.colorbuttonBackground.set_sensitive(False)
      self.dictAllStyles[self.selectedStyleId].background = None;
      self.update_sample_view()
      
  def on_foreground_toggled(self, param):
    
    if param.get_active():
      self.colorbuttonForeground.set_sensitive(True)
      self.colorbuttonForeground.activate()
    else:
      self.colorbuttonForeground.set_sensitive(False)
      self.dictAllStyles[self.selectedStyleId].foreground = None;
      self.update_sample_view()
  
  def on_style_changed(self, data):
        
    if self.selectedStyleId not in self.dictAllStyles:
      self.dictAllStyles[self.selectedStyleId] = Props()
    
    cScale = 255.0/65535.0
    
    if data == self.colorbuttonBackground:
      color = data.get_color()
      self.dictAllStyles[self.selectedStyleId].background = ('#%02x%02x%02x' %
        (color.red * cScale, color.green * cScale, color.blue * cScale))
    
    elif data == self.colorbuttonForeground:
      color = data.get_color()
      self.dictAllStyles[self.selectedStyleId].foreground = ('#%02x%02x%02x' %
        (color.red * cScale, color.green * cScale, color.blue * cScale))
    
    elif data == self.togglebuttonBold:
      self.dictAllStyles[self.selectedStyleId].bold = data.get_active()
      
    elif data == self.togglebuttonItalic:
      self.dictAllStyles[self.selectedStyleId].italic = data.get_active()
    
    elif data == self.togglebuttonUnderline:
      self.dictAllStyles[self.selectedStyleId].underline = data.get_active()
    
    elif data == self.togglebuttonStrikethrough:
      self.dictAllStyles[self.selectedStyleId].strikethrough = data.get_active()
    
    self.update_sample_view()
    
  def on_style_selected(self, selection):
    model, treeiter = selection.get_selected()

    # handle the special case for when the styles get cleared since the signal activates
    if treeiter == None:
      return
    
    self.selectedStyleId = self.currentLanguageId + ':' + model[treeiter][0]

    # handle the special case for GUI styles
    if self.selectedStyleId not in self.dictAllStyles and self.currentLanguageId == 'def':
      self.selectedStyleId = model[treeiter][0]
    
    # block all the toggle handlers so they dont get triggered
    self.togglebuttonItalic.handler_block(self.togglebuttonItalicHandler)
    self.togglebuttonBold.handler_block(self.togglebuttonBoldHandler)
    self.togglebuttonUnderline.handler_block(self.togglebuttonUnderlineHandler)
    self.togglebuttonStrikethrough.handler_block(self.togglebuttonStrikethroughHandler)
    self.checkbuttonBackground.handler_block(self.checkbuttonBackgroundHandler)
    self.checkbuttonForeground.handler_block(self.checkbuttonForegroundHandler)
    
    if self.selectedStyleId in self.dictAllStyles:
      
      thisStyle = self.dictAllStyles[self.selectedStyleId]
      
      # handle foreground and background colors

      if thisStyle.foreground:
        self.colorbuttonForeground.set_color(Gdk.color_parse(thisStyle.foreground))
        self.colorbuttonForeground.set_sensitive(True)
        self.checkbuttonForeground.set_active(True)
      else:
        self.colorbuttonForeground.set_color(self.colorBlack)
        self.colorbuttonForeground.set_sensitive(False)
        self.checkbuttonForeground.set_active(False)

      if thisStyle.background:
        self.colorbuttonBackground.set_color(Gdk.color_parse(thisStyle.background))
        self.colorbuttonBackground.set_sensitive(True)
        self.checkbuttonBackground.set_active(True)
      else:
        self.colorbuttonBackground.set_color(self.colorBlack)
        self.colorbuttonBackground.set_sensitive(False)
        self.checkbuttonBackground.set_active(False)
        
      # handle text styling

      self.togglebuttonItalic.set_active(thisStyle.italic)
      self.togglebuttonBold.set_active(thisStyle.bold)
      self.togglebuttonStrikethrough.set_active(thisStyle.strikethrough)
      self.togglebuttonUnderline.set_active(thisStyle.underline)
      self.resetButton.set_sensitive(True)
      
    # if style does not exist, set to default GUI values
    else:
      self.clear_and_disable_style_buttons()
      
    # unblock toggle handlers so the user can do stuff
    self.togglebuttonItalic.handler_unblock(self.togglebuttonItalicHandler)
    self.togglebuttonBold.handler_unblock(self.togglebuttonBoldHandler)
    self.togglebuttonUnderline.handler_unblock(self.togglebuttonUnderlineHandler)
    self.togglebuttonStrikethrough.handler_unblock(self.togglebuttonStrikethroughHandler)
    self.checkbuttonBackground.handler_unblock(self.checkbuttonBackgroundHandler)
    self.checkbuttonForeground.handler_unblock(self.checkbuttonForegroundHandler)
  
  def on_language_selected(self, combo):

    tree_iter = combo.get_active_iter()
    if tree_iter != None:
      model = combo.get_model()
      self.currentLanguageName = model[tree_iter][0]
      self.currentLanguageId = self.langMapNameToId[self.currentLanguageName]
      
      self.liststoreStyles.clear()
      
      # remove the language namespace thing from the style name
      removeLen = len(self.currentLanguageId) + 1
    
      thisLanguage = self.languageManager.get_language(self.currentLanguageId)

      if thisLanguage != None:
        styleIds = thisLanguage.get_style_ids()
        
        styleIds.sort() # make the styles list alphabetical
        
        if self.currentLanguageId == 'def':
          for styleId in self.guiStyleIds:
            self.liststoreStyles.append([styleId])
        
        for styleId in styleIds:
          self.liststoreStyles.append([styleId[removeLen:]])
            
      # select the first style in the list
      treeIter = self.treeviewStyles.get_model().get_iter_first()
      self.treeviewStylesSelection.select_iter(treeIter)
      model = self.treeviewStyles.get_model()
      self.selectedStyleId = model[treeIter][0]
      
      # update the sample view
      if self.currentLanguageId in samples:
        self.sourceBuffer.set_language(thisLanguage);
        self.sourceBuffer.set_text(samples[self.currentLanguageId])
        self.labelSample.set_text(self.currentLanguageName + ' sample')
      else:
        self.sourceBuffer.set_language(self.defaultLanguage);
        self.sourceBuffer.set_text(samples[self.defaultLanguageId])
        self.labelSample.set_text(self.defaultLanguageName + ' sample')


def messagedialog(dialog_type, short, long=None, parent=None,
                  buttons=Gtk.ButtonsType.OK, additional_buttons=None):

  d = Gtk.MessageDialog(parent=parent, flags=Gtk.DialogFlags.MODAL,
    type=dialog_type, buttons=buttons)

  if additional_buttons:
    d.add_buttons(*additional_buttons)

  d.set_markup(short)

  if long:
    if isinstance(long, Gtk.Widget):
      widget = long
    elif isinstance(long, str):
      widget = Gtk.Label()
      widget.set_markup(long)
    else:
      raise TypeError('"long" must be a Gtk.Widget or a string')
    
    expander = Gtk.Expander(label = 'Click here for details')
    expander.set_border_width(6)
    expander.add(widget)
    d.vbox.pack_end(expander, True, True, 0)
      
  d.show_all()
  response = d.run()
  d.destroy()
  return response
