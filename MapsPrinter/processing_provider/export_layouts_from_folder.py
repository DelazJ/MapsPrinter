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
from qgis.core import (
    QgsProject,
    QgsProcessingAlgorithm,
    QgsProcessingOutputFolder,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
)
from qgis.PyQt.QtCore import QCoreApplication
from processing.core.ProcessingConfig import ProcessingConfig

from MapsPrinter.processor import Processor


class ExportLayoutsFromFolder(QgsProcessingAlgorithm):

    PROJECTS_FOLDER = "PROJECTS_FOLDER"
    RECURSIVE = "RECURSIVE"
    EXTENSION = "EXTENSION"
    RESOLUTION = "RESOLUTION"
    PREFIX = "PREFIX"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    OUTPUT = "OUTPUT"

    def createInstance(self):
        return type(self)()

    def tags(self):
        return (self.tr("layout,composer,map,printer,batch,project,folder")).split(",")

    def __init__(self):
        super().__init__()
        self.processor = Processor()
        self.listFormats = self.processor.listFormat()

    def initAlgorithm(self, config=None):
        project_folder = QgsProcessingParameterFile(
            self.PROJECTS_FOLDER,
            self.tr("Projects folder"),
            QgsProcessingParameterFile.Folder,
        )
        project_folder.setHelp(
            "The folder containing the projects to export the layouts from."
        )
        self.addParameter(project_folder)

        sub_directories = QgsProcessingParameterBoolean(
            self.RECURSIVE,
            self.tr("Include sub-directories"),
            defaultValue=False,
        )
        sub_directories.setHelp(
            "Whether layouts should also be taken from projects in sub-folders of the selected folder."
        )
        self.addParameter(sub_directories)

        extension = QgsProcessingParameterEnum(
            self.EXTENSION,
            self.tr("Extension for exported maps"),
            self.listFormats,
            defaultValue=ProcessingConfig.getSetting("DEFAULT_EXPORT_EXTENSION"),
        )
        extension.setHelp("The file format to apply to exported files.")
        self.addParameter(extension)

        resolution = QgsProcessingParameterNumber(
            self.RESOLUTION,
            self.tr("Export resolution"),
            optional=True,
            minValue=1,
        )
        resolution.setHelp(
            "The image resolution to assign to exported files. If not set, the resolution set in the layout properties is used."
        )
        self.addParameter(resolution)

        prefix = QgsProcessingParameterBoolean(
            self.PREFIX,
            self.tr("Prefix with project file name"),
            defaultValue=False,
        )
        prefix.setHelp(
            "Whether the output file name should begin with its original project file name."
        )
        self.addParameter(prefix)

        output_folder = QgsProcessingParameterFile(
            self.OUTPUT_FOLDER,
            self.tr("Output folder where to save maps"),
            QgsProcessingParameterFile.Folder,
        )
        output_folder.setHelp("The folder to export the layouts to.")
        self.addParameter(output_folder)

        self.addOutput(QgsProcessingOutputFolder(self.OUTPUT, self.tr("Output")))

    def name(self):
        return "exportlayoutsfromfolder"

    def tr(self, string):
        return QCoreApplication.translate("ExportLayoutsFromFolder", string)

    def displayName(self):
        return self.tr("Export layouts from folder")

    def flags(self):
        """Important: this algorithm should run in the main thread"""
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def shortDescription(self):  # pylint: disable=missing-docstring
        return self.tr(
            "Exports print layouts of the project files in a folder "
            "to pdf, svg or image file formats."
        )

    def shortHelpString(self):  # pylint: disable=missing-docstring
        return self.tr(
            "This algorithm exports print layouts from the project files in a given folder "
            "to pdf, svg or image file formats. Layouts from projects in sub-folders can also be included."
        )

    def processAlgorithm(self, parameters, context, feedback):
        projectsFolder = self.parameterAsString(
            parameters, self.PROJECTS_FOLDER, context
        )
        isRecursive = self.parameterAsBoolean(parameters, self.RECURSIVE, context)
        extensionId = self.parameterAsEnum(parameters, self.EXTENSION, context)
        extension = self.processor.setFormat(self.listFormats[extensionId])
        resolution = self.parameterAsInt(parameters, self.RESOLUTION, context)
        prefix = self.parameterAsBoolean(parameters, self.PREFIX, context)
        mainOutputFolder = self.parameterAsString(
            parameters, self.OUTPUT_FOLDER, context
        )

        if not isRecursive:
            projectPaths = glob.glob(os.path.join(projectsFolder, "*.qg[s|z]"))
        else:
            projectPaths = glob.glob(
                os.path.join(projectsFolder, "**/*.qg[s|z]"), recursive=True
            )
        # feedback.pushInfo(self.tr('{} project files found: {}').format(len(projectPaths), projectPaths))

        total = 100 / len(projectPaths)
        exportedCount = 0

        if not len(projectPaths):
            feedback.reportError(
                self.tr(
                    "\nERROR: No QGIS project files (.qgs or .qgz) found in the specified folder. We cannot continue...\n"
                )
            )
        elif not os.path.isdir(mainOutputFolder):
            feedback.reportError(
                self.tr(
                    "\nERROR: No valid output folder given. We cannot continue...\n"
                )
            )
        elif extensionId is None:
            feedback.reportError(
                self.tr(
                    "\nERROR: No valid extension selected for output. We cannot continue...\n"
                )
            )
        else:
            project = QgsProject.instance()

            # Do the work!
            for count, projectPath in enumerate(projectPaths):
                project.read(projectPath)
                feedback.pushInfo(self.tr("\n'{}' project read!").format(projectPath))
                feedback.setProgress(count * total)

                # Compute the destination folder for the current file outputs
                # by appending sub-directories name to the user set output folder
                outputFolder = os.path.join(
                    mainOutputFolder,
                    os.path.dirname(projectPath)[len(projectsFolder) + 1 :],
                )
                # Create the destination folder if it does not exist yet
                if not os.path.exists(outputFolder):
                    try:
                        os.makedirs(outputFolder)
                    except OSError:
                        feedback.pushInfo(
                            self.tr("Creation of the directory '{}' failed").format(
                                outputFolder
                            )
                        )
                    else:
                        feedback.pushInfo(
                            self.tr("Successfully created the directory '{}'").format(
                                outputFolder
                            )
                        )

                for composer in project.layoutManager().printLayouts():
                    feedback.pushInfo(
                        self.tr("\n--> Layout found: '{}'!").format(composer.name())
                    )

                    # Retrieve the resolution to apply to the export
                    self.processor.getResolution(composer, resolution)

                    title = composer.name()
                    if prefix:
                        title = project.baseName() + "_" + title

                    result = self.processor.exportCompo(
                        composer, outputFolder, title, extension, prefix
                    )
                    if result:
                        feedback.pushInfo(self.tr("      Layout exported!"))
                        exportedCount += 1
                    else:
                        feedback.reportError(
                            self.tr("      Layout could not be exported!!")
                        )

            if exportedCount:
                feedback.pushInfo(
                    self.tr("\nINFO: {} layout(s) were exported to '{}'\n").format(
                        exportedCount, mainOutputFolder
                    )
                )

        return {self.OUTPUT: mainOutputFolder if exportedCount else None}
