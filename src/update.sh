#!/bin/bash

# Python interpreter
PYTHON="python3.11"
VENV_PATH="venv"

# Build a new venv from the requirements files.
rm -rf $VENV_PATH

$PYTHON -m venv $VENV_PATH

source $VENV_PATH/bin/activate

$PYTHON -m pip install -U pip
$PYTHON -m pip install -r requirements.txt