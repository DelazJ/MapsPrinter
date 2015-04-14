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

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QFileInfo, QDir, QUrl
from PyQt4.QtGui import QAction, QIcon, QListWidgetItem, QFileDialog, QMessageBox,\
    QPainter, QPrinter, QMenu, QProgressDialog, QCursor, QDesktopServices, QApplication, QCursor
    #QWidget #QFrame #QListView #QAbstractItemView #QListWidget

from qgis.core import *
from qgis.gui import QgsMessageBar
# Initialize Qt resources from file resources.py
import resources_rc
import errno
import time
# Import the code for the dialog
from maps_printer_dialog import MapsPrinterDialog
from mpaboutWindow import mpAboutWindow


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
        self.action = QAction(QIcon(":/plugins/MapsPrinter/icons/icon.png"),
                              self.tr('Export multiple print composers'),
                              self.iface.mainWindow()
                              )
        self.helpAction = QAction(QIcon(":/plugins/MapsPrinter/icons/about.png"),
                                  self.tr('Help'), self.iface.mainWindow()
                                  )

        
        # Connect actions to context menu
        self.dlg.composerList.customContextMenuRequested.connect(self.context_menu)

        # Connect the action to the run method
        self.action.triggered.connect(self.run)
        # self.helpAction.triggered.connect(self.showHelp)
        self.helpAction.triggered.connect(self.help2)
        self.dlg.buttonBox.helpRequested.connect(self.help2)
        # self.dlg.buttonBox.helpRequested.connect(self.showPluginHelp)

        # Connect the signal to set the "select all" checkbox behaviour 
        self.dlg.checkBox.clicked.connect(self.on_selectAllcbox_changed)
        self.dlg.composerList.itemChanged.connect(self.on_composercbox_changed)

        # Connect to the export button to do the real work
        self.dlg.exportButton.clicked.connect(self.saveFile)

        # Connect to the browser button so you can select directory
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
        self.iface.projectRead.connect(self.refreshList)        

        # Add toolbar button and menu item0
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Maps Printer", self.action)
        self.iface.addPluginToMenu(u"&Maps Printer", self.helpAction)
            
    def context_menu(self):
        """ Add context menu fonctions """
        menu = QMenu(self.dlg.composerList)
        menu.addAction(self.tr("Check selection"), self.actionCheckComposer)
        menu.addAction(self.tr("Uncheck selection"), self.actionUncheckComposer)
        menu.addSeparator()
        menu.addAction(self.tr("Show composer(s)..."),self.actionShowComposer)
        menu.addAction(self.tr("Close composer(s)..."),self.actionHideComposer)
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
            if cView.composerWindow().windowTitle() in selected :
                cView.composerWindow().show()
                cView.composerWindow().activate()

    def actionHideComposer(self):
        selected = {item.text() for item in self.dlg.composerList.selectedItems()}
        for cView in self.iface.activeComposers() :
            if cView.composerWindow().windowTitle() in selected :
                cView.composerWindow().hide()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu(u"&Maps Printer", self.action)
        self.iface.removePluginMenu(u"&Maps Printer", self.helpAction)
        self.iface.removeToolBarIcon(self.action)           

    def getNewCompo(self, w, cView):
        """Function that finds new composer to be added to the list """
        nameCompo = cView.composerWindow().windowTitle()
        if not w.findItems(nameCompo, Qt.MatchExactly):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setText(nameCompo)
            w.addItem(item)

    def populateComposerList(self, w):
        """ Called to populate the composer list when opening a new dialog"""
        # Get  all the composers in a previously emptied list
        w.clear() 
        # Populate export format listbox
        self.listFormat(self.dlg.formatBox)
        # Ensure the "select all" box is unchecked
        self.dlg.checkBox.setChecked(False)

        for cView in self.iface.activeComposers():
            self.getNewCompo(w, cView)
        w.sortItems()
        self.dlg.show()

    def addNewCompo(self):
        pass
    
    def removeOldCompo(self):
        pass

    def refreshList(self):
        """ When updating the list of composers, the state of composers already listed is kept if they are still in the project
        so just add new composers and erase those deleted/renamed
        """
        currentComposers = []
        i,j = 0,0

        if len(self.iface.activeComposers()) == 0:
            self.iface.messageBar().pushMessage(
                'Maps Printer : ',
                self.tr('dialog shut because no more print composer in the project.'),
                level = QgsMessageBar.INFO, duration = 5
                )
            self.dlg.close()
        else :
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
        """ When changing the state of the "select all" checkbox, 
        do the same to the composers listed below 
        """
        etat = self.dlg.checkBox.checkState()
        for rowList in range(0, self.dlg.composerList.count()):
            self.dlg.composerList.item(rowList).setCheckState(etat)

    def listCheckedComposer(self): 
        """ Get all the boxes and textes checked in the list."""
        global rowsChecked

        # rowsChecked = [rowList for rowList in range(0, self.dlg.composerList.count()) \
            # if self.dlg.composerList.item(rowList).checkState() == Qt.Checked
            # ]
        # rowsChecked = {(rowList, self.dlg.composerList.item(rowList).text()) \
            # for rowList in range(0, self.dlg.composerList.count()) \
            # if self.dlg.composerList.item(rowList).checkState() == Qt.Checked
            # }
        # rowsChecked = {rowList:self.dlg.composerList.item(rowList).text() for rowList in range(0, self.dlg.composerList.count()) \
            # if self.dlg.composerList.item(rowList).checkState() == Qt.Checked
            # }
        rowsChecked = {self.dlg.composerList.item(rowList).text():rowList for rowList in range(0, self.dlg.composerList.count()) \
            if self.dlg.composerList.item(rowList).checkState() == Qt.Checked
            }

        return rowsChecked

    def on_composercbox_changed(self):
        """ When at least one of the composers listed is unchecked, 
        then the "select All" checkbox should be unchecked too 
        """
        self.listCheckedComposer()
        if len(rowsChecked) == self.dlg.composerList.count():
            self.dlg.checkBox.setChecked(True)
        else:
            self.dlg.checkBox.setChecked(False)

    def listFormat(self, box):
        """ List all the file formats used in export mode"""
        box.clear()
        list1 = [
            '',
            self.tr('PDF format (*.pdf *PDF)'),
            self.tr('JPG format (*.jpg *JPG)'),
            self.tr('JPEG format (*.jpeg *JPEG)'),
            self.tr('TIF format (*.tif *TIF)'),
            self.tr('TIFF format (*.tiff *TIFF)'),
            self.tr('PNG format (*.png *PNG)'),
            self.tr('BMP format (*.bmp *BMP)'),
            self.tr('ICO format (*.ico *ICO)'),
            self.tr('PPM format (*.ppm *PPM)'),
            self.tr('XBM format (*.xbm *XBM)'),
            self.tr('XPM format (*.xpm *XPM)')
            ]

        box.addItems(list1) 
        box.insertSeparator(2)

    def setFormat(self, value):
        try:
            f = value.split()[2].strip('(*')
            # f = value.split('*')[1].strip()
        except:
            f = ''
        return f

    def checkFilled(self, d):
        """Check if all the mandatory informations are filled"""
        missed = []
        for (x,y) in d:
            if not y: # if the second value is null, 0 or empty
                # outline the first item in red
                x.setStyleSheet(" border-style: outset; border-width: 1px; border-color: red")
                # retrieve the missing value        
                missed.append(y)
            else:
                x.setStyleSheet("border-color: palette()")
        #[missed.append(x[1]) for x in d if not x[1]]
        # and if there are missing values, show error message and stop execution
        if missed: 
            self.iface.messageBar().pushMessage('Maps Printer : ', 
                self.tr('Please consider filling the mandatory field(s) outlined in red.'), 
                level = QgsMessageBar.CRITICAL, 
                duration = 5)
            return False
        # otherwise let's proceed the export
        else:
            return True

    def saveFile(self):
        """Check if the conditions are filled to export file(s) and 
        export the checked composers to the specified file format 
        """
        # Ensure list of print composers is up to date (user can launch export without having previously refreshed the list)
        # will not be needed if the list can automatically be refreshed
        self.refreshList()
        # retrieve the selected composers list
        self.listCheckedComposer()
        # get the output file format and directory
        ext = self.setFormat(self.dlg.formatBox.currentText())
        folder = self.dlg.path.text()
        # Is there at least one composer checked, an output folder indicated and an output file format chosen?       
        d = {
            (self.dlg.composerList, len(rowsChecked)), # the composer list and the number of checked composers
            (self.dlg.path, folder), # the folder box and its text
            (self.dlg.formatBox, ext) # the format list and its choice
            }

        # check if all the mandatory informations are filled and if ok, export
        if self.checkFilled(d) and self.checkFolder(folder):
            x = len(rowsChecked)
            i = 0
            progress = QProgressDialog( self.tr( "Exporting maps..." ), self.tr( "Abort" ), 0, x, self.dlg )
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.setOverrideCursor( Qt.BusyCursor )

            for cView in self.iface.activeComposers ():
                title = cView.composerWindow().windowTitle()

                if title in rowsChecked :
                    progress.setValue( i )
                    progress.setLabelText(self.tr( "Exporting maps from {}...".format(title) ))
                    # process input events in order to allow aborting
                    QApplication.processEvents()
                    if progress.wasCanceled():
                        break
                    self.exportCompo(cView, ext, folder)
                    i = i + 1
                    # progress.setValue( i )
                    self.dlg.composerList.item(rowsChecked[title]).setCheckState(Qt.Unchecked)
            progress.setValue(x)
            QApplication.restoreOverrideCursor()
            # self.dlg.close()

            # show a successful message bar
            if i == x :
                self.iface.messageBar().pushMessage(
                    self.tr('Operation finished : '),
                    self.tr('{} compositions have been exported!'.format(x)), 
                    level = QgsMessageBar.INFO, duration = 5
                    )
            # or not
            else :
                self.iface.messageBar().pushMessage(
                    self.tr('Operation interrupted : '),
                    self.tr('{} compositions on {} have been exported!'.format(i, x)), 
                    level = QgsMessageBar.INFO, duration = 5
                    )

    def exportCompo(self, cView, extension, location):
        """ function that sets how to export files """
        printer = QPrinter()
        painter = QPainter()
        title = cView.composerWindow().windowTitle()

        if extension == ".pdf" :
            cView.composition().setUseAdvancedEffects( False )
        else:
            cView.composition().setUseAdvancedEffects( True )

        myAtlas = cView.composition().atlasComposition()
        # if the composition has an atlas
        if myAtlas.enabled():
            myAtlas.beginRender()
            previous_mode = cView.composition().atlasMode()
            cView.composition().setAtlasMode(QgsComposition.ExportAtlas)
            if len(myAtlas.filenamePattern()) == 0:
                QMessageBox.warning( None, self.tr( "Empty filename pattern" ),
                    self.tr("The print composer '{}' has an empty filename pattern. A default one will be used.".format(title)), 
                    QMessageBox.Ok, QMessageBox.Ok  )
                myAtlas.setFilenamePattern( "'{}_'||$feature".format(title) )

            for i in range(0, myAtlas.numFeatures()):
                myAtlas.prepareForFeature( i )
                current_fileName = myAtlas.currentFilename()
                # export atlas to pdf format
                if extension == ".pdf":
                    if myAtlas.singleFile():
                        cView.composition().beginPrintAsPDF(printer, os.path.join(location, title + ".pdf"))
                        cView.composition().beginPrint(printer)
                        printReady =  painter.begin(printer)
                        if i > 0:
                            printer.newPage()
                        cView.composition().doPrint( printer, painter )
                    else:
                        cView.composition().exportAsPDF(os.path.join(location, current_fileName + ".pdf"))
                # export atlas to image format
                else:
                    self.printToRaster(cView, location, current_fileName, extension)
            myAtlas.endRender()
            painter.end()
            # set atlas mode to its original value
            cView.composition().setAtlasMode(previous_mode )

        # if the composition has no atlas
        else:
            if extension == ".pdf":  
                cView.composition().exportAsPDF(os.path.join(location, title + ".pdf" ))                        
            else:
                self.printToRaster(cView, location, title, extension)

        """
        if extension == ".pdf":
            printer = QPrinter()
            painter = QPainter()
            if myAtlas.enabled():
                myAtlas.beginRender()
                previous_mode = cView.composition().atlasMode()
                cView.composition().setAtlasMode(QgsComposition.ExportAtlas)
                if myAtlas.singleFile():
                    cView.composition().beginPrintAsPDF(printer, os.path.join(location, title + ".pdf"))
                    cView.composition().beginPrint(printer)
                for i in range(0, myAtlas.numFeatures()):
                    myAtlas.prepareForFeature( i )
                    current_fileName = myAtlas.currentFilename()
                    if myAtlas.singleFile():
                        if i > 0:
                            printer.newPage()
                        cView.composition().doPrint( printer, painter )
                    else:    #fonctionne
                        cView.composition().exportAsPDF(os.path.join(location, current_fileName + ".pdf"))
            
        else:
            for i in range(0, myAtlas.numFeatures()):
                self.printToRaster(cView, location, current_fileName, extension)
        """    

    def printToRaster(self, cView, folder, title, ext):
        """Export to image raster"""
        for numpage in range(0, cView.composition().numPages()):
            # managing multiple pages in the composition
            imgOut = cView.composition().printPageAsRaster(numpage)
            if numpage == 0:
                imgOut.save(os.path.join(folder, title + ext))
            else:
                imgOut.save(os.path.join(folder, title + "_"+ str(numpage + 1) + ext))

    def browseDir(self):
        """ Open the browser so the user selects the output directory """
        fileDialog = QFileDialog.getExistingDirectory(
            None, 
            "",
            self.dlg.path.text(),
            QFileDialog.ShowDirsOnly,
            # QFileDialog.DontResolveSymlinks
            ) 

        if fileDialog == '':
            self.dlg.path.setText(self.dlg.path.text())
        else:
            self.dlg.path.setText(fileDialog)

    def checkFolder(self, outputDir):
        """ test directory (if it exists and is writable)"""
        try:
            os.makedirs( outputDir )
            return True
        except OSError as e :    
            # if the directory already exists then ok
            if e.errno == errno.EEXIST :
                return True
                # QMessageBox.warning( None, self.tr( "Unable to create the directory" ),
                    # self.tr( "directory already exists{}".format(e) ), 
                    # QMessageBox.Ok, QMessageBox.Ok  )
            # if the directory is not writable, choose another one
            if e.errno == errno.EACCES :
                QMessageBox.warning( None, self.tr( "Unable to access the directory" ),
                    self.tr( "You don't have rights to write in this folder. Please, select another folder!" ), 
                    QMessageBox.Ok, QMessageBox.Ok  )
                self.browseDir()

    def showHelp(self):
        """ Function that shows the help dialog """
        self.aboutWindow = mpAboutWindow()

    def help2(self):
        # help_file = os.path.join(os.path.dirname(__file__), "help/build/html", "index.html")
        # QDesktopServices.openUrl(QUrl.fromLocalFile(helpfile))
        help_file = "file:///"+ self.plugin_dir + "/help/build/html/index.html"
        QDesktopServices.openUrl(QUrl(help_file))

    def run(self):
        """ Run method that performs all the real work """
        # when no composer is in the project, display a message about the lack of composers and exit
        if len(self.iface.activeComposers()) == 0:
            self.iface.messageBar().pushMessage(
                'Maps Printer : ',
                self.tr('There is currently no print composer in the project. Please create at least one before running this plugin.'), 
                level = QgsMessageBar.INFO, duration = 5
                )
            self.dlg.close()
        else:
            # Name the dialog with the project's title or filename
            if QgsProject.instance().title() <> '' :
                self.dlg.setWindowTitle("Maps Printer - {}".format( QgsProject.instance().title()))
            else :    
                self.dlg.setWindowTitle("Maps Printer - {}".format(
                    os.path.splitext(os.path.split(QgsProject.instance().fileName())[1])[0]))

            # show the dialog and fill the widget the first time
            if not self.dlg.isVisible():
                self.populateComposerList(self.dlg.composerList)
            else: 
                # if the dialog is already opened but not at top of the screen
                # Put it at the top of all other widgets,
                # update the list of composers and keep the previously selected options in the dialog
                self.dlg.activateWindow()
                self.refreshList()

            # for elem in self.dlg.children():
                # try:
                    # # if elem.type() == QWidget():
                        # elem.setStyleSheet("border-color: palette()")
                # except:
                    # pass


"""
OTHER SITUATIONS TO DEAL WITH:
- Known issues: 
    - shouldExportPage ? 
- Improvements : 
    - when refreshing, keep in the list the renamed composer(s) and its checkbox state. Currently, they are erased from the list and appended with their new name.
    - check if file already exist and ask how to deal with
    - it would be great to find a way to automatically refreshList whenever the dialog is set to foreground
    - Implement svg format export
    - 
"""