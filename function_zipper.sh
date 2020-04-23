#!/bin/bash
ZIP_PATH=$(pwd)/$1
zip -r -X $ZIP_PATH $2 %1>/dev/null %2>/dev/null
echo {"success":"true"}