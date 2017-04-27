#! /bin/sh

for dir in $1/*/* ; do
    if [ ! -d "$dir/build" ];  then
      echo "$dir does not have build folder"
    else
      [ -z "`find $dir/build -type f`" ] && echo "$dir is empty"
    fi
done
