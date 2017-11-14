#!/bin/sh

rm -rfv build/* dist/* docs/* docsrc/source/* \
    && make -C docsrc apidoc html \
    && python setup.py sdist bdist_wheel
