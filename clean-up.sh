#!/bin/bash

#project_details.json
#/builds
#/TBUILD
#/Uncompress
#badjars.txt
#badjars_*
#save_*
#fqn_to_jar.log
#fqn-to-jar-.shelve

echo "Cleaning TBUILD Uncompress builds"
rm -rf TBUILD Uncompress builds ./env-test/builds/* ./env-test/*.json ./env-test/*.shelve
echo "Cleaning badjars.txt badjars_* save_* fqn_to_jar.log fqn-to-jar-.shelve project_details.json"
rm -rf badjars.txt badjars_* save_* *.log *.shelve *.json
