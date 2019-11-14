# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Show, hide and export several print layouts to pdf, svg or image file format in one-click
                              -------------------
        begin                : 2019-11-05
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Harrissou Sant-anna / CAUE du Maine-et-Loire
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

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
from qgis.PyQt.QtWidgets import QListWidgetItem
from qgis.PyQt.QtCore import Qt, QCoreApplication, QSettings 
from qgis.PyQt.QtGui import QImageWriter

from qgis.core import QgsLayoutExporter

class Processor:
    """
    Utilities for managing layout export components
    """

    def getNewCompo(self, w, cView):
        """Function that finds new layout to be added to the list.
        Seems to work only with the dialog so consider moving to there?"""

        nameCompo = cView.name()
        if not w.findItems(nameCompo, Qt.MatchExactly):
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setText(nameCompo)
            w.addItem(item)

    def listFormat():
        """List all the file formats we can export to."""

        formats = [
            '',
            QCoreApplication.translate('Maps Printer', 'PDF format (*.pdf *.PDF)'),
            QCoreApplication.translate('Maps Printer', 'SVG format (*.svg *.SVG)'),
            ]
        #Automatically add supported image formats instead of manually
        imageformats = QImageWriter.supportedImageFormats()
        for f in imageformats:
            fs = f.data().decode('utf-8')
            formats.append(QCoreApplication.translate('Maps Printer', '{} format (*.{} *.{})').format(fs.upper(), fs, fs.upper()))

        return formats

    def setFormat(value):
        """Retrieves the format suffix to append to the output file."""

        try:
            f = value.split()[2].strip('(*')
            # f = value.split('*')[1].strip()
        except:
            f = ''
        return f

    def findActiveDir( extension ):
        """Find the last used directory depending on the format."""

        settings = QSettings()
        shortExt = Processor.setFormat(extension).lower()
        if shortExt == '.pdf' : # if extension is pdf
            dir = settings.value('/UI/lastSaveAsPdfFile')
        elif shortExt == '.svg' : # if extension is svg
            dir = settings.value('/UI/lastSaveAsSvgFile')
        else:
            dir = settings.value('/UI/lastSaveAsImageDir')

        return dir

