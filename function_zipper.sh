#!/bin/bash
# yes it's hardcoded and I don't like it either but it didn't want to play nice with vars
zip -r -X docScanner.zip docScanner.py %1>/dev/null %2>/dev/null
echo '{"name":"docScanner.zip"}'