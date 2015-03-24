# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Exports simultaneously several print composers to pdf or image file format
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
    QPainter, QPrinter, QMenu, QProgressBar, QProgressDialog, QCursor, QDesktopServices 

from qgis.core import *
from qgis.gui import QgsMessageBar
# Initialize Qt resources from file resources.py
import resources_rc
import errno
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

        # global wdgt
        # wdgt = self.dlg.composerList
        
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

        global wdgt
        wdgt = self.dlg.composerList
        
        # Connect actions to context menu
        wdgt.customContextMenuRequested.connect(self.context_menu)

        # Connect the action to the run method
        self.action.triggered.connect(self.run)
        self.helpAction.triggered.connect(self.showHelp)
        self.dlg.buttonBox.helpRequested.connect(self.help2)
        # self.dlg.buttonBox.helpRequested.connect(self.showPluginHelp)
        
        # Connect the signal to set the "select all" checkbox behaviour 
        self.dlg.checkBox.clicked.connect(self.on_selectAllcbox_changed)
        wdgt.itemChanged.connect(self.on_composercbox_changed)
        
        # Connect to the export button to do the real work
        self.dlg.exportButton.clicked.connect(self.saveFile)
        
        # Connect to the browse button so you can select directory
        self.dlg.browse.clicked.connect(self.browseDir)

        # Connect the action to the updater button so you can update the list of composers
        self.dlg.updater.clicked.connect(self.refreshList)
        
        # Connect some actions to manage dialog status while another project is opened
        self.iface.newProjectCreated.connect(self.dlg.close)
        self.iface.projectRead.connect(self.resetDialog)
        
        
        # Add toolbar button and menu item0
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Maps Printer", self.action)
        self.iface.addPluginToMenu(u"&Maps Printer", self.helpAction)

    def resetDialog(self):
        if len(self.iface.activeComposers()) == 0 :
            self.dlg.close()
        else:
            self.refreshList()
            
    def context_menu(self):
        """ Add context menu fonctions """
        menu = QMenu(wdgt)
        menu.addAction("Check selection", self.actionCheckComposer)
        menu.addAction("Uncheck selection", self.actionUncheckComposer)
        menu.addSeparator()
        menu.addAction("Show composer(s)...",self.actionShowComposer)
        menu.addAction("Hide composer(s)...",self.actionHideComposer)
        menu.exec_(QCursor.pos()) 
        
    def actionCheckComposer(self):
        for item in self.dlg.composerList.selectedItems():
            item.setCheckState(Qt.Checked)
        
    def actionUncheckComposer(self):
        for item in self.dlg.composerList.selectedItems():
            item.setCheckState(Qt.Unchecked)

    def actionShowComposer(self):
        selected = {item.text() for item in wdgt.selectedItems()}
        for cView in self.iface.activeComposers():
            if cView.composerWindow().windowTitle() in selected:
                cView.composerWindow().show()
        
    def actionHideComposer(self):
        selected = {item.text() for item in wdgt.selectedItems()}
        for cView in self.iface.activeComposers():
            if cView.composerWindow().windowTitle() in selected:
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
        
    def refreshList(self):
        """ When updating the list of composers, the state of composers already listed is kept if they are still in the project
        so just add new composers and erase those deleted/renamed
        """
        currentComposers = []
        i,j = 0,0
        
        # if len(self.iface.activeComposers()) == 0:
            # self.iface.messageBar().pushMessage(
                # self.tr('Maps Printer : '),
                # self.tr('The dialog has been closed due to a lack of print composer in the project. Please create at least one before running this plugin.'), 
                # level = QgsMessageBar.INFO, duration = 10
                # )
            # self.dlg.close()
        # else :
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
        for cView in self.iface.activeComposers ():
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
        for rowList in range(0, wdgt.count()):
            wdgt.item(rowList).setCheckState(etat)
        
    def listCheckedComposer(self): 
        """ Get all the boxes and textes checked in the list."""
        global rowsChecked

        # rowsChecked = [rowList for rowList in range(0, wdgt.count()) \
            # if wdgt.item(rowList).checkState() == Qt.Checked
            # ]
        # rowsChecked = {(rowList, wdgt.item(rowList).text()) \
            # for rowList in range(0, wdgt.count()) \
            # if wdgt.item(rowList).checkState() == Qt.Checked
            # }
        # rowsChecked = {rowList:wdgt.item(rowList).text() for rowList in range(0, wdgt.count()) \
            # if wdgt.item(rowList).checkState() == Qt.Checked
            # }
        rowsChecked = {wdgt.item(rowList).text():rowList for rowList in range(0, wdgt.count()) \
            if wdgt.item(rowList).checkState() == Qt.Checked
            }
        # QMessageBox.warning( None, self.tr( "Unable to write into the directory" ),
            # "{}".format(rowsChecked), 
            # QMessageBox.Ok, QMessageBox.Ok  )
        return rowsChecked

    def on_composercbox_changed(self):
        """ When at least one of the composers listed is unchecked, 
        then the "select All" checkbox should be unchecked too 
        """
        self.listCheckedComposer()
        if len(rowsChecked) == wdgt.count():
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
        # box.addItems([x[0] for x in list1]) 
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
            self.iface.messageBar().pushMessage('Maps Printer', 
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
        # update the selected composers list
        self.listCheckedComposer()
        # get the output file format and directory
        ext = self.setFormat(self.dlg.formatBox.currentText())
        folder = self.dlg.path.text()
        # Is there at least one composer checked, an output folder indicated or an output file format chosen?       
        d = {
            (self.dlg.composerList, len(rowsChecked)), # the composer list and the number of checked composers
            (self.dlg.path, folder), # the folder box and its text
            (self.dlg.formatBox, ext) # the format list and its choice
            }
        # check if all the mandatory informations are filled and if ok, export
        if self.checkFilled(d):
            if self.checkFolder(folder):
                self.dlg.progressBar.setEnabled(True)
                self.dlg.progressBar.setValue(0)
                # printer = QPrinter()
                # painter = QPainter()
                l = len(rowsChecked)
                
                for cView in self.iface.activeComposers ():
                    title = cView.composerWindow().windowTitle()
                    if title in rowsChecked :
                        self.exportCompo(cView, ext, folder)
                        self.dlg.progressBar.setValue(self.dlg.progressBar.value()+ 100/l)
                        # QMessageBox.warning( None, self.tr( "Unable to write into the directory" ),
                            # self.tr('compositions {} , n° {} has been exported!'.format(title, rowsChecked[str(title)])), 
                            # QMessageBox.Ok, QMessageBox.Ok  )
                        wdgt.item(rowsChecked[title]).setCheckState(Qt.Unchecked)
                    # self.dlg.progressBar.setEnabled(False)
                    # self.dlg.progressBar.setValue(0)
        
                # show a successful message bar
                self.iface.messageBar().pushMessage(
                    self.tr('Operation succeeded : '),
                    self.tr('{} compositions have been exported!'.format(l)), 
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

        # if fileDialog == '':
            # self.dlg.path.setText(self.dlg.path.text())
        # else:
        self.dlg.path.setText(fileDialog)

    def checkFolder(self, outputDir):
        """ test directory (if it exists and is writable)"""
        try:
            os.makedirs( outputDir )
        except OSError as e :    
            # if the directory already exists then pass
            if e.errno == errno.EEXIST :
                return True
                # QMessageBox.warning( None, self.tr( "Unable to create the directory" ),
                    # self.tr( "directory already exists{}".format(e) ), 
                    # QMessageBox.Ok, QMessageBox.Ok  )
            # if the directory is not writable
            if e.errno == errno.EACCES :
                QMessageBox.warning( None, self.tr( "Unable to access the directory" ),
                    self.tr( "You don't have rights to write in this folder. Please, select another folder!" ), 
                    QMessageBox.Ok, QMessageBox.Ok  )
                self.browseDir()
        
    def showHelp(self):
        """ Function that shows the help dialog """
        self.aboutWindow = mpAboutWindow()
              
    def help2(self):
        helpfile = os.path.join(os.path.dirname(__file__), "help/build/html", "index.html")
        QDesktopServices.openUrl(QUrl.fromLocalFile(helpfile))

    def run(self):
        """ Run method that performs all the real work """
        # when no composer is in the project, display a message about the lack of composers and exit
        if len(self.iface.activeComposers()) == 0:
            self.iface.messageBar().pushMessage(
                self.tr('Maps Printer : '),
                self.tr('There is no print composer in the project. Please create at least one before running this plugin.'), 
                level = QgsMessageBar.CRITICAL, duration = 5
                )
        else:
            # Name the dialog with the project's title or filename
            if QgsProject.instance().title() <> '' :
                self.dlg.setWindowTitle("MapsPrinter - {}".format( QgsProject.instance().title()))
            else :    
                self.dlg.setWindowTitle("MapsPrinter - {}".format(
                    os.path.splitext(os.path.split(QgsProject.instance().fileName())[1])[0]))

            # show the dialog and fill the widget the first time
            if not self.dlg.isVisible():
                self.populateComposerList(wdgt)
            else: 
                # if the dialog is already opened but not at top of the screen
                # Put it at the top of all other widgets,
                # update the list of composers and keep the previously selected options in the dialog
                self.dlg.activateWindow()
                self.refreshList()

"""
OTHER SITUATIONS TO DEAL WITH:
- Known issues: 
        - shouldExportPage
        - What about composers that have same name? they appear just once in the list and, due to the naming, only one export is kept (overwriting without notification?)
- Improvements : 
    - when refreshing, keep in the list the renamed composer(s) and its checkbox state. Currently, they are erased from the list and appended with their new name.
    - Check the read/write ability of the user on the specified output folder
    - check if file already exist and ask how to deal with
    - Add project name in the dialog title
    - Rely the dialog to the project, so many dialogs can be opened simultaneously (different projects)
    - Implement svg format export
"""