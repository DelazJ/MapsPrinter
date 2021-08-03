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
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QImageWriter

from qgis.core import QgsLayoutExporter, QgsFeedback

class Processor:
    """
    Utilities for managing layout export components
    """

    def listFormat(self):
        """List all the file formats we can export to."""

        formats = [
            'PDF format (*.pdf *.PDF)',
            'SVG format (*.svg *.SVG)',
            ]
        #Automatically add supported image formats instead of manually
        imageformats = QImageWriter.supportedImageFormats()
        for f in imageformats:
            fs = f.data().decode('utf-8')
            formats.append('{} format (*.{} *.{})'.format(fs.upper(), fs, fs.upper()))

        return formats

    def setFormat(self, value):
        """Retrieves the format suffix to append to the output file."""

        try:
            f = value.split()[2].strip('(*')
            # f = value.split('*')[1].strip()
        except:
            f = ''
        return f

    def findActiveDir(self, extension):
        """Find the last used directory depending on the format."""

        settings = QSettings()
        shortExt = self.setFormat(extension).lower()
        if shortExt == '.pdf' : # if extension is pdf
            dir = settings.value('/UI/lastSaveAsPdfFile')
        elif shortExt == '.svg' : # if extension is svg
            dir = settings.value('/UI/lastSaveAsSvgFile')
        else:
            dir = settings.value('/UI/lastSaveAsImageDir')

        return dir

    def exportCompo(self, cView, folder, title, extension, prefix=False, feedback=None):
        """Function that sets how to export files.
        Returns a file
        :param cView: The print layout to export
        :param folder: The folder in which to store the output file
        :param title: The print layout name
        :param extension: The file extension to use for the output
        :param prefix: A boolean whether the output should be prefixed with filename
        :return: A file representing the layout in the selected format
        """

        #self.msgWMSWarning(cView)

        myAtlas = cView.atlas()

        # Let's use custom export properties if there are
        exportSettings = self.overrideExportSettings(cView, extension)

        # Do the export process
        exporter = QgsLayoutExporter(cView)

        # Refresh the layout before printing
        exporter.layout().refresh()

        if myAtlas.enabled():
            if feedback is None:
                feedback = QgsFeedback()

            # If single file export is required (only compatible with pdf, yet)
            # singleFile can be True, False or None
            if cView.customProperty('singleFile') in [None, True] and extension == '.pdf':
                result, error = exporter.exportToPdf(myAtlas, os.path.join(folder, title + '.pdf'), exportSettings, feedback)

            else: #If instead multiple files will be output

                # Check if there's a valid expression for filenames,
                # and otherwise inform that a default one will be used and set it using the layout name.
                # replacement in the GUI is failing at the moment
                # if len(myAtlas.filenameExpression()) == 0:
                #     self.iface.messageBar().pushMessage(
                #         self.tr(u'Empty filename expression'),
                #         self.tr(u'The print layout "{}" has an empty output filename expression. {}_@atlas_pagename is used as default.').format(title, title),
                #         level = Qgis.Warning
                #         )
                #     myAtlas.setFilenameExpression(u"'{}_'||@atlas_pagename".format(title))

                # Store original expression
                user_expression = myAtlas.filenameExpression()
                if prefix:
                    myAtlas.setFilenameExpression(u"'{}_'||{}".format(QgsProject.instance().baseName(), user_expression ))
                
                current_fileName = myAtlas.filenameExpression()

                try:
                    # Export atlas to multiple pdfs
                    if extension =='.pdf':
                        result, error = exporter.exportToPdfs(myAtlas, os.path.join(folder, current_fileName), exportSettings, feedback)

                    # Export atlas to svg format
                    elif extension =='.svg':
                        result, error = exporter.exportToSvg(myAtlas, os.path.join(folder, current_fileName), exportSettings, feedback)

                    # Export atlas to image format
                    else:
                       result, error = exporter.exportToImage(myAtlas, os.path.join(folder, current_fileName), extension, exportSettings, feedback)

                finally:
                    # Reset to the user default expression
                    myAtlas.setFilenameExpression(user_expression)

            myAtlas.endRender()

        # If the composition has no atlas
        else:
            if extension == '.pdf':
                result = exporter.exportToPdf(os.path.join(folder, title + '.pdf'), exportSettings)

            elif extension == '.svg':
                result = exporter.exportToSvg(os.path.join(folder, title + '.svg'), exportSettings)

            else:
                result = exporter.exportToImage(os.path.join(folder, title + extension), exportSettings)

        return result == QgsLayoutExporter.Success

    def getResolution(self, layout, resolution):
        """Define the resolution to use during export (custom or layout)
        Returns an integer representing the resolution
        :param layout: The print layout to export
        :param resolution: The custom value set by user
        """

        global layoutDpi
        if resolution:
            layoutDpi = resolution
        else:
            # rely on value set in the layout properties dialog
            layoutDpi = layout.renderContext().dpi()

        return layoutDpi
    
    def overrideExportSettings(self, layout, extension):
        """Because GUI settings are not exposed in Python,
           we need to find and catch user selection and override
           export settings values with what is actually active in the GUI.
           See discussion at http://osgeo-org.1560.x6.nabble.com/Programmatically-export-layout-with-georeferenced-file-td5365462.html
        """

        if extension == '.pdf':
            # See QgsLayoutDesignerDialog::getPdfExportSettings
            # let's follow non-default values if set
            exportSettings = QgsLayoutExporter.PdfExportSettings()
            exportSettings.flags = layout.renderContext().flags()
            exportSettings.dpi = layoutDpi
            if layout.customProperty('rasterize') in ['true', True]:
                exportSettings.rasterizeWholeImage = True

            if layout.customProperty('forceVector') == 1:
                exportSettings.forceVectorOutput = True

            if layout.customProperty('pdfTextFormat') == 1:
                exportSettings.textRenderFormat = 1

            if layout.customProperty('pdfOgcBestPracticeFormat') == 1:
                exportSettings.useIso32000ExtensionFormatGeoreferencing = False
                exportSettings.useOgcBestPracticeFormatGeoreferencing = True

            if layout.customProperty('pdfExportThemes'):
                exportSettings.exportThemes = layout.customProperty('pdfExportThemes')

            if layout.customProperty('pdfIncludeMetadata') == 0:
                exportSettings.exportMetadata = False

            if layout.customProperty('pdfSimplify') == 0:
                exportSettings.simplifyGeometries = False

            if layout.customProperty('pdfCreateGeoPdf') == 1:
                exportSettings.writeGeoPdf = True

            if layout.customProperty('pdfAppendGeoreference') == 0:
                exportSettings.appendGeoreference = False

            if layout.customProperty('pdfExportGeoPdfFeatures') == 0:
                exportSettings.includeGeoPdfFeatures = False

        elif extension == '.svg':
            # See QgsLayoutDesignerDialog::getSvgExportSettings
            exportSettings = QgsLayoutExporter.SvgExportSettings()
            exportSettings.flags = layout.renderContext().flags()
            exportSettings.dpi = layoutDpi
            if layout.customProperty('forceVector') == 1:
                exportSettings.forceVectorOutput = True

            if layout.customProperty('svgIncludeMetadata') == 0:
                exportSettings.exportMetadata = False

            if layout.customProperty('svgSimplify') == 0:
                exportSettings.simplifyGeometries = False

            if layout.customProperty('svgGroupLayers')  in ['true', True]:
                exportSettings.exportAsLayers = True

            if layout.customProperty('svgTextFormat') == 1:
                exportSettings.textRenderFormat = 1

            if layout.customProperty('svgCropToContents') in ['true', True]:
                exportSettings.cropToContents = True
            # Todo: add margin values when cropping to content
            #exportSettings.cropMargins = ???QgsMargins???
            #if layout.customProperty('svgDisableRasterTiles')  in ['true', True] : ??? # to fine tune with flags FlagDisableTiledRasterLayerRenders

        else:
            # see QgsLayoutDesignerDialog::getRasterExportSettings for settings
            exportSettings = QgsLayoutExporter.ImageExportSettings()
            exportSettings.flags = layout.renderContext().flags()
            exportSettings.dpi = layoutDpi
            if layout.customProperty('exportWorldFile') in ['true', True]:
                exportSettings.generateWorldFile = True

            if layout.customProperty('imageCropToContents')  in ['true', True]:
                exportSettings.cropToContents = True
            # Todo: add margin values when cropping to content
            #exportSettings.cropMargins = ???QgsMargins???
            # exportSettings.exportMetadata = False # what's the corresponding layout's property? 
            # layout.customProperty('atlasRasterFormat') # overridden by extension 
            # # if layout.customProperty('imageAntialias') in ['true', True] : ??? # to fine tune with flags FlagAntialiasing

        return exportSettings

    #def msgEmptyPattern(self):
        #"""Display a message to tell there's no pattern filename for atlas
        #TODO: offer the ability to fill the pattern name.
        #"""
        #self.iface.messageBar().pushMessage(
            #self.tr(u'Empty filename pattern'),
                #self.tr(u'The print layout "{}" has an empty filename '\
                    #'pattern. {}_$feature is used as default.'
                    #).format(self.title, self.title),
            #level = Qgis.Warning
            #)

    #def msgWMSWarning(self, cView):
        #"""Show message about use of WMS layers in map"""

        #for elt in list(cView.composition().items()):
            #if isinstance(elt, QgsLayoutItemMap) and elt.containsWMSLayer():
                #self.iface.messageBar().pushMessage(
                    #'Maps Printer : ',
                    #self.tr(u'Project contains WMS Layers. '\
                    #'Some WMS servers have a limit for the width and height parameter. '\
                    #'Printing layers from such servers may exceed this limit. '\
                    #'If this is the case, the WMS layer will not be printed.'),
                    #level = Qgis.Warning
                #)
                ## once we found a map layer concerned, we get out to show just once the message
                #break


    # def checkFolder(self, outputDir):
        # """Ensure export's folder exists and is writeable."""

        # # It'd be better to find a way to check writeability in the first try...
        # try:
            # os.makedirs(outputDir)
            # # settings.setValue('/UI/lastSaveAsImageDir', outputDir)
        # except Exception as e:
            # # if the folder already exists then let's check it's writeable
            # if e.errno == errno.EEXIST:
                # try:
                    # testfile = tempfile.TemporaryFile(dir = outputDir)
                    # testfile.close()
                # except Exception as e:
                    # if e.errno in (errno.EACCES, errno.EPERM):
                        # QMessageBox.warning(None, self.tr(u'Unable to write in folder'),
                            # self.tr(u"You don't have rights to write in this folder. "\
                            # "Please, select another one!"),
                            # QMessageBox.Ok, QMessageBox.Ok)
                    # else:
                        # raise
                    # self.browseDir()
                # else:
                    # return True
            # # if the folder doesn't exist and can't be created then choose another directory
            # elif e.errno in (errno.EACCES, errno.EPERM):
                # QMessageBox.warning(None, self.tr(u'Unable to use the directory'),
                    # self.tr(u"You don't have rights to create or use such a folder. " \
                    # "Please, select another one!"),
                    # QMessageBox.Ok, QMessageBox.Ok)
                # self.browseDir()
            # # for anything else, let user know (mind if it's worth!?)
            # else:
                # QMessageBox.warning(None, self.tr(u'An error occurred : '),
                    # u'{}'.format(e), QMessageBox.Ok, QMessageBox.Ok)
                # self.browseDir()
        # else: # if it is created with no exception
            # return True

    # def setDefaultDir(self, extension):
        # """Find the last used directory depending on the format."""

        # settings = QSettings()
        # # keep in memory the output folder
        # if extension == '.pdf':
            # QSettings().setValue('/UI/lastSaveAsPdfFile', folder)
        # elif extension == '.svg':
            # QSettings().setValue('/UI/lastSaveAsSvgFile', folder)
        # else:
            # QSettings().setValue('/UI/lastSaveAsImageDir', folder)

