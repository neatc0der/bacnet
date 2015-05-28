#!/bin/bash -e

PROJECTNAME="bacnet"
PYTHONENV="python_modules"

BACPYPES_SVN_DIR="svn_bacpypes"
BACPYPES_SVN_URL="http://svn.code.sf.net/p/bacpypes/code/trunk"

PYPY_HG_DIR="bacnet/sandbox/pypy"
PYPY_HG_URL="https://bitbucket.org/pypy/pypy"
PYPY_COMPILED="bacnet/sandbox/pypy-sandbox"
PYPY_TMP="pypy/pypy/sandbox/tmp"
SANDBOX_TMP="bacnet/sandbox/tmp"

WEBGUI_DIR="bacnet/webgui/"

ABLIB_GIT_DIR="git_ablib"
ABLIB_GIT_URL="git://github.com/tanzilli/ablib.git"

function preadlink(){
    python -c "import os.path;print(os.path.realpath('${1}'))"
}

STARTDIR="$(pwd)"
if ! which svn &>/dev/null ; then
    echo "svn not installed!"
    exit 1
fi
if ! which pip &>/dev/null ; then
    echo "pip not installed!"
    exit 1
fi
if ! which virtualenv &>/dev/null ; then
    echo "no virtualenv installed, installing"
    if ! pip install virtualenv ; then
        echo "pip was unable to install virtualenv"
        exit 1
    fi
fi

if [ "${STARTDIR##*/}" == "${PROJECTNAME}" ] ; then
    REQS="$(preadlink "requirements.txt")"
else
    echo "please start this script in the project directory"
    exit 2
fi

mkdir -p "${STARTDIR}/run"

if cd "${WEBGUI_DIR}"; then
    if ! [ -e "db" ]; then
        mkdir -p db
        ./manage.py syncdb --noinput
    fi
    cd "${STARTDIR}"
fi

if [ -z "${VIRTUAL_ENV}" ] ; then
    if ! [ -e "${PYTHONENV}" ] ; then
        if ! which virtualenv &>/dev/null ; then
            echo "virtualenv not in path!"
            exit 3
        fi
        virtualenv "${PYTHONENV}"
    fi
    . "${PYTHONENV}/bin/activate"
    if [ -z "${VIRTUAL_ENV}" ] ; then
        echo "unable to get python environment"
        exit 4
    fi

    rm activate &>/dev/null || true
    ln -s "${PYTHONENV}/bin/activate" "activate"
fi
if [ ! -d "${VIRTUAL_ENV}" ] ; then
    echo "virtual env ${VIRTUAL_ENV} is not a directory"
    exit 5
fi

if [ ! -e "${REQS}" ] ; then
    echo "please start this script in the project directory! (requirements.txt not found)"
    exit 6
fi

find . -type f -name '*.py[cp]' -delete || true


# bacpypes

if [ -d "${BACPYPES_SVN_DIR}" ] ; then
    rm -rf "${BACPYPES_SVN_DIR}" &>/dev/null || echo "unable to remove existing bacpypes directory"
fi
if ! svn checkout "${BACPYPES_SVN_URL}" "${BACPYPES_SVN_DIR}" ; then
    echo "unable to clone bacpypes using svn"
    exit 7
fi
if ! cd "${BACPYPES_SVN_DIR}" ; then
    rm -rf "${BACPYPES_SVN_DIR}" &>/dev/null || true
    echo "unable to change to bacpypes directory"
    exit 8
fi

echo "installing bacpypes"
if ! python setup.py install ; then
    cd "${STARTDIR}" && rm -rf "${BACPYPES_SVN_DIR}" &>/dev/null || echo "unable to remove bacpypes directory"
    echo "python encountered a problem during bacpypes install"
    exit 9
fi

cd "${STARTDIR}"

rm -rf "${BACPYPES_SVN_DIR}" &>/dev/null || echo "unable to remove bacpypes directory"


# ablib

if [ "$(uname -n)" == "ariag25" ] ; then
    echo "install ablib dependency"
    pip install --upgrade smbus-cffi pyserial || echo "make sure to install libi2c-dev and i2c-tools "

    if [ -d "${ABLIB_GIT_DIR}" ] ; then
        rm -rf "${ABLIB_GIT_DIR}" &>/dev/null || echo "unable to remove existing ablib directory"
    fi
    if ! git clone "${ABLIB_GIT_URL}" "${ABLIB_GIT_DIR}" ; then
        echo "unable to clone ablib using git"
        exit 7
    fi
    if ! cd "${ABLIB_GIT_DIR}" ; then
        rm -rf "${ABLIB_GIT_DIR}" &>/dev/null || true
        echo "unable to change to ablib directory"
        exit 8
    fi

    echo "installing ablib"
    if ! python setup.py install ; then
        cd "${STARTDIR}" && rm -rf "${ABLIB_GIT_DIR}" &>/dev/null || echo "unable to remove ablib directory"
        echo "python encountered a problem during ablib install"
        exit 9
    fi

    cd "${STARTDIR}"

    rm -rf "${ABLIB_GIT_DIR}" &>/dev/null || echo "unable to remove ablib directory"
else
    echo "ablib will not be installed - dummies are used"
fi


# pypy source code

if [ ! -d "${PYPY_HG_DIR}" ] ; then
    if ! which hg &>/dev/null ; then
        echo "WARNING: mercurial seems to be missing - no sandbox support"
    else
        echo "cloning pypy - this might take a while ..."
        if ! hg clone "${PYPY_HG_URL}" "${PYPY_HG_DIR}" -b release-2.5.x ; then
            echo "WARNING: unable to clone pypy using mercurial"
        else
# as los as pypy sandbox is damaged, this line must be commented out
#            cp -r "${PYPY_COMPILED}"/* "${PYPY_HG_DIR}/pypy/goal/"
            if ! which pypy &>/dev/null ; then
                echo "WARNING: please install pypy, otherwise sandbox will fail"
            fi
        fi
    fi
fi

if [ ! -e "${SANDBOX_TMP}" ] ; then
    cd ${SANDBOX_TMP%/*}
    if [ ! -d "${PYPY_TMP}" ] ; then
        mkdir -p "${PYPY_TMP}"
    fi
    ln -s "${PYPY_TMP}" "$(basename ${SANDBOX_TMP})"
    cd ${STARTDIR}
fi


if [ -e ".git/hooks" ] && [ ! -e ".git/hooks/pre-commit" ] ; then
    cat <<EOF > .git/hooks/pre-commit
#!/bin/bash -e
git-pylint-commit-hook --pylint-params ""
EOF
    chmod +x .git/hooks/pre-commit
fi

echo pip install --upgrade -r "${REQS}"
pip install --upgrade -r "${REQS}"

if [ ! -e "BACnet.ini" ] ; then
    echo -e "\nConfiguration:"
    ./main.py config
fi
