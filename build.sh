#!/bin/bash

# https://packaging.python.org/en/latest/tutorials/packaging-projects/

rm -r ./dist
python -m pip install --upgrade build
python -m build

