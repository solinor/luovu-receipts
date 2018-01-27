#!/bin/bash
# TODO: temporarily disable pylint results
# set -e
pylint --load-plugins pylint_django improve_stuff feedback --disable line-too-long --disable missing-docstring --disable no-self-use
exit 0
