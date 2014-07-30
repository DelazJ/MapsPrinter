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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt4.QtGui import QAction, QIcon, QListWidgetItem, QFileDialog, QMessageBox #QWidget #QFrame #QListView #QAbstractItemView #QListWidget
from qgis.core import *
from qgis.gui import QgsMessageBar
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from maps_printer_dialog import MapsPrinterDialog
import os.path
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

        global wdgt
        wdgt = self.dlg.composerList

        
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
        self.action = QAction( QIcon(":/plugins/MapsPrinter/icons/icon.png"), self.tr('Export multiple print composers'), self.iface.mainWindow())
        self.helpAction = QAction( QIcon(":/plugins/MapsPrinter/icons/about.png"), self.tr('Help'), self.iface.mainWindow())

        # connect the action to the run method
        self.action.triggered.connect(self.run)
        self.helpAction.triggered.connect(self.showHelp)

        # connect the signal to update the list of composers checked
        wdgt.itemClicked.connect(self.listCheckedComposer)

        # connect the signal to set the "select all" checkbox behaviour 
        self.dlg.checkBox.clicked.connect(self.selectAllCheckbox)
        wdgt.itemClicked.connect(self.unselectAllCheckbox)
        
        # connect to the export button to do the real work
        self.dlg.exportButton.clicked.connect(self.exportFile)
        
        # connect to the browse button so you can select directory
        self.dlg.browse.clicked.connect(self.browseDir)
        
        # connect the action to the updater button so you can update the list of composers
        self.dlg.updater.clicked.connect(self.refreshList)

        # Add toolbar button and menu item0
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Maps Printer", self.action)
        self.iface.addPluginToMenu(u"&Maps Printer", self.helpAction)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu(u"&Maps Printer", self.action)
        self.iface.removePluginMenu(u"&Maps Printer", self.helpAction)
        self.iface.removeToolBarIcon(self.action)           
    
    def getNewCompo(self, compo):
        """Function that finds new composer to be added to the list """
        nameCompo = compo.composerWindow().windowTitle()
        if not wdgt.findItems(nameCompo, Qt.MatchExactly):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setText(nameCompo)
            wdgt.addItem(item)
            
    def populateComposerList(self):
        """ called to populate the composer list when opening a new dialog"""
        # ensure the "select All" checkbox is unchecked when opening a new dialog
        # would be better to set a default checkstate somewhere (?)
        self.dlg.checkBox.setChecked(False) 
        # then get back all the composers in an previously emptied list
        wdgt.clear() 
        for cView in self.iface.activeComposers ():
            self.getNewCompo(cView)
        wdgt.sortItems()
        
    def refreshList(self):
        """ When updating the list of composers, the state of composers already listed is kept if they are still in the project
        so just add new composers and erase those deleted/renamed"""
        mylistComposers = []
        i,j = 0,0
        # get the current list of composers
        while i < len(self.iface.activeComposers()):
            nameCompo = self.iface.activeComposers()[i].composerWindow().windowTitle() 
            mylistComposers.append(nameCompo)
            i += 1
            
        # # erase deleted (or renamed) composers
        while j < wdgt.count():
            rowCheckbox = wdgt.item(j)
            if rowCheckbox.text() not in mylistComposers:
                wdgt.takeItem(j)
            else:
                j += 1
        
        # add new composers to the list
        for cView in self.iface.activeComposers ():
            self.getNewCompo(cView)
            # if self.getNewCompo(cView):
                # self.dlg.checkBox.setChecked(False)
        wdgt.sortItems()
        
        # and check if all the remained rows are checked (called to display coherent check boxes). Better way?
        self.listCheckedComposer()
        self.unselectAllCheckbox()
        
    def selectAllCheckbox(self):
        """ when changing the state of the "select all" checkbox, do the same to the composers listed below """
        for rowList in range(0, wdgt.count()):
            wdgt.item(rowList).setCheckState(self.dlg.checkBox.checkState())
        # then update the selected composers list (no more needed as it is called before exporting)
        # self.listCheckedComposer()
        
    def listCheckedComposer(self): 
        """ get all the boxes checked in the list"""
        global rowsChecked
        rowsChecked=[]

        # the code below actually reinitializes the rowsChecked list instead of adding new items and taking deleted ones,
        # because of the hard management of composer rank in the list (when new items have been added).
        for rowList in range(0, wdgt.count()):
            rowCheckbox = wdgt.item(rowList)
            if rowCheckbox.checkState() == Qt.Checked:
                rowsChecked.append(rowList)
        return rowsChecked

    def unselectAllCheckbox(self):
        """ when one of the composers listed is unchecked, then the "select All" checkbox is unchecked too """
        if len(rowsChecked) == wdgt.count():
            self.dlg.checkBox.setChecked(True)
        else:
            self.dlg.checkBox.setChecked(False)

    def listFormat(self):
        """List all the file formats used in export mode"""
        self.dlg.formatBox.clear()
        list1 = [
            (''),
            ('.pdf'),
            ('----'),
            ('.bmp'),
            ('.ico'),
            ('.jpg'),
            ('.jpeg'),
            ('.tif'),
            ('.tiff'),
            ('.png'),
            ('.ppm'),
            ('.xbm'),
            ('.xpm')
            ]
        self.dlg.formatBox.addItems(list1) 
       
    def exportFile(self):
        """check if the conditions are filled to export file(s) and 
        export the checked composers to a file format specified """
        # get the current output file format
        ext = self.dlg.formatBox.currentText() 
        # then update the selected composers list
        self.listCheckedComposer()
        
        # check if all the mandatory informations are filled
        # is at least one composer checked ?
        if len(rowsChecked) == 0 :
            QMessageBox.information(None,QCoreApplication.translate('Maps Printer','Information'), \
                QCoreApplication.translate(self.tr('Maps Printer'),self.tr('Please, check at least one print composer in the list.')))
            # return
        # is an output folder indicated ?
        elif self.dlg.path.text() == '' :
            QMessageBox.information(None,QCoreApplication.translate('Maps Printer','Information'), \
                QCoreApplication.translate(self.tr('Maps Printer'),self.tr('Please, select an existing output folder for the file(s).')))
            # return
        # is an output file format chosen?       
        elif ext in ('' , '----') :
            QMessageBox.information(None,QCoreApplication.translate('Maps Printer','Information'), \
                QCoreApplication.translate(self.tr('Maps Printer'),self.tr('Please, select a valid output format for the file(s).')))
            # return
        else:
            # now that all is ok, let's export
                # take only checked checkbox
            for c in rowsChecked : 
                for cView in self.iface.activeComposers () :
                    rowCheckbox = wdgt.item(c)
                    if cView.composerWindow().windowTitle() == rowCheckbox.text() :
                        # export to pdf format
                        if ext == ".pdf" :
                            cView.composition().exportAsPDF(os.path.join(self.dlg.path.text(),rowCheckbox.text()+ ".pdf" ))
                        # export to other image format
                        else :
                            for numpage in range(0, cView.composition().numPages()) :
                                # managing multiple pages in the composition
                                imgOut = cView.composition().printPageAsRaster (numpage)
                                if numpage == 0 :
                                    imgOut.save(os.path.join(self.dlg.path.text(),rowCheckbox.text() + ext))
                                else :
                                    imgOut.save(os.path.join(self.dlg.path.text(),rowCheckbox.text() + "_"+ str(numpage + 1) + ext))
                       
                        # then uncheck the item and, if needed, the selectAll checkbox   
                        rowCheckbox.setCheckState(Qt.Unchecked)
                        self.dlg.checkBox.setCheckState(Qt.Unchecked)
                        
            # show a successful message bar
            self.iface.messageBar().pushMessage(self.tr('Operation Succeeded : '),self.tr( 'The files have been exported!'), level = QgsMessageBar.INFO, duration = 5)
  
    def browseDir(self):
        """ open the browser so the user selects the output directory """
        fileDialog = QFileDialog.getExistingDirectory(None, "",self.dlg.path.text(), QFileDialog.DontResolveSymlinks)
        if fileDialog == '':
            self.dlg.path.setText(self.dlg.path.text())
        else:
            self.dlg.path.setText(fileDialog)
        
    def showHelp(self):
        """ function that shows the help dialog """
        self.aboutWindow = mpAboutWindow()
              
    def run(self):
        """ run method that performs all the real work """
        # when no composer is in the project, display a message about the lack of composers and exit
        if len(self.iface.activeComposers ()) == 0 :
            self.iface.messageBar().pushMessage(self.tr('Maps Printer : '),self.tr('There is no print composer in the project. Please create at least one before running this plugin.'), level = QgsMessageBar.CRITICAL, duration = 5)
        else :
            # show the dialog and fill the widget the first time
            if not self.dlg.isVisible():
                self.dlg.show()
                self.listFormat()
                self.populateComposerList()
            else: 
                # if the dialog is already opened but not in top of the screen
                # Put it at the top of all other widgets,
                # update the list of composers and keep the previously selected options in the dialog
                self.dlg.activateWindow()
                self.refreshList()


"""
OTHER SITUATIONS TO DEAL WITH:
- Known issues: 
        - What about composers that have same name? they appear just once in the list and, due to the naming, only one export is kept (overwriting without notification?)
- Improvements : 
    - Better display the list of the exports files format
    - when refreshing, keep in the list the renamed composer(s) and its checkbox state. Currently, they are erased from the list and appended with their new name.
    - Check the read/write ability of the user on the specified output folder
    - Implement svg format export
"""