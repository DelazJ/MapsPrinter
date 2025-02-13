"""
/***************************************************************************
 MapsPrinter
                                 A QGIS plugin
 Export several print layouts to pdf, svg or image file format in one-click
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

import os.path
from functools import partial

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QUrl
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication, Qgis

from .processing_provider.maps_printer_provider import MapsPrinterProvider


class MapsPrinter:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.provider = MapsPrinterProvider()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(self.plugin_dir, "i18n", f"MapsPrinter_{locale}.qm")

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > "4.3.3":
                QCoreApplication.installTranslator(self.translator)

    # noinspection PyMethodMayBeStatic

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate("MapsPrinter", message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.initProcessing()
        # Create action that will start plugin help
        self.helpAction = QAction(
            QIcon(os.path.join(self.plugin_dir, "icons/icon.png")),
            self.tr("Maps Printer"),
            self.iface.mainWindow(),
        )
        if Qgis.QGIS_VERSION_INT < 31000:
            self.iface.addPluginToMenu("&Maps Printer", self.helpAction)
        else:
            self.iface.pluginHelpMenu().addAction(self.helpAction)

        # Connect the action to the docs method
        self.helpAction.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://delazj.github.io/MapsPrinter")
            )
        )

    def initProcessing(self):
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Removes the plugin provider, menu item and icon from QGIS GUI."""

        QgsApplication.processingRegistry().removeProvider("mapsprinter")

        if Qgis.QGIS_VERSION_INT < 31000:
            self.iface.removePluginMenu("&Maps Printer", self.helpAction)
        else:
            self.iface.pluginHelpMenu().removeAction(self.helpAction)

        del self.helpAction
