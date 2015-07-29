# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Show, hide and export several print composers to pdf or image file format in one click
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
import os.path
import sys
import errno
import tempfile

from PyQt4.QtCore import QSettings, QTranslator, qVersion, SIGNAL,\
    QCoreApplication, QFileInfo, QDir, QUrl, QTimer, Qt, QObject 
from PyQt4.QtGui import QAction, QIcon, QListWidgetItem, QFileDialog, QDialogButtonBox, \
    QPainter, QPrinter, QMenu, QCursor, QDesktopServices, QMessageBox, QApplication

from qgis.core import *
from qgis.gui import QgsMessageBar

# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from maps_printer_dialog import MapsPrinterDialog


class MapsPrinter:
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
                              self.tr(u'Export multiple print composers'),
                              self.iface.mainWindow()
                              )
        self.helpAction = QAction(QIcon(':/plugins/MapsPrinter/icons/about.png'),
                                  self.tr(u'Help'), self.iface.mainWindow()
                                  )

        # Connect actions to context menu
        self.dlg.composerList.customContextMenuRequested.connect(self.context_menu)

        # Connect the action to the run method
        self.action.triggered.connect(self.run)
        self.helpAction.triggered.connect(self.showHelp)
        self.dlg.buttonBox.helpRequested.connect(self.showHelp)

        # Connect to the export button to do the real work
        self.dlg.exportButton.clicked.connect(self.saveFile)

        # Connect the signal to set the "select all" checkbox behaviour
        self.dlg.checkBox.clicked.connect(self.on_selectAllcbox_changed)
        self.dlg.composerList.itemChanged.connect(self.on_composercbox_changed)

        # Connect to the browser button to select export folder
        self.dlg.browser.clicked.connect(self.browseDir)

        # Connect the action to the updater button so you can update the list of composers
        # will be useless if i can synchronise with the composer manager widgetlist
        self.dlg.updater.clicked.connect(self.refreshList)
        # refresh the composer list when a composer is created or deleted (miss renaming case)
        # self.iface.composerAdded.connect(self.refreshList)
        # self.iface.composerWillBeRemoved.connect(self.refreshList, Qt.QueuedConnection)
        # self.iface.composerRemoved.connect(self.refreshList)

        # Connect some actions to manage dialog status while another project is opened
        self.iface.newProjectCreated.connect(self.dlg.close)
        self.iface.projectRead.connect(self.renameDialog)
        self.iface.projectRead.connect(self.refreshList)

        # Add toolbar button and menu item0
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u'&Maps Printer', self.action)
        self.iface.addPluginToMenu(u'&Maps Printer', self.helpAction)

        # Hide the Cancel button at the opening
        self.dlg.btnCancel = self.dlg.buttonBox.button(QDialogButtonBox.Cancel)
        self.dlg.btnCancel.hide()
        self.dlg.btnClose = self.dlg.buttonBox.button(QDialogButtonBox.Close)


    def context_menu(self):
        """Add context menu fonctions."""

        menu = QMenu(self.dlg.composerList)
        menu.addAction(self.tr(u'Check...'), self.actionCheckComposer)
        menu.addAction(self.tr(u'Uncheck...'), self.actionUncheckComposer)
        menu.addSeparator()
        menu.addAction(self.tr(u'Show...'), self.actionShowComposer)
        menu.addAction(self.tr(u'Close...'), self.actionHideComposer)
        menu.exec_(QCursor.pos())

    def actionCheckComposer(self):
        for item in self.dlg.composerList.selectedItems():
            item.setCheckState(Qt.Checked)

    def actionUncheckComposer(self):
        for item in self.dlg.composerList.selectedItems():
            item.setCheckState(Qt.Unchecked)

    def actionShowComposer(self):
        selected = {item.text() for item in self.dlg.composerList.selectedItems()}
        for cView in self.iface.activeComposers():
            if cView.composerWindow().windowTitle() in selected:
                cView.composerWindow().show()
                cView.composerWindow().activate()

    def actionHideComposer(self):
        selected = {item.text() for item in self.dlg.composerList.selectedItems()}
        for cView in self.iface.activeComposers():
            if cView.composerWindow().windowTitle() in selected:
                cView.composerWindow().hide()

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
        """Function that finds new composer to be added to the list."""

        nameCompo = cView.composerWindow().windowTitle()
        if not w.findItems(nameCompo, Qt.MatchExactly):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setText(nameCompo)
            w.addItem(item)

    def populateComposerList(self, w):
        """Called to populate the composer list when opening a new dialog."""

        # Get  all the composers in a previously emptied list
        w.clear()
        # Populate export format listbox
        self.listFormat(self.dlg.formatBox)
        # Ensure the "select all" box is unchecked
        self.dlg.checkBox.setChecked(False)

        for cView in self.iface.activeComposers():
            self.getNewCompo(w, cView)
        w.sortItems()

    def refreshList(self):
        """When updating the list of composers,
        the state of composers already listed is kept if they are still in the project
        so just add new composers and erase those deleted/renamed."""

        currentComposers = []
        i,j = 0,0

        if len(self.iface.activeComposers()) == 0 and self.dlg.isVisible():
            self.iface.messageBar().pushMessage( 'Maps Printer : ',
                self.tr(u'dialog shut because no more print composer in the project.'),
                level = QgsMessageBar.INFO, duration = 5
                )
            self.dlg.close()
        else:
            # Get the current list of composers
            while i < len(self.iface.activeComposers()):
            # for i in range(len(self.iface.activeComposers())):
                currentComposers.append(
                    self.iface.activeComposers()[i].composerWindow().windowTitle()
                    )
                i += 1

            # Erase deleted (or renamed) composers
            while j < self.dlg.composerList.count():
                if self.dlg.composerList.item(j).text() not in currentComposers:
                    self.dlg.composerList.takeItem(j)
                else:
                    j += 1

            # Add new composers to the list
            for cView in self.iface.activeComposers():
                self.getNewCompo(self.dlg.composerList, cView)
            self.dlg.composerList.sortItems()

            # And check if all the remained rows are checked
            # (called to display coherent check boxes). Better way?
            self.on_composercbox_changed()

    def on_selectAllcbox_changed(self):
        """When changing the state of the "select all" checkbox,
        do the same to the composers listed below.
        """

        etat = self.dlg.checkBox.checkState()
        for rowList in range(0, self.dlg.composerList.count()):
            self.dlg.composerList.item(rowList).setCheckState(etat)

    def listCheckedComposer(self):
        """Get all the boxes and texts checked in the list."""

        global rowsChecked

        # rowsChecked = [rowList for rowList in range(0, self.dlg.composerList.count()) \
            # if self.dlg.composerList.item(rowList).checkState() == Qt.Checked]
            #
        # rowsChecked = {(rowList, self.dlg.composerList.item(rowList).text()) \
            # for rowList in range(0, self.dlg.composerList.count()) \
            # if self.dlg.composerList.item(rowList).checkState() == Qt.Checked}
            #
        # rowsChecked = {rowList:self.dlg.composerList.item(rowList).text() for rowList in range(0, self.dlg.composerList.count()) \
            # if self.dlg.composerList.item(rowList).checkState() == Qt.Checked}
            #
        rowsChecked = {
            self.dlg.composerList.item(rowList).text(): rowList for rowList in range(
                0, self.dlg.composerList.count()
                ) if self.dlg.composerList.item(rowList).checkState() == Qt.Checked
        }

        return rowsChecked

    def on_composercbox_changed(self):
        """When at least one of the composers listed is unchecked,
        then the "select All" checkbox should be unchecked too.
        """

        self.listCheckedComposer()
        if len(rowsChecked) == self.dlg.composerList.count():
            self.dlg.checkBox.setChecked(True)
        else:
            self.dlg.checkBox.setChecked(False)

    def listFormat(self, box):
        """List all the file formats used in export mode."""

        box.clear()
        list1 = [
            '',
            self.tr(u'PDF format (*.pdf *.PDF)'),
            self.tr(u'JPG format (*.jpg *.JPG)'),
            self.tr(u'JPEG format (*.jpeg *.JPEG)'),
            self.tr(u'TIF format (*.tif *.TIF)'),
            self.tr(u'TIFF format (*.tiff *.TIFF)'),
            self.tr(u'PNG format (*.png *.PNG)'),
            self.tr(u'BMP format (*.bmp *.BMP)'),
            self.tr(u'ICO format (*.ico *.ICO)'),
            self.tr(u'PPM format (*.ppm *.PPM)'),
            self.tr(u'XBM format (*.xbm *.XBM)'),
            self.tr(u'XPM format (*.xpm *.XPM)')
            ]

        box.addItems(list1)
        box.insertSeparator(2)

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

        missed = []
        for (x, y) in d:
            if not y: # if the second value is null, 0 or empty
                # outline the first item in red
                x.setStyleSheet('border-style: outset; border-width: 1px; border-color: red')
                # retrieve the missing value
                missed.append(y)
            else:
                x.setStyleSheet('border-color: palette()')
        #[missed.append(x[1]) for x in d if not x[1]]
        # and if there are missing values, show error message and stop execution
        if missed:
            self.iface.messageBar().pushMessage('Maps Printer : ',
                self.tr(u'Please consider filling the mandatory field(s) outlined in red.'),
                level = QgsMessageBar.CRITICAL,
                duration = 5)
            return False
        # otherwise let's proceed the export
        else:
            return True

    def initGuiButtons(self):
        """Init the GUI to follow export processes."""

        self.dlg.printBar.setValue(0)
        self.dlg.printBar.setMaximum(len(rowsChecked))
        self.dlg.exportButton.setEnabled(False)

        # Activate the Cancel button to stop export process, and hide the Close button
        QObject.disconnect(self.dlg.buttonBox, SIGNAL("rejected()"), self.dlg.reject)
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
        
        # Reset standardbuttons and their functions and labels
        # self.dlg.btnCancel.clicked.disconnect(self.stopProcessing)
        self.dlg.buttonBox.rejected.disconnect(self.stopProcessing)
        QObject.connect(self.dlg.buttonBox, SIGNAL("rejected()"), self.dlg.reject)
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
                self.tr(u'The print composer "{}" has an empty filename '\
                    'pattern. {}_$feature is used as default.'
                    ).format(self.title, self.title),
            level = QgsMessageBar.WARNING
            )

    def saveFile(self):
        """Check if the conditions are filled to export file(s) and
        export the checked composers to the specified file format."""

        # Ensure list of print composers is up to date
        # (user can launch export without having previously refreshed the list)
        # will not be needed if the list can automatically be refreshed
        self.refreshList()
        # retrieve the selected composers list
        self.listCheckedComposer()
        # get the output file format and directory
        extension = self.setFormat(self.dlg.formatBox.currentText())
        folder = self.dlg.path.text()
        # Are there at least one composer checked,
        # an output folder indicated and an output file format chosen?
        d = {
            # the composer list and the number of checked composers
            (self.dlg.composerList, len(rowsChecked)),
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

            for cView in self.iface.activeComposers():
                title = cView.composerWindow().windowTitle()
                if title in rowsChecked:
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
                    self.dlg.composerList.item(
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
                    level = QgsMessageBar.INFO, duration = 10
                    )
            # or when export ended completely
            else:
                self.iface.messageBar().pushMessage(
                    self.tr(u'Operation finished : '),
                    self.tr(u'The maps from {} compositions have been '\
                        'exported to "{}".'
                        ).format(x, folder),
                    level = QgsMessageBar.INFO, duration = 5
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

        printer = QPrinter()
        painter = QPainter()
        if extension == '.pdf':
            cView.composition().setUseAdvancedEffects(False)
        else:
            cView.composition().setUseAdvancedEffects(True)

        myAtlas = cView.composition().atlasComposition()

        # Prepare the composition if it has an atlas
        if myAtlas.enabled():
            myAtlas.beginRender()
            previous_mode = cView.composition().atlasMode()
            cView.composition().setAtlasMode(QgsComposition.ExportAtlas)
            # If there's no pattern for filename, inform that a default one will be used and set it
            if len(myAtlas.filenamePattern()) == 0:
                self.iface.messageBar().pushMessage(
                    self.tr(u'Empty filename pattern'),
                    self.tr(u'The print composer "{}" has an empty filename pattern. {}_$feature is used as default.').format(title, title),
                    level = QgsMessageBar.WARNING
                    )
                myAtlas.setFilenamePattern(u"'{}_'||$feature".format(title))

        # Set page progressbar maximum value
        # possible for atlases once the rendering has begun
        if myAtlas.enabled():
            if extension == '.pdf':
                maxpages = myAtlas.numFeatures()
            else:
                maxpages = myAtlas.numFeatures() * cView.composition().numPages()
        else:
            if extension == '.pdf': maxpages = 1
            else: 
                maxpages = cView.composition().numPages()
        self.dlg.pageBar.setValue(0)
        self.dlg.pageBar.setMaximum(maxpages)
        
        # Do the export process
        if myAtlas.enabled():
            for i in range(0, myAtlas.numFeatures()):
                if self.arret: break
                # process input events
                QCoreApplication.processEvents()

                myAtlas.prepareForFeature(i)
                current_fileName = myAtlas.currentFilename()
                # export atlas to pdf format
                if extension == '.pdf':
                    if myAtlas.singleFile():
                        cView.composition().beginPrintAsPDF(printer, os.path.join(folder, title + '.pdf'))
                        cView.composition().beginPrint(printer)
                        printReady = painter.begin(printer)
                        if i > 0:
                            printer.newPage()
                        cView.composition().doPrint(printer, painter)
                    else:
                        cView.composition().exportAsPDF(os.path.join(folder, current_fileName + '.pdf'))
                    #increase progressbar
                    self.pageProcessed()

                # export atlas to image format
                else:
                    self.printToRaster(cView, folder, current_fileName, extension)
            myAtlas.endRender()
            painter.end()
            # Reset atlas mode to its original value
            cView.composition().setAtlasMode(previous_mode)

        # if the composition has no atlas
        else:
            if extension == '.pdf':
                cView.composition().exportAsPDF(os.path.join(folder, title + '.pdf'))
            else:
                self.printToRaster(cView, folder, title, extension)
            self.pageProcessed()

    def printToRaster(self, cView, folder, name, ext):
        """Export to image raster."""

        for numpage in range(0, cView.composition().numPages()):
            if self.arret:
                break
            # process input events
            QCoreApplication.processEvents()

            # managing multiple pages in the composition
            imgOut = cView.composition().printPageAsRaster(numpage)
            if numpage == 0:
                imgOut.save(os.path.join(folder, name + ext))
            else:
                imgOut.save(os.path.join(folder, name + '_'+ str(numpage + 1) + ext))
            self.pageProcessed()

    def renameDialog(self):
        """Name the dialog with the project's title or filename."""
        
        prj = QgsProject.instance()
        # if QgsProject.instance == None:
            # self.dlg.reject()
            # return

        if prj.title() <> '':
            self.dlg.setWindowTitle(u'Maps Printer - {}'.format(prj.title()))
        else:
            self.dlg.setWindowTitle(u'Maps Printer - {}'.format(
                os.path.splitext(os.path.split(prj.fileName())[1])[0]))

    def run(self):
        """Run method that performs all the real work."""

        # when no composer is in the project, display a message about the lack of composers and exit
        if len(self.iface.activeComposers()) == 0:
            self.iface.messageBar().pushMessage(
                'Maps Printer : ',
                self.tr(u'There is currently no print composer in the project. '\
                'Please create at least one before running this plugin.'),
                level = QgsMessageBar.INFO, duration = 5
                )
            self.dlg.close()
        else:
            self.renameDialog()
            # show the dialog and fill the widget the first time
            if not self.dlg.isVisible():
                self.populateComposerList(self.dlg.composerList)
                self.dlg.show()
            else:
                # if the dialog is already opened but not on top of other windows
                # Put it on the top of all other widgets,
                self.dlg.activateWindow()
                # update the list of composers and keep the previously selected options in the dialog
                self.refreshList()

