#!/bin/bash

### Temp docker syntax checker script. Doesnt really check something...
set -e
for file in $(find . -name 'Dockerfile.j2')
do
    fgrep -q FROM $file || echo 'Miss/ wrong FROM section in file' $file
    fgrep -q MAINTAINER $file || echo 'Miss/ wrong MAINTAINER section in file' $file
done
