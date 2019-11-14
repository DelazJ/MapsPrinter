# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinterDialog
                                 A QGIS plugin
 Show, hide and export several print layouts to pdf, svg or image file format in one click
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

import os

from qgis.PyQt import QtWidgets, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'maps_printer_dialog_base.ui'))


class MapsPrinterDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(MapsPrinterDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.iface=iface
        self.setupUi(self)
        # Connect actions to context menu
        self.layoutList.customContextMenuRequested.connect(self.context_menu)

        # Connect to the export button to do the real work
        self.exportButton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.exportButton.setText(self.tr(u'Export'))
        self.exportButton.clicked.connect(self.saveFile)
        # self.buttonBox.accepted.connect(self.saveFile) # weirdly this does not work

        # Connect the signal to set the "select all" checkbox behaviour
        self.checkBox.clicked.connect(self.on_selectAllcbox_changed)
        self.layoutList.itemChanged.connect(self.on_layoutcbox_changed)

        # Connect to the browser button to select export folder
        self.browser.clicked.connect(self.browseDir)

        # Connect the action to the updater button so you can update the list of layouts
        # will be useless if i can synchronise with the layout manager widgetlist
        self.updater.clicked.connect(self.refreshList)
        # refresh the layout list when a layout is created or deleted (miss renaming case)
        # self.iface.layoutAdded.connect(self.refreshList)
        # self.iface.layoutWillBeRemoved.connect(self.refreshList, Qt.QueuedConnection)
        # self.iface.layoutRemoved.connect(self.refreshList)

        # Connect some actions to manage dialog status while another project is opened
        self.iface.newProjectCreated.connect(self.close)
        self.iface.projectRead.connect(self.renameDialog)
        self.iface.projectRead.connect(self.refreshList)

        # Hide the Cancel button and progress text at the opening
        self.printinglabel.hide()
        self.btnCancel = self.buttonBox.button(QDialogButtonBox.Cancel)
        self.btnCancel.hide()
        self.btnClose = self.buttonBox.button(QDialogButtonBox.Close)

        self.arret = False

    def context_menu(self):
        """Add context menu fonctions."""

        menu = QMenu(self.layoutList)
        menu.addAction(self.tr(u'Check...'), self.actionCheckLayout)
        menu.addAction(self.tr(u'Uncheck...'), self.actionUncheckLayout)
        menu.addSeparator()
        menu.addAction(self.tr(u'Show...'), self.actionShowLayout)
        menu.addAction(self.tr(u'Close...'), self.actionHideLayout)
        menu.exec_(QCursor.pos())

    def actionCheckLayout(self):
        for item in self.layoutList.selectedItems():
            item.setCheckState(Qt.Checked)

    def actionUncheckLayout(self):
        for item in self.layoutList.selectedItems():
            item.setCheckState(Qt.Unchecked)

    def actionShowLayout(self):
        selected = {item.text() for item in self.layoutList.selectedItems()}
        for cView in QgsProject.instance().layoutManager().printLayouts():
            if cView.name() in selected:
                #print (cView.name(), cView.layoutType())
                self.iface.openLayoutDesigner(cView)

    def actionHideLayout(self):
        selected = {item.text() for item in self.layoutList.selectedItems()}
        #print(selected)
        designers = [d for d in self.iface.openLayoutDesigners() if d.masterLayout().name() in selected]
        #print(designers)
        for d in designers:
            #print(d, type(d))
            d.close()

    def on_layoutcbox_changed(self):
        """When at least one of the layouts listed is unchecked,
        then the "Check All" checkbox should be unchecked too.
        """

        self.listCheckedLayout()
        if len(rowsChecked) == self.layoutList.count():
            self.checkBox.setChecked(True)
        else:
            self.checkBox.setChecked(False)

    def on_selectAllcbox_changed(self):
        """When changing the state of the "Check all" checkbox,
        do the same to the layouts listed below.
        """

        etat = self.checkBox.checkState()
        for rowList in range(0, self.layoutList.count()):
            self.layoutList.item(rowList).setCheckState(etat)

    def listCheckedLayout(self):
        """Get all the boxes and texts checked in the list."""

        global rowsChecked

        # rowsChecked = [rowList for rowList in range(0, self.layoutList.count()) \
            # if self.layoutList.item(rowList).checkState() == Qt.Checked]
            #
        # rowsChecked = {(rowList, self.layoutList.item(rowList).text()) \
            # for rowList in range(0, self.layoutList.count()) \
            # if self.layoutList.item(rowList).checkState() == Qt.Checked}
            #
        # rowsChecked = {rowList:self.layoutList.item(rowList).text() for rowList in range(0, self.layoutList.count()) \
            # if self.layoutList.item(rowList).checkState() == Qt.Checked}
            #
        rowsChecked = {
            self.layoutList.item(rowList).text(): rowList for rowList in range(
                0, self.layoutList.count()
                ) if self.layoutList.item(rowList).checkState() == Qt.Checked
        }

        return rowsChecked

    def browseDir(self):
        """Open the browser so the user selects the output directory."""

        dir = Processor.findActiveDir(self.formatBox.currentText())
        folderDialog = QFileDialog.getExistingDirectory(
            None,
            '',
            dir,
            QFileDialog.ShowDirsOnly,
            # QFileDialog.DontResolveSymlinks
            )

        #Do not alter potential folder path if the dialog was canceled
        if folderDialog == '':
            self.path.setText(self.path.text())
        else:
            self.path.setText(folderDialog)

    def refreshList(self):
        """Updates the list of layouts shown in the widget.
        When updating the list of layouts, we try to keep the check state of
        already listed layouts already if they are still in the project.
        So let's just add new layouts and erase those deleted/renamed."""

        currentLayouts = []
        i,j = 0,0

        if len(QgsProject.instance().layoutManager().printLayouts()) == 0 and self.isVisible():
            self.iface.messageBar().pushMessage('Maps Printer : ',
                self.tr(u'dialog shut because no more print layout in the project.'),
                level = Qgis.Info, duration = 5
                )
            self.close()
        else:
            # Get the current list of layouts
            while i < len(QgsProject.instance().layoutManager().printLayouts()):
            # for i in range(len(QgsProject.instance().layoutManager().printLayouts()):
                currentLayouts.append(
                    QgsProject.instance().layoutManager().printLayouts()[i].name()
                    )
                i += 1

            # Erase deleted (or renamed) layouts
            while j < self.layoutList.count():
                if self.layoutList.item(j).text() not in currentLayouts:
                    self.layoutList.takeItem(j)
                else:
                    j += 1

            # Add new layouts to the list
            for cView in QgsProject.instance().layoutManager().printLayouts():
                Processor.getNewCompo(self, self.layoutList, cView)
            self.layoutList.sortItems()

            # And check if all the remained rows are checked
            # (called to display coherent check boxes). Better way?
            self.on_layoutcbox_changed()

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
        extension = Processor.setFormat(self.formatBox.currentText())
        folder = self.path.text()
        # Are there at least one layout checked,
        # an output folder indicated and an output file format chosen?
        d = {
            # the layout list and the number of checked layouts
            (self.layoutList, len(rowsChecked)),
            # the folder box and its text
            (self.path, folder),
            # the format list and its choice
            (self.formatBox, extension)
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
                self.printinglabel.show()
                self.printinglabel.setText(
                    self.tr(u'Exporting {}...').format(title)
                    )

                # process input events in order to allow canceling
                QCoreApplication.processEvents()
                if self.arret:
                    break
                self.pageBar.setValue(0)
                Processor.exportCompo(self, cView, folder, title, extension)
                i = i + 1
                self.printBar.setValue(i)
                self.layoutList.item(
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

    def populateLayoutList(self, w):
        """Called to populate the layout list when opening a new dialog."""

        # Get  all the layouts in a previously emptied list
        w.clear()
        # Populate export format listbox
        self.displayFormat(self.formatBox)
        # Ensure the "select all" box is unchecked
        self.checkBox.setChecked(False)

        for cView in QgsProject.instance().layoutManager().printLayouts():
            Processor.getNewCompo(self, w, cView)
        w.sortItems()

    def displayFormat(self, box):
        """List all the file formats used in export mode."""

        box.clear()
        list1 = Processor.listFormat()
        box.addItems(list1)
        box.insertSeparator(2)
        box.insertSeparator(4)

    def checkFilled(self, d):
        """Check if all the mandatory informations are filled in the GUI.
        Consider moving it to GuiUtils?"""

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

    def initGuiButtons(self):
        """Init the GUI to follow export processes."""

        self.printBar.setValue(0)
        self.printBar.setMaximum(len(rowsChecked))
        self.exportButton.setEnabled(False)

        # Activate the Cancel button to stop export process, and hide the Close button
        self.buttonBox.disconnect()
        self.btnClose.hide()
        self.btnCancel.show()
        self.buttonBox.rejected.connect(self.stopProcessing)

    def pageProcessed(self, feedback):
        """Increment the page progressbar. Only atlas makes it run as
        there seems to be no obvious way to catch page export."""

        QCoreApplication.processEvents()
        if feedback:
            self.pageBar.setValue(feedback)
        # else:
            # self.pageBar.setValue(100)

    def stopProcessing(self, feedback=None):
        """Help to stop the export processing."""

        #print ('feed', feedback)
        if feedback:
            #print ('feedOK', feedback)
            emit(feedback.isCanceled)
        self.arret = True

    def restoreGui(self):
        """Reset the GUI to its initial state."""

        QTimer.singleShot(1000, lambda: self.pageBar.setValue(0))
        self.printinglabel.setText('')
        self.printinglabel.hide()

        # Reset standardbuttons and their functions and labels
        self.buttonBox.rejected.disconnect(self.stopProcessing)
        self.buttonBox.rejected.connect(self.reject)
        self.btnCancel.hide()
        self.btnClose.show()
        QApplication.restoreOverrideCursor()
        self.exportButton.setEnabled(True)

        self.arret = False

    def renameDialog(self):
        """Name the dialog with the project's title or filename."""

        prj = QgsProject.instance()

        if prj.title() != '':
            self.setWindowTitle(u'Maps Printer - {}'.format(prj.title()))
        else:
            self.setWindowTitle(u'Maps Printer - {}'.format(
                os.path.splitext(os.path.split(prj.fileName())[1])[0]))
