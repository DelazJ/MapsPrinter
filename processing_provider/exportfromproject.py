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

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QImageWriter
from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFolderDestination)

from MapsPrinter.gui_utils import GuiUtils
from MapsPrinter.processor import Processor

class ExportFromProjectAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    LAYOUTS = 'LAYOUTS'
    EXTENSION = 'EXTENSION'
    OUTPUT = 'OUTPUT'
    EXPORTEDLAYOUTS = 'EXPORTEDLAYOUTS'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.layoutList = [cView.name() for cView in QgsProject.instance().layoutManager().printLayouts()]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.LAYOUTS,
                self.tr('Layouts to export'),
                options=self.layoutList,
                allowMultiple=True
            )
        )

        self.listFormats = Processor.listFormat()
        self.addParameter(
            QgsProcessingParameterEnum(
                self.EXTENSION,
                self.tr('File format to export to'),
                options=self.listFormats,
                defaultValue=11)
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT,
                self.tr('Output folder')
            )
        )

        self.addOutput(
            QgsProcessingOutputNumber(
                self.EXPORTEDLAYOUTS,
                self.tr('Number of layouts exported')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        extensionId = self.parameterAsEnum(parameters, self.EXTENSION, context)
        extension = Processor.setFormat(self.listFormats[extensionId])
    
        output_folder = self.parameterAsFile(parameters, self.OUTPUT, context)

        layoutIds = self.parameterAsEnums(parameters, self.LAYOUTS, context)
        # # Todo: if no layout is checked, pick them all
        # if not layoutIds:
            # layoutIds = self.layoutList.keys()
        processedLayouts = 0
        
        for layout in layoutIds:
            title = self.layoutList[layout]
            cView = QgsProject.instance().layoutManager().layoutByName(title)
            feedback.pushInfo( "cView = {}, Title=  {}, extensionId=  {}, extension=  {},  output_folder=  {}".format(cView, title, extensionId, extension, output_folder)
                )
            feedback.pushInfo( "Exporting layout '{}'".format( title ) )
            Processor.exportCompo(self, cView, output_folder, title, extension)
            processedLayouts += 1

        EXPORTEDLAYOUTS = processedLayouts
        feedback.pushInfo( "End of export!'" )
        
        return {self.EXPORTEDLAYOUTS: EXPORTEDLAYOUTS,
                self.OUTPUT: output_folder
                }

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'exportlayoutsfromproject'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Export layouts from a project")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Cartography'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExportFromProjectAlgorithm()

    def shortDescription(self):  # pylint: disable=missing-docstring
        return self.tr("Exports a set of print layouts in the project to pdf, svg or image file formats " \
               "to an indicated folder.")

    # def shortHelpString(self): 
        # return self.tr("Exports a set of print layouts in the project to pdf, svg or image file formats " \
               # "to an indicated folder.")

    # def helpUrl(self):
        # return GuiUtils.showHelp()

    def tag(self):
        return self.tr("print,layout,export,image,pdf,svg,map")

    def flags(self):
        """ Important: this algorithm should run in the main thread """
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading
