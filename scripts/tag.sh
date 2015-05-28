#!/bin/bash -e

PROJECTNAME="groschmsc"
STARTDIR="$(pwd)"

if [ "${STARTDIR##*/}" != "${PROJECTNAME}" ] ; then
    echo "please start this script in the project directory"
    exit 2
fi

./main.py set_tag
git push --tags
