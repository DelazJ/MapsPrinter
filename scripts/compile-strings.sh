#!/bin/bash
LOCALES=$*

for LOCALE in ${LOCALES}
do
    echo "MapsPrinter/i18n/MapsPrinter_"${LOCALE}".ts"
    # echo "MapsPrinter/i18n/"${LOCALE}".ts"
    # Note we don't use pylupdate with qt .pro file approach as it is flakey
    # about what is made available.
    lrelease i18n/MapsPrinter_${LOCALE}.ts
    # lrelease i18n/${LOCALE}.ts
    # lrelease-qt4 i18n/${LOCALE}.ts
done
