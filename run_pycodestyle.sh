#!/bin/bash
set -e
pycodestyle --ignore E501,E402 --exclude=.git,dev3,dev .
