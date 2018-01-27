#!/bin/bash
set -e
isort --diff --check --recursive receipts receipt_checking *.py
