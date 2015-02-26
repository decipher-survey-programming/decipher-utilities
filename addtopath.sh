#!/bin/bash

${1?"Usage: $0 script1 [script2] [...]"}

for script_path in $@; do
    if [ -x $script_path ]; then
        script_name=$(basename $script_path | sed 's/\.[a-zA-Z0-9]\+//');
        ln -s $(readlink -f $script_path) ~/bin/${script_name};
    fi
done
