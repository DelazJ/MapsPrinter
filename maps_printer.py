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


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        self.iface.removePluginMenu(u'&Maps Printer', self.action)
        self.iface.removePluginMenu(u'&Maps Printer', self.helpAction)
        self.iface.removeToolBarIcon(self.action)

    def getNewCompo(self, w, cView):
        """Function that finds new layout to be added to the list."""

        nameCompo = cView.name()
        if not w.findItems(nameCompo, Qt.MatchExactly):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setText(nameCompo)
            w.addItem(item)

    def saveFile(self):
        """Check if the conditions are filled to export file(s) and
        export the checked layouts to the specified file format."""

        # Ensure list of print layouts is up to date
        # (user can launch export without having previously refreshed the list)
        # will not be needed if the list can automatically be refreshed
        self.refreshList()
        # retrieve the selected layouts list
        self.listCheckedLayout()
        # get the output file format and directory
        extension = self.setFormat(self.dlg.formatBox.currentText())
        folder = self.dlg.path.text()
        # Are there at least one layout checked,
        # an output folder indicated and an output file format chosen?
        d = {
            # the layout list and the number of checked layouts
            (self.dlg.layoutList, len(rowsChecked)),
            # the folder box and its text
            (self.dlg.path, folder),
            # the format list and its choice
            (self.dlg.formatBox, extension)
            }

        # check if all the mandatory infos are filled and if ok, export
        if self.checkFilled(d) and self.checkFolder(folder):
            x = len(rowsChecked)
            i = 0
            # Init progressbars
            self.initGuiButtons()

            QApplication.setOverrideCursor(Qt.BusyCursor)

            for title in rowsChecked:
                cView = QgsProject.instance().layoutManager().layoutByName(title)
                #print(title, cView, cView.name())
                self.dlg.printinglabel.show()
                self.dlg.printinglabel.setText(
                    self.tr(u'Exporting {}...').format(title)
                    )

                # process input events in order to allow canceling
                QCoreApplication.processEvents()
                if self.arret:
                    break
                self.dlg.pageBar.setValue(0)
                self.exportCompo(cView, folder, title, extension)
                i = i + 1
                self.dlg.printBar.setValue(i)
                self.dlg.layoutList.item(
                    rowsChecked[title]).setCheckState(Qt.Unchecked)

            QApplication.restoreOverrideCursor()

            # show an ending message
            # in case of abortion
            if self.arret:
                self.iface.messageBar().pushMessage(
                    self.tr(u'Operation interrupted : '),
                    self.tr(u'Maps from {} composition(s) on {} have been '\
                        'exported to "{}" before cancelling. '\
                        'Some files may be incomplete.'
                        ).format(i, x, folder),
                    level = Qgis.Info, duration = 10
                    )
            # or when export ended completely
            else:
                self.iface.messageBar().pushMessage(
                    self.tr(u'Operation finished : '),
                    self.tr(u'The maps from {} compositions have been '\
                        'exported to "{}".'
                        ).format(x, folder),
                    level = Qgis.Info, duration = 5
                    )
                # keep in memory the output folder
                if extension == '.pdf':
                    QSettings().setValue('/UI/lastSaveAsPdfFile', folder)
                elif extension == '.svg':
                    QSettings().setValue('/UI/lastSaveAsSvgFile', folder)
                else:
                    QSettings().setValue('/UI/lastSaveAsImageDir', folder)

            # Reset the GUI
            self.restoreGui()

    def exportCompo(self, cView, folder, title, extension):
        """Function that sets how to export files."""

        #self.msgWMSWarning(cView)

        myAtlas = cView.atlas()

        #Let's use custom export properties if there are
        exportSettings = self.overrideExportSetings(cView, extension)

        # Do the export process
        exporter = QgsLayoutExporter(cView)

        # Allow export cancelation
        QCoreApplication.processEvents()
        self.dlg.buttonBox.rejected.connect(self.stopProcessing)
        
        if myAtlas.enabled():
            # for i in range(0, myAtlas.count()):
            feedback = QgsFeedback()

            # Allow to listen to changes and increase progressbar
            # or abort the operation
            # with process input events
            QCoreApplication.processEvents()
            self.dlg.buttonBox.rejected.connect(feedback.cancel)
            feedback.progressChanged.connect(self.pageProcessed)

            # if single file export is required (only compatible with pdf, yet)
            # singleFile can be true and None in that case
            if cView.customProperty('singleFile') is not False and extension == '.pdf':
                result, error = exporter.exportToPdf(myAtlas, os.path.join(folder, title + '.pdf'), exportSettings, feedback)

            else: #If instead multiple files will be output
            
                # Check if there's a valid expression for filenames,
                # and otherwise inform that a default one will be used and set it using the layout name.
                # replacement in the GUI is failing at the moment
                if len(myAtlas.filenameExpression()) == 0:
                    self.iface.messageBar().pushMessage(
                        self.tr(u'Empty filename expression'),
                        self.tr(u'The print layout "{}" has an empty output filename expression. {}_@atlas_pagename is used as default.').format(title, title),
                        level = Qgis.Warning
                        )
                    myAtlas.setFilenameExpression(u"'{}_'||@atlas_pagename".format(title))

                current_fileName = myAtlas.filenameExpression()

                #export atlas to multiple pdfs
                if extension =='.pdf':
                    result, error = exporter.exportToPdfs(myAtlas, os.path.join(folder, current_fileName), exportSettings, feedback)

                # export atlas to svg format
                elif extension =='.svg':
                    result, error = exporter.exportToSvg(myAtlas, os.path.join(folder, current_fileName), exportSettings, feedback)

                # export atlas to image format
                else:
                   result, error = exporter.exportToImage(myAtlas, os.path.join(folder, current_fileName), extension, exportSettings, feedback)

            myAtlas.endRender()

        # if the composition has no atlas
        else:
            if extension == '.pdf':
                result = exporter.exportToPdf(os.path.join(folder, title + '.pdf'), exportSettings)

            elif extension == '.svg':
                result = exporter.exportToSvg(os.path.join(folder, title + '.svg'), exportSettings)

            else:
                result = exporter.exportToImage(os.path.join(folder, title + extension), exportSettings)

        # When the export fails (eg it's aborted)
        if not result == QgsLayoutExporter.Success:
            #print( 'noresult')
            self.stopProcessing()

    def overrideExportSetings(self, layout, extension):
        """Because GUI settings are not exposed in Python, we need to find and catch user selection
           See discussion at http://osgeo-org.1560.x6.nabble.com/Programmatically-export-layout-with-georeferenced-file-td5365462.html"""

        if extension == '.pdf':
            exportSettings = QgsLayoutExporter.PdfExportSettings()
            if layout.customProperty('dpi') and layout.customProperty('dpi') != -1 : exportSettings.dpi = layout.customProperty('dpi')
            if layout.customProperty('forceVector') == True : exportSettings.forceVectorOutput = True
            if layout.customProperty('rasterize') == True : exportSettings.rasterizeWholeImage = True
        elif extension == '.svg':
            exportSettings = QgsLayoutExporter.SvgExportSettings()
            if layout.customProperty('dpi') and layout.customProperty('dpi') != -1 : exportSettings.dpi = layout.customProperty('dpi')
            if layout.customProperty('forceVector') == True : exportSettings.forceVectorOutput = True
            if layout.customProperty('svgIncludeMetadata') == True : exportSettings.exportMetadata = True
            if layout.customProperty('svgGroupLayers') == True : exportSettings.exportAsLayers = True
        else:
            exportSettings = QgsLayoutExporter.ImageExportSettings()
            if layout.customProperty('exportWorldFile') == True : exportSettings.generateWorldFile = True
            if layout.customProperty('') == True : exportSettings.exportMetadata = True
            if layout.customProperty('dpi') and layout.customProperty('dpi') != -1 : exportSettings.dpi = layout.customProperty('dpi')
            # if layout.customProperty('atlasRasterFormat') == True : exportSettings.xxxx = True
            # if layout.customProperty('imageAntialias') == True : exportSettings.xxxx = True

        return exportSettings

    def msgEmptyPattern(self):
        """Display a message to tell there's no pattern filename for atlas
        TODO: offer the ability to fill the pattern name.
        """
        self.iface.messageBar().pushMessage(
            self.tr(u'Empty filename pattern'),
                self.tr(u'The print layout "{}" has an empty filename '\
                    'pattern. {}_$feature is used as default.'
                    ).format(self.title, self.title),
            level = Qgis.Warning
            )

    def msgWMSWarning(self, cView):
        """Show message about use of WMS layers in map"""

        for elt in list(cView.composition().items()):
            if isinstance(elt, QgsLayoutItemMap) and elt.containsWMSLayer():
                self.iface.messageBar().pushMessage(
                    'Maps Printer : ',
                    self.tr(u'Project contains WMS Layers. '\
                    'Some WMS servers have a limit for the width and height parameter. '\
                    'Printing layers from such servers may exceed this limit. '\
                    'If this is the case, the WMS layer will not be printed.'),
                    level = Qgis.Warning
                )
                # once we found a map layer concerned, we get out to show just once the message
                break

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
