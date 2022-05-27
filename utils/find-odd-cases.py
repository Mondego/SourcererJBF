from subprocess import check_output
import os, sys
import simplejson as json

total = 0
type1 = 0
type2 = 0
failures = 0

folder_input = sys.argv[1]

for pid in json.load(open('project_details.json', 'r')):
    total += 1
    if not os.path.exists(os.path.join(folder_input, str(pid))):
        continue
    build_json = json.load(open(os.path.join(folder_input, str(pid) + '/build-result.json'), 'r'))
    if (build_json['success']) and (
            check_output(['find', os.path.join(folder_input, str(pid) + '/build'), '-name', '*.class'],
                         encoding='utf8') == ''):
        if (build_json['create_build']):
            type1 += 1
        if not (build_json['create_build']):
            type2 += 1
    if (not build_json['success']):
        failures += 1

print('Total: ', total)
print('Type1: ', type1)
print('Type2: ', type2)
print('Fail : ', failures)
