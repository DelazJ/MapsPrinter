# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Export several print layouts to pdf, svg or image file format in one-click
                              -------------------
        begin                : 2020-01-10
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Germán Carrillo (GeoTux)
        email                : gcarrillo@linuxmail.org
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
import glob
import qgis
from qgis.core import (QgsProject,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterEnum,
                       QgsProcessingOutputFolder,
                       QgsProcessingParameterNumber,
                      )
from qgis.PyQt.QtCore import QCoreApplication
from processing.core.ProcessingConfig import ProcessingConfig

from MapsPrinter.processor import Processor


class ExportLayoutsFromFolder(QgsProcessingAlgorithm):

    PROJECTS_FOLDER = 'PROJECTS_FOLDER'
    EXTENSION = 'EXTENSION'
    RESOLUTION = 'RESOLUTION'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    OUTPUT = 'OUTPUT'

    def createInstance(self):
        return type(self)()

    def tags(self):
        return (self.tr('layout,composer,map,printer,batch,project,folder')).split(',')

    def __init__(self):
        super().__init__()
        self.processor = Processor()
        self.listFormats = self.processor.listFormat()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECTS_FOLDER,
                self.tr("Projects folder"),
                QgsProcessingParameterFile.Folder
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.EXTENSION,
                self.tr("Extension for exported maps"),
                self.listFormats,
                defaultValue=ProcessingConfig.getSetting('DEFAULT_EXPORT_EXTENSION')
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RESOLUTION,
                self.tr("Export resolution (if not set, the layout resolution is used)"),
                optional=True,
                minValue=1
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                self.tr("Output folder where to save maps")
            )
        )
        self.addOutput(
            QgsProcessingOutputFolder(
                self.OUTPUT,
                self.tr('Output')
            )
        )

    def name(self):
        return 'ExportLayoutsFromFolder'

    def tr(self, string):
        return QCoreApplication.translate('ExportLayoutsFromFolder', string)

    def displayName(self):
        return self.tr("Export layouts from folder")

    def flags(self):
        """ Important: this algorithm should run in the main thread """
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def shortDescription(self):  # pylint: disable=missing-docstring
        return self.tr("Exports print layouts of the project files in a folder " \
               "to pdf, svg or image file formats.")

    def processAlgorithm(self, parameters, context, feedback):
        Projects_folder = self.parameterAsString(parameters, self.PROJECTS_FOLDER, context)
        extensionId = self.parameterAsEnum(parameters, self.EXTENSION, context)
        extension = self.processor.setFormat(self.listFormats[extensionId])
        resolution = self.parameterAsInt(parameters, self.RESOLUTION, context)
        Output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)

        projectPaths = glob.glob(os.path.join(Projects_folder, '*.qg[s|z]'))

        count = 0
        exported_count = 0

        if not len(projectPaths):
            feedback.reportError(
                self.tr(
                    "\nERROR: No QGIS project files (.qgs or .qgz) found in the specified folder. We cannot continue...\n"
                    )
                )
        elif not os.path.isdir(Output_folder):
            feedback.reportError(
                self.tr(
                    "\nERROR: No valid output folder given. We cannot continue...\n"
                )
            )
        elif not extensionId:
            feedback.reportError(
                self.tr(
                    '\nERROR: No valid extension selected for output. We cannot continue...\n'
                )
            )
        else:
            project = QgsProject.instance()

            # Do the work!
            for projectPath in projectPaths:
                project.read(projectPath)
                feedback.pushInfo(
                    self.tr("\n'{}' project read!").format(projectPath)
                )
                feedback.setProgress(count * 100 / len(projectPaths))
                count += 1

                for composer in project.layoutManager().printLayouts():
                    feedback.pushInfo(
                        self.tr("\n--> Layout found: '{}'!").format(composer.name())
                    )

                    # Retrieve the resolution to apply to the export
                    self.processor.getResolution(composer, resolution)

                    title = composer.name()
                    title = project.baseName() + '_' + title
                    result = self.processor.exportCompo(composer, Output_folder, title, extension)
                    if result:
                        feedback.pushInfo(
                            self.tr("      Layout exported!")
                        )
                        exported_count += 1
                    else:
                        feedback.reportError(
                            self.tr("      Layout could not be exported!!")
                        )

            if exported_count:
                feedback.pushInfo(
                    self.tr("\nINFO: {} layout(s) were exported to '{}'\n").format(exported_count, Output_folder)
                )

        return {self.OUTPUT: Output_folder if exported_count else None}

