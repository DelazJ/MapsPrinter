# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Show, hide and export several print composers to pdf, svg or image file format in one-click
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
        self.dlg = MapsPrinterDialog()

        self.arret = False

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
        self.action = QAction(QIcon(':/plugins/MapsPrinter/icons/icon.png'),
                              self.tr(u'Export multiple print layouts'),
                              self.iface.mainWindow()
                              )
        self.helpAction = QAction(QIcon(':/plugins/MapsPrinter/icons/about.png'),
                                  self.tr(u'Help'), self.iface.mainWindow()
                                  )

        # Connect actions to context menu
        self.dlg.layoutList.customContextMenuRequested.connect(self.context_menu)

        # Connect the action to the run method
        self.action.triggered.connect(self.run)
        self.helpAction.triggered.connect(self.showHelp)
        self.dlg.buttonBox.helpRequested.connect(self.showHelp)

        # Connect to the export button to do the real work
        self.dlg.exportButton.clicked.connect(self.saveFile)

        # Connect the signal to set the "select all" checkbox behaviour
        self.dlg.checkBox.clicked.connect(self.on_selectAllcbox_changed)
        self.dlg.layoutList.itemChanged.connect(self.on_layoutcbox_changed)

        # Connect to the browser button to select export folder
        self.dlg.browser.clicked.connect(self.browseDir)

        # Connect the action to the updater button so you can update the list of layouts
        # will be useless if i can synchronise with the layout manager widgetlist
        self.dlg.updater.clicked.connect(self.refreshList)
        # refresh the layout list when a layout is created or deleted (miss renaming case)
        # self.iface.layoutAdded.connect(self.refreshList)
        # self.iface.layoutWillBeRemoved.connect(self.refreshList, Qt.QueuedConnection)
        # self.iface.layoutRemoved.connect(self.refreshList)

        # Connect some actions to manage dialog status while another project is opened
        self.iface.newProjectCreated.connect(self.dlg.close)
        self.iface.projectRead.connect(self.renameDialog)
        self.iface.projectRead.connect(self.refreshList)

        # Add toolbar button and menu item0
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u'&Maps Printer', self.action)
        self.iface.addPluginToMenu(u'&Maps Printer', self.helpAction)

        # Hide the Cancel button and progress text at the opening
        self.dlg.printinglabel.hide()
        self.dlg.btnCancel = self.dlg.buttonBox.button(QDialogButtonBox.Cancel)
        self.dlg.btnCancel.hide()
        self.dlg.btnClose = self.dlg.buttonBox.button(QDialogButtonBox.Close)

    def context_menu(self):
        """Add context menu fonctions."""

        menu = QMenu(self.dlg.layoutList)
        menu.addAction(self.tr(u'Check...'), self.actionCheckLayout)
        menu.addAction(self.tr(u'Uncheck...'), self.actionUncheckLayout)
        menu.addSeparator()
        menu.addAction(self.tr(u'Show...'), self.actionShowLayout)
        menu.addAction(self.tr(u'Close...'), self.actionHideLayout)
        menu.exec_(QCursor.pos())

    def actionCheckLayout(self):
        for item in self.dlg.layoutList.selectedItems():
            item.setCheckState(Qt.Checked)

    def actionUncheckLayout(self):
        for item in self.dlg.layoutList.selectedItems():
            item.setCheckState(Qt.Unchecked)

    def actionShowLayout(self):
        selected = {item.text() for item in self.dlg.layoutList.selectedItems()}
        for cView in QgsProject.instance().layoutManager().printLayouts():
            if cView.name() in selected:
                #print (cView.name(), cView.layoutType())
                self.iface.openLayoutDesigner(cView)

    def actionHideLayout(self):
        selected = {item.text() for item in self.dlg.layoutList.selectedItems()}
        #print(selected)
        designers = [d for d in self.iface.openLayoutDesigners() if d.masterLayout().name() in selected]
        #print(designers)
        for d in designers:
            #print(d, type(d))
            d.close()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        self.iface.removePluginMenu(u'&Maps Printer', self.action)
        self.iface.removePluginMenu(u'&Maps Printer', self.helpAction)
        self.iface.removeToolBarIcon(self.action)

    def showHelp(self):
        """Shows the help page."""

        locale = QSettings().value('locale/userLocale')[0:2]
        help_file = self.plugin_dir + '/help/help_{}.html'.format(locale)

        if os.path.exists(help_file):
            QDesktopServices.openUrl(QUrl('file:///'+ help_file))
        else:
            QDesktopServices.openUrl(QUrl(
                'file:///'+ self.plugin_dir + '/help/help.html')
                )

    def getNewCompo(self, w, cView):
        """Function that finds new layout to be added to the list."""

        nameCompo = cView.name()
        if not w.findItems(nameCompo, Qt.MatchExactly):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setText(nameCompo)
            w.addItem(item)

    def populateLayoutList(self, w):
        """Called to populate the layout list when opening a new dialog."""

        # Get  all the layouts in a previously emptied list
        w.clear()
        # Populate export format listbox
        self.listFormat(self.dlg.formatBox)
        # Ensure the "select all" box is unchecked
        self.dlg.checkBox.setChecked(False)

        for cView in QgsProject.instance().layoutManager().printLayouts():
            self.getNewCompo(w, cView)
        w.sortItems()

    def refreshList(self):
        """When updating the list of layouts,
        the state of layouts already listed is kept if they are still in the project
        so just add new layouts and erase those deleted/renamed."""

        currentLayouts = []
        i,j = 0,0

        if len(QgsProject.instance().layoutManager().printLayouts()) == 0 and self.dlg.isVisible():
            self.iface.messageBar().pushMessage('Maps Printer : ',
                self.tr(u'dialog shut because no more print layout in the project.'),
                level = Qgis.Info, duration = 5
                )
            self.dlg.close()
        else:
            # Get the current list of layouts
            while i < len(QgsProject.instance().layoutManager().printLayouts()):
            # for i in range(len(QgsProject.instance().layoutManager().printLayouts()):
                currentLayouts.append(
                    QgsProject.instance().layoutManager().printLayouts()[i].name()
                    )
                i += 1

            # Erase deleted (or renamed) layouts
            while j < self.dlg.layoutList.count():
                if self.dlg.layoutList.item(j).text() not in currentLayouts:
                    self.dlg.layoutList.takeItem(j)
                else:
                    j += 1

            # Add new layouts to the list
            for cView in QgsProject.instance().layoutManager().printLayouts():
                self.getNewCompo(self.dlg.layoutList, cView)
            self.dlg.layoutList.sortItems()

            # And check if all the remained rows are checked
            # (called to display coherent check boxes). Better way?
            self.on_layoutcbox_changed()

    def on_selectAllcbox_changed(self):
        """When changing the state of the "Check all" checkbox,
        do the same to the layouts listed below.
        """

        etat = self.dlg.checkBox.checkState()
        for rowList in range(0, self.dlg.layoutList.count()):
            self.dlg.layoutList.item(rowList).setCheckState(etat)

    def listCheckedLayout(self):
        """Get all the boxes and texts checked in the list."""

        global rowsChecked

        # rowsChecked = [rowList for rowList in range(0, self.dlg.layoutList.count()) \
            # if self.dlg.layoutList.item(rowList).checkState() == Qt.Checked]
            #
        # rowsChecked = {(rowList, self.dlg.layoutList.item(rowList).text()) \
            # for rowList in range(0, self.dlg.layoutList.count()) \
            # if self.dlg.layoutList.item(rowList).checkState() == Qt.Checked}
            #
        # rowsChecked = {rowList:self.dlg.layoutList.item(rowList).text() for rowList in range(0, self.dlg.layoutList.count()) \
            # if self.dlg.layoutList.item(rowList).checkState() == Qt.Checked}
            #
        rowsChecked = {
            self.dlg.layoutList.item(rowList).text(): rowList for rowList in range(
                0, self.dlg.layoutList.count()
                ) if self.dlg.layoutList.item(rowList).checkState() == Qt.Checked
        }

        return rowsChecked

    def on_layoutcbox_changed(self):
        """When at least one of the layouts listed is unchecked,
        then the "Check All" checkbox should be unchecked too.
        """

        self.listCheckedLayout()
        if len(rowsChecked) == self.dlg.layoutList.count():
            self.dlg.checkBox.setChecked(True)
        else:
            self.dlg.checkBox.setChecked(False)

    def listFormat(self, box):
        """List all the file formats used in export mode."""

        box.clear()
        list1 = [
            '',
            self.tr(u'PDF format (*.pdf *.PDF)'),
            self.tr(u'SVG format (*.svg *.SVG)'),
            ]
        #Automatically add supported image formats instead of manually
        imageformats = QImageWriter.supportedImageFormats()
        for f in imageformats:
            fs = f.data().decode('utf-8')
            list1.append(self.tr(u'{} format (*.{} *.{})').format(fs.upper(), fs, fs.upper()))
            
        #Todo: add an entry for the custom property atlasRasterFormat
        #which will export each print layout to its custom format if selected

            # >>>lst=QgsProject.instance().layoutManager().layouts()
            # >>>lst[0].customProperties()
            # ['atlasRasterFormat']
            # >>>lst[0].customProperty('atlasRasterFormat')
            # 'png'

        box.addItems(list1)
        box.insertSeparator(2)
        box.insertSeparator(4)

    def setFormat(self, value):
        """Retrieve the format suffix that will be appended to the file."""

        try:
            f = value.split()[2].strip('(*')
            # f = value.split('*')[1].strip()
        except:
            f = ''
        return f

    def browseDir(self):
        """Open the browser so the user selects the output directory."""

        settings = QSettings()
        if self.dlg.formatBox.currentIndex() == 1 : # if extension is pdf
            dir = settings.value('/UI/lastSaveAsPdfFile')
        else:
            dir = settings.value('/UI/lastSaveAsImageDir')

        folderDialog = QFileDialog.getExistingDirectory(
            None,
            '',
            dir,
            QFileDialog.ShowDirsOnly,
            # QFileDialog.DontResolveSymlinks
            )

        #Do not alter potential folder path if the dialog was canceled
        if folderDialog == '':
            self.dlg.path.setText(self.dlg.path.text())
        else:
            self.dlg.path.setText(folderDialog)

    def checkFolder(self, outputDir):
        """Ensure export's folder exists and is writeable."""

        # It'd be better to find a way to check writeability in the first try...
        try:
            os.makedirs(outputDir)
            # settings.setValue('/UI/lastSaveAsImageDir', outputDir)
        except Exception as e:
            # if the folder already exists then let's check it's writeable
            if e.errno == errno.EEXIST:
                try:
                    testfile = tempfile.TemporaryFile(dir = outputDir)
                    testfile.close()
                except Exception as e:
                    if e.errno in (errno.EACCES, errno.EPERM):
                        QMessageBox.warning(None, self.tr(u'Unable to write in folder'),
                            self.tr(u"You don't have rights to write in this folder. "\
                            "Please, select another one!"),
                            QMessageBox.Ok, QMessageBox.Ok)
                    else:
                        raise
                    self.browseDir()
                else:
                    return True
            # if the folder doesn't exist and can't be created then choose another directory
            elif e.errno in (errno.EACCES, errno.EPERM):
                QMessageBox.warning(None, self.tr(u'Unable to use the directory'),
                    self.tr(u"You don't have rights to create or use such a folder. " \
                    "Please, select another one!"),
                    QMessageBox.Ok, QMessageBox.Ok)
                self.browseDir()
            # for anything else, let user know (mind if it's worth!?)
            else:
                QMessageBox.warning(None, self.tr(u'An error occurred : '),
                    u'{}'.format(e), QMessageBox.Ok, QMessageBox.Ok)
                self.browseDir()
        else: # if it is created with no exception
            return True

    def checkFilled(self, d):
        """Check if all the mandatory informations are filled."""

        missing = []
        for (x, y) in d:
            if not y: # if the second value is null, 0 or empty
                # outline the first item in red
                x.setStyleSheet('border-style: outset; border-width: 1px; border-color: red')
                # retrieve the missing value
                missing.append(y)
            else:
                x.setStyleSheet('border-color: palette()')
        #[missing.append(x[1]) for x in d if not x[1]]
        # and if there are missing values, show error message and stop execution
        if missing:
            self.iface.messageBar().pushMessage('Maps Printer : ',
                self.tr(u'Please consider filling the mandatory field(s) outlined in red.'),
                level = Qgis.Critical,
                duration = 5)
            return False
        # otherwise let's execute the export
        else:
            return True

    def initGuiButtons(self):
        """Init the GUI to follow export processes."""

        self.dlg.printBar.setValue(0)
        self.dlg.printBar.setMaximum(len(rowsChecked))
        self.dlg.exportButton.setEnabled(False)

        # Activate the Cancel button to stop export process, and hide the Close button
        self.dlg.buttonBox.disconnect()
        self.dlg.btnClose.hide()
        self.dlg.btnCancel.show()
        self.dlg.buttonBox.rejected.connect(self.stopProcessing)
        # self.dlg.btnCancel.clicked.connect(self.stopProcessing)

    def pageProcessed(self):
        """Increment the page progressbar."""

        self.dlg.pageBar.setValue(self.dlg.pageBar.value() + 1)

    def stopProcessing(self):
        """Help to stop the export processing."""

        self.arret = True

    def restoreGui(self):
        """Reset the GUI to its initial state."""

        QTimer.singleShot(1000, lambda: self.dlg.pageBar.setValue(0))
        self.dlg.printinglabel.setText('')
        self.dlg.printinglabel.hide()

        # Reset standardbuttons and their functions and labels
        # self.dlg.btnCancel.clicked.disconnect(self.stopProcessing)
        self.dlg.buttonBox.rejected.disconnect(self.stopProcessing)
        ## QObject.connect(self.dlg.buttonBox, pyqtSignal("rejected()"), self.dlg.reject)
        self.dlg.buttonBox.rejected.connect(self.dlg.reject)
        self.dlg.btnCancel.hide()
        self.dlg.btnClose.show()
        QApplication.restoreOverrideCursor()
        self.dlg.exportButton.setEnabled(True)

        self.arret = False

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
                else:
                    QSettings().setValue('/UI/lastSaveAsImageDir', folder)

            # Reset the GUI
            self.restoreGui()

    def exportCompo(self, cView, folder, title, extension):
        """Function that sets how to export files."""

        #self.msgWMSWarning(cView)

        myAtlas = cView.atlas()

        # Prepare the layout if it has an atlas
        if myAtlas.enabled():
            myAtlas.beginRender()

        # Set page progressbar maximum value
        # only possible for atlases once the rendering has begun, reason why it's placed here
        if myAtlas.enabled():
            if extension == '.pdf':
                maxIteration = myAtlas.count()
            else:
                maxIteration = myAtlas.count() * cView.pageCollection().pageCount()
        else:
            if extension == '.pdf': maxIteration = 1
            else:
                maxIteration = cView.pageCollection().pageCount()
        print(maxIteration)
        self.dlg.pageBar.setValue(0)
        self.dlg.pageBar.setMaximum(maxIteration)

        # Do the export process
        exporter = QgsLayoutExporter(cView)
        if myAtlas.enabled():
            #for i in range(0, myAtlas.count()):
                #if self.arret: break
            # process input events
            QCoreApplication.processEvents()

            # if single file export is required (only compatible with pdf, yet)
            if myAtlas.layout().customProperty('singleFile') and extension == '.pdf':
                success = exporter.exportToPdf(myAtlas, os.path.join(folder, title + '.pdf'), QgsLayoutExporter.PdfExportSettings())

            else: #If instead multiple files will be output
            
                # Check if there's a valid expression for filenames,
                # and otherwise inform that a default one will be used and set it using the layout name.
                # replacement is failing at the moment
                if len(myAtlas.filenameExpression()) == 0:
                    self.iface.messageBar().pushMessage(
                        self.tr(u'Empty filename expression'),
                        self.tr(u'The print layout "{}" has an empty output filename expression. {}_$feature is used as default.').format(title, title),
                        level = Qgis.Warning
                        )
                    myAtlas.setFilenameExpression(u"'{}_'||@atlas_pagename".format(title))

                current_fileName = myAtlas.filenameExpression()
                #print ('current_fileName:', current_fileName)

               #export atlas to multiple pdfs
                if extension =='.pdf':
                    success = exporter.exportToPdfs(myAtlas, os.path.join(folder, current_fileName), QgsLayoutExporter.PdfExportSettings())

                # export atlas to svg format
                elif extension =='.svg':
                    success = exporter.exportToSvg(myAtlas, os.path.join(folder, current_fileName), QgsLayoutExporter.SvgExportSettings())

                # export atlas to image format
                else:
                    exporter.exportToImage(myAtlas, os.path.join(folder, current_fileName), extension, QgsLayoutExporter.ImageExportSettings())
            #increase progressbar
            self.pageProcessed()

            myAtlas.endRender()

            # Reset atlas mode to its original value and, if needed, atlas map
            # was working in QGIS 2 but not yet in 3.1 (see report at https://issues.qgis.org/issues/19021

        # if the composition has no atlas
        else:
            success = False
            if extension == '.pdf':
                success = exporter.exportToPdf(os.path.join(folder, title + '.pdf'), QgsLayoutExporter.PdfExportSettings())

            elif extension == '.svg':
                success = exporter.exportToSvg(os.path.join(folder, title + '.svg'), QgsLayoutExporter.SvgExportSettings())

            else:
                success = exporter.exportToImage(os.path.join(folder, title + extension), QgsLayoutExporter.ImageExportSettings())
            ## QMessageBox.information(None, "Resultat", "Ret : " + str(success), QMessageBox.Ok)
            self.pageProcessed()


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

    def renameDialog(self):
        """Name the dialog with the project's title or filename."""

        prj = QgsProject.instance()

        if prj.title() != '':
            self.dlg.setWindowTitle(u'Maps Printer - {}'.format(prj.title()))
        else:
            self.dlg.setWindowTitle(u'Maps Printer - {}'.format(
                os.path.splitext(os.path.split(prj.fileName())[1])[0]))

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
            self.renameDialog()
            # show the dialog and fill the widget the first time
            if not self.dlg.isVisible():
                self.populateLayoutList(self.dlg.layoutList)
                self.dlg.show()
            else:
                # if the dialog is already opened but not on top of other windows
                # Put it on the top of all other widgets,
                self.dlg.activateWindow()
                # update the list of layouts and keep the previously selected options in the dialog
                self.refreshList()
