# This script is a diff between two build folders

from subprocess import check_output
import json, os, sys, glob

build_folder_1 = sys.argv[1]
build_folder_2 = sys.argv[2]

not_found = 0
# Success 2 Failure
s2f = 0
# Failure to Success
f2s = 0

filesDepth3 = glob.glob(os.path.join(build_folder_1,'*','*'))
dirsDepth3 = filter(lambda f: os.path.isdir(f), filesDepth3)

for proj_dir in dirsDepth3:

  aux = proj_dir.split(os.path.sep)
  proj_dir_2 = os.path.join(build_folder_2,aux[1],aux[2])
  json_file_2 = os.path.join(proj_dir_2,'build-result.json')

  if not os.path.isfile(json_file_2):
    not_found += 1
    continue

  build_json2 = json.load(open(json_file_2,'r'))
  build_json = json.load(open(os.path.join(proj_dir,'build-result.json'),'r'))


  if (build_json['success']) and (not build_json2['success']):
    print 'S2F:',proj_dir
    s2f += 1

  if (not build_json['success']) and (build_json2['success']):
    #print 'F2S:',proj_dir
    f2s += 1

print 'In the first but no in the second:',not_found
print 'Success2Failure:',s2f
print 'Failure2Success:',f2s

