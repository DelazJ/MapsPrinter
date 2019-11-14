# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Show, hide and export several print layouts to pdf, svg or image file format in one-click
                              -------------------
        begin                : 2014-07-24
        git sha              : $Format:%H$
        copyright            : (C) 2014 by Harrissou Sant-anna / CAUE du Maine-et-Loire
        email                : delazj@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from __future__ import absolute_import
from builtins import str
from builtins import range
from builtins import object
import os.path
import sys
import errno
import tempfile

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo, QDir, QUrl, QTimer, Qt, QObject
from qgis.PyQt.QtWidgets import QAction, QListWidgetItem, QFileDialog, QDialogButtonBox, QMenu, QMessageBox, QApplication
from qgis.PyQt.QtGui import QIcon, QCursor, QDesktopServices, QImageWriter

from qgis.core import *
from qgis.gui import QgsMessageBar

from .processing_provider.maps_printer_provider import MapsPrinterProvider

# Initialize Qt resources from file resources.py
from . import resources_rc
# Import the code for the dialog
from .maps_printer_dialog import MapsPrinterDialog
from .gui_utils import GuiUtils


class MapsPrinter(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.provider = None
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MapsPrinter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = MapsPrinterDialog(iface)


    # noinspection PyMethodMayBeStatic

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MapsPrinter', message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.initProcessing()
        # Create action that will start plugin configuration
        self.action = QAction(GuiUtils.get_icon('icon.png'),
                              self.tr(u'Export multiple print layouts'),
                              self.iface.mainWindow()
                              )
        self.helpAction = QAction(GuiUtils.get_icon('about.png'),
                                  self.tr(u'Help'), self.iface.mainWindow()
                                  )

        # Connect the action to the run method
        self.action.triggered.connect(self.run)
        self.helpAction.triggered.connect(GuiUtils.showHelp)

        # Add toolbar button and menu item0
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u'&Maps Printer', self.action)
        self.iface.addPluginToMenu(u'&Maps Printer', self.helpAction)

    def initProcessing(self):
        self.provider = MapsPrinterProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.removePluginMenu(u'&Maps Printer', self.action)
        self.iface.removePluginMenu(u'&Maps Printer', self.helpAction)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Run method that performs all the real work."""

        # when no layout is in the project, display a message about the lack of layouts and exit
        if len(QgsProject.instance().layoutManager().printLayouts()) == 0:
            self.iface.messageBar().pushMessage(
                'Maps Printer : ',
                self.tr(u'There is currently no print layout in the project. '\
                'Please create at least one before running this plugin.'),
                level = Qgis.Info, duration = 5
                )
            self.dlg.close()
        else:
            self.dlg.renameDialog()
            # show the dialog and fill the widget the first time
            if not self.dlg.isVisible():
                self.dlg.populateLayoutList(self.dlg.layoutList)
                self.dlg.show()
            else:
                # if the dialog is already opened but not on top of other windows
                # Put it on the top of all other widgets,
                self.dlg.activateWindow()
                # update the list of layouts and keep the previously selected options in the dialog
                self.dlg.refreshList()
