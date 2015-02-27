#!/bin/bash

${1?"Usage: $0 script1 [script2] [...]"}

for scriptpath in $@; do
    if [ -x $script_path ]; then
        scriptname=$(basename "$scriptpath");
        scriptname="${scriptname%.*}";
        ln -s $(readlink -f $scriptpath) ~/bin/${scriptname};
    fi
done
