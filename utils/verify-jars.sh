#! /bin/bash

counter=0
for f in jars/*/*.jar jars/*/*/*.jar jars/*/*/*/*.jar; do
    if [ -f "$f" ]; then
        counter=$((counter+1))

        str=`jarsigner -verify "$f"`
        if [[ $str == *"SecurityException"* ]]; then
          echo "$f"
          echo -e  "$f" >> bad-jars
        fi
    fi
done

echo "Counted $counter jars"

