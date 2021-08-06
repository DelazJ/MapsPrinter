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
from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QImageWriter
from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingMultiStepFeedback,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterNumber,
                      )
from processing.core.ProcessingConfig import ProcessingConfig

from MapsPrinter.processor import Processor

class ExportLayoutsFromProject(QgsProcessingAlgorithm):
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
    RESOLUTION = 'RESOLUTION'
    OUTPUT = 'OUTPUT'
    EXPORTEDLAYOUTS = 'EXPORTEDLAYOUTS'

    def __init__(self):
        super().__init__()
        self.processor = Processor()
        self.listFormats = self.processor.listFormat()

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.layoutList = sorted([cView.name() for cView in QgsProject.instance().layoutManager().printLayouts()], key=str.lower)
        self.addParameter(
            QgsProcessingParameterEnum(
                self.LAYOUTS,
                self.tr('Layouts to export'),
                options=self.layoutList,
                allowMultiple=True
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.EXTENSION,
                self.tr('Extension for exported maps'),
                options=self.listFormats,
                defaultValue=ProcessingConfig.getSetting('DEFAULT_EXPORT_EXTENSION')
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.RESOLUTION,
                self.tr('Export resolution (if not set, the layout resolution is used)'),
                optional=True,
                minValue=1
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT,
                self.tr('Output folder where to save maps')
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
        extension = self.processor.setFormat(self.listFormats[extensionId])
        resolution = self.parameterAsInt(parameters, self.RESOLUTION, context)
        outputFolder = self.parameterAsFile(parameters, self.OUTPUT, context)

        layoutIds = self.parameterAsEnums(parameters, self.LAYOUTS, context)
        # # Todo?: if no layout is checked, pick them all
        # if not layoutIds:
            # layoutIds = self.layoutList.keys()
        exportedCount = 0
        
        feedback = QgsProcessingMultiStepFeedback(len(layoutIds), feedback)

        if not os.path.isdir(outputFolder):
            feedback.reportError(self.tr('\nERROR: No valid output folder given. We cannot continue...\n'))
        elif extensionId is None:
            feedback.reportError(self.tr('\nERROR: No valid extension selected for output. We cannot continue...\n'))
        else:
            for current, layout in enumerate(layoutIds):
                if feedback.isCanceled():
                    feedback.pushInfo(self.tr("Export aborted!"))
                    break

                title = self.layoutList[layout]
                cView = QgsProject.instance().layoutManager().layoutByName(title)

                # Retrieve the resolution to apply to the export
                self.processor.getResolution(cView, resolution)

                #feedback.pushInfo('cView= {}, Title= {}, extension= {},
                                    # resolution= {}, outputFolder= {}'.format(
                                        # cView, title, extension,
                                        # self.processor.getResolution(cView, resolution),
                                        # outputFolder)
                                    # )
                #feedback.pushInfo(self.tr("total layoutIds '{}'").format( len(layoutIds) ) )
                feedback.pushInfo(self.tr("Exporting layout '{}'").format( title ) )
                result = self.processor.exportCompo(cView, outputFolder, title, extension, feedback=feedback)
                if result:
                    feedback.pushInfo(self.tr('      Layout exported!'))
                    exportedCount += 1
                else:
                    feedback.reportError(self.tr('      Layout could not be exported!'))

                feedback.setCurrentStep(current + 1)

            feedback.pushInfo( self.tr('End of export!'))

        if exportedCount:
            return {self.EXPORTEDLAYOUTS: exportedCount,
                    self.OUTPUT: outputFolder
                   }
        else:
            return {self.OUTPUT: None}

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
        return self.tr('Export layouts from project')

    def tr(self, string):
        return QCoreApplication.translate('ExportLayoutsFromProject', string)

    def createInstance(self):
        return ExportLayoutsFromProject()

    def shortDescription(self):  # pylint: disable=missing-docstring
        return self.tr("Exports print layouts of the current project file to pdf, svg or image file formats.")

    # def shortHelpString(self):
        # return self.tr("Exports a set of print layouts in the project to pdf, svg or image file formats " \
               # "to an indicated folder.")

    # def helpUrl(self):
        # return ...

    def tag(self):
        return self.tr("print,layout,export,composer,image,pdf,svg,map")

    def flags(self):
        """ Important: this algorithm should run in the main thread """
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading
