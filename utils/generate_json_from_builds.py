# Using a pre-existing builds folder, this generates a large json file
# with all the information required to rebuild the projects

import os, sys
import json

if len(sys.argv) != 3:
    print
    'ERROR, two arguments needed, input folder and output file name.'
    sys.exit(1)

folder = sys.argv[1]
destin = sys.argv[2]

results = dict()
for f1 in os.listdir(folder):
    for f2 in os.listdir(os.path.join(folder, f1)):
        results[os.path.join(f1, f2)] = json.load(open((os.path.join(folder, f1, f2, "build-result.json"))))

with open(destin, 'w') as fp:
    json.dump(results, fp)
