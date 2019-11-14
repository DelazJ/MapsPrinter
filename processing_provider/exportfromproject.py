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

from collections import OrderedDict
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFolderDestination,
                       #QgsProcessingParameterLayout
                       QgsProject)

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
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.listFormats = Processor.listFormat()


        # for version >=3.8 only and useless until there's an "allowMultiple" capability
        # self.addParameter(
            # QgsProcessingParameterLayout(
                # self.LAYOUTS,
                # self.tr('Layouts to export'),
                # None,
                # optional=False
            # )
        # )
        #we display layout names in the GUI but need a reference to the layout composition
        #self.layoutList = (cView.name(), cView) for cView in QgsProject.instance().layoutManager().printLayouts()
        self.layoutList = OrderedDict([cView.name(), cView] for cView in QgsProject.instance().layoutManager().printLayouts())
        layoutkeys = list(self.layoutList.keys())
        self.addParameter(
            QgsProcessingParameterEnum(
                self.LAYOUTS,
                self.tr('Layouts to export'),
                options=layoutkeys, #[cView.name() for cView in QgsProject.instance().layoutManager().printLayouts()],
                allowMultiple=True
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.EXTENSION,
                self.tr('File format to export to'),
                options=self.listFormats)
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                self.tr('Output folder')
            )
        )

    def prepareAlgorithm(self, parameters, context, feedback):
        """
        we need to configure the processing settings formatting
        since some variables displayed in the GUI are not what we'll actually work with
        (extension, layout)
        """

        layouts = self.parameterAsEnum(parameters, self.LAYOUTS, context)
        #Allow to process on all layouts if none is selected
        #keys = list(self.layoutList.keys())
        #self.selectedLayouts = 0
        #if keys.isEmpty():
            #for i in Layouts:
                #keys.append(self.layoutList.keys())
                
                #self.selectedLayouts |= self.layoutList[keys[i]]
        #else:
            #self.selected

        #from join by nearest attributes algorithm
        #https://github.com/qgis/QGIS/blob/master/src/analysis/processing/qgsalgorithmjoinbynearest.cpp
        #const QStringList fieldsToCopy = parameterAsFields( parameters, QStringLiteral( "FIELDS_TO_COPY" ), context );

        #QgsFields outFields2;
        #QgsAttributeList fields2Indices;
        #if ( fieldsToCopy.empty() )
        #{
            #outFields2 = input2->fields();
            #fields2Indices.reserve( outFields2.count() );
            #for ( int i = 0; i < outFields2.count(); ++i )
            #{
            #fields2Indices << i;
            #}
        #}
        #else
        #{
            #fields2Indices.reserve( fieldsToCopy.count() );
            #for ( const QString &field : fieldsToCopy )
            #{
            #int index = input2->fields().lookupField( field );
            #if ( index >= 0 )
            #{
                #fields2Indices << index;
                #outFields2.append( input2->fields().at( index ) );
            #}
            #}
        #}
        extension = self.parameterAsEnum(parameters, self.EXTENSION, context)

        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        Processor.checkFolder(self.output_folder) #the function needs to move to processor and feedback adapted


    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        for layout in self.selectedLayouts:
            Processor.exportCompo(layout, folder, title, extension)

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
