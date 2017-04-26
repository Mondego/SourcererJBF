# This script grabs a project_details.json and copies all the jars to a given folder.
# To run:
#$ python this_script.py project_details.json destination

import sys, os
import json
from shutil import copy2

print '** WARNING ** This script uses a fair amount of custom paths so look inside before using it'
sys.exit(1)

pd = json.load(open(sys.argv[1],'r'))

s = set(dep[4] for pid in pd if "depends" in pd[pid] for dep in pd[pid]["depends"])
#s = map(lambda x: x.replace('../..','/extra/lopes1/mondego-data') , s)

for jar in s:
  corpus_directory = jar.replace('../../','')
  corpus_directory = os.path.abspath( os.path.join(sys.argv[2],corpus_directory[:(corpus_directory.rfind('/')+1)]) )
  if not os.path.exists(corpus_directory):
    os.makedirs(corpus_directory)

  print jar.replace('../..','/extra/lopes1/mondego-data')
  print corpus_directory
  copy2(jar.replace('../..','/extra/lopes1/mondego-data'),corpus_directory)

#print s

