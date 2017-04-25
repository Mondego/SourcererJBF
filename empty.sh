#! /bin/sh

for dir in builds/*/*/build ; do
    [ -z "`find $dir -type f`" ] && echo "$dir is empty"
done
