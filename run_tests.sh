#!/usr/bin/env bash

# skip tests

exit

git stash -k -u

# lint code in lib directory
echo "pylint --rcfile=.pylintrc src/blobtools/lib -f parseable -r n" &&
pylint --rcfile=.pylintrc src/blobtools/lib -f parseable -r n &&
# check codestyle
echo "pycodestyle src/blobtools/lib --max-line-length=120" &&
pycodestyle src/blobtools/lib --max-line-length=120 &&
# check docstyle
echo "pydocstyle src/blobtools/lib" &&
pydocstyle src/blobtools/lib &&

# lint code in test directory with alternate config
echo "pylint --rcfile=.pylintrc_tests tests/unit_tests/* -f parseable -r n" &&
pylint --rcfile=.pylintrc_tests tests/unit_tests/* -f parseable -r n &&
# check codestyle for tests
echo "pycodestyle tests/unit_tests/* --max-line-length=120" &&
pycodestyle tests/unit_tests/* --max-line-length=120 &&
# requiring docstrings for tests would be excessive so don't run pydocstyle

# run tests and generate coverage report
echo "py.test --ignore viewer --cov-config .coveragerc --doctest-modules --cov=lib --cov-report term-missing" &&
py.test --ignore viewer --cov-config .coveragerc --doctest-modules --cov=lib --cov-report term-missing

git stash pop
