# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Export several print layouts to pdf, svg or image file format in one-click
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

import os.path
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider
from processing.core.ProcessingConfig import ProcessingConfig, Setting

from .export_layouts_from_project import ExportLayoutsFromProject
from .export_layouts_from_folder import ExportLayoutsFromFolder
from MapsPrinter.processor import Processor

class MapsPrinterProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)
        self.processor = Processor()

    def load(self):
        """
        Loads the provider with its settings.
        """
        ProcessingConfig.settingIcons[self.name()] = self.icon()

        ProcessingConfig.addSetting(Setting(
            self.name(),
            'DEFAULT_EXPORT_EXTENSION',
            self.tr('Default layout export format'),
            default='PNG format (*.png *.PNG)',
            valuetype=Setting.SELECTION,
            options=self.processor.listFormat()))

        ProcessingConfig.readSettings()
        return super().load()

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        ProcessingConfig.removeSetting('DEFAULT_EXPORT_EXTENSION')

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(ExportLayoutsFromProject())
        self.addAlgorithm(ExportLayoutsFromFolder())
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'mapsprinter'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('Maps Printer')

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QIcon(os.path.join(os.path.dirname(__file__),'../icons/icon.png'))


    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.tr("Export layouts from projects or folders")
