#!/bin/bash

# https://packaging.python.org/en/latest/tutorials/packaging-projects/

# Abort if error
set -xe

rm -r ./dist
python -m pip install --upgrade build
python -m build

