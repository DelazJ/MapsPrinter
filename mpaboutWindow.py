# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Exports simultaneously several print composers to pdf or image file format
                              -------------------
        begin                : 2014-07-24
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
# Import the PyQt and QGIS libraries
from PyQt4 import QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

class mpAboutWindow(QDialog):

    def __init__(self):
        QDialog.__init__(self)
        
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self.helpFile = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "python/plugins/MapsPrinter/README.html"
        
        self.setWindowTitle(self.tr('Maps Printer - Help'))
        
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/plugins/MapsPrinter/icons/icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)

        txt = QTextBrowser()
        txt.setReadOnly(True)
        txt.setText( open(self.helpFile, 'r').read() )

        cls = QPushButton(self.tr('Close'))
        
        QObject.connect(cls,SIGNAL("pressed()"),self.accept)

        lay = QVBoxLayout()
        lay.addWidget(txt)
        lay.addWidget(cls)

        self.setLayout(lay)

        self.show()
        
