#!/bin/bash -e

PROJECTNAME="groschmsc"
STARTDIR="$(pwd)"

if [ "${STARTDIR##*/}" != "${PROJECTNAME}" ] ; then
    echo "please start this script in the project directory"
    exit 2
fi

PROJECT_PY_FILES=$(find "${STARTDIR%}" -name "*.py" -not -path "${STARTDIR%}/python_modules/*" -not -path "${STARTDIR%}/bacnet/sandbox/pypy/*" -not -path "${STARTDIR%}/run/*" -not -path "${STARTDIR%}/docs/*" -not -path "${STARTDIR%}/bacnet/examples/*" -not -path "${STARTDIR%}/bacnet/run/*")

pylint --rcfile=pylint.rc $PROJECT_PY_FILES || true

if which cloc &>/dev/null ; then
    cloc $PROJECT_PY_FILES
fi
