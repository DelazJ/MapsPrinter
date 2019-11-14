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

import os.path
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtCore import QSettings, QUrl

class GuiUtils:
    """
    Utilities for GUI plugin components
    """

    @staticmethod
    def get_icon(icon: str):
        """
        Returns a plugin icon
        :param icon: icon name (svg file name)
        :return: QIcon
        Inspired by SLYR plugin
        """
        path = os.path.join(
            os.path.dirname(__file__),
            'icons',
            icon)
        if not os.path.exists(path):
            return QIcon()

        return QIcon(path)

    def showHelp():
        """Shows the help page."""

        locale = QSettings().value('locale/userLocale')[0:2]
        help_file = os.path.join(
            os.path.dirname(__file__),
            'help/help_{}.html'.format(locale)
            )
        help_file_en = os.path.join(
            os.path.dirname(__file__),
            'help/help.html')

        if os.path.exists(help_file):
            QDesktopServices.openUrl(QUrl('file:///'+ help_file))
            #QDesktopServices.openUrl(QUrl(help_file))
        else:
            QDesktopServices.openUrl(QUrl('file:///'+ help_file_en))
            # QDesktopServices.openUrl(QUrl(
                # 'file:///'+# self.plugin_dir + '/help/help.html')
                # os.path.join(
                    # os.path.dirname(__file__),
                    # '/help/help.html')
                # )
            # )
