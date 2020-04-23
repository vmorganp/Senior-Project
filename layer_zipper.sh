#!/bin/bash
set -e
ZIP_PATH=$(pwd)/layer.zip
uname -a 
pip --version

pip3 install virtualenv
virtualenv -p python3.7 venv
. ./venv/bin/activate
mkdir python
pip3 install -r requirements.txt -t ./python/
mv ./meta/* ./python/
# normally I'd touch ./python/__init__.py here but we already have that in meta
zip -r repiece_layer.zip ./python %1>/dev/null %2>/dev/null # this won't output anyway due to how it's run, but it can screw up the next line returning properly
# returning this so we can wait on it in the terraform 
echo "{ \"success\": \"true\"}"

