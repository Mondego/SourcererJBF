import json, re, shelve
import cPickle
from multiprocessing import Process

THREADCOUNT = 112


def get_all_variations(fqn_parts):
    fqns = set([fqn_parts[0]])
    for i in range(1, len(fqn_parts) + 1):
        fqns.add(".".join(fqn_parts[:i]))
    return fqns


def get_all_fqns_from_line(line):
    all_paths = set()
    line = line.strip()
    if line.endswith(".class"):
        new_line = "/".join(l for l in line[:-6].split("$") if not re.match(r"\d+", l))
        all_paths.update(get_all_variations([p for p in new_line.split("/") if p != ".." and p != "."]))
    return all_paths


jar_details = json.load(open("jar_details.json"))
print
"Loaded jar details"
class_to_jarmap_full = dict()


def convert_set_to_list(themap):
    for key in themap:
        themap[key] = list(themap[key])


def jarpathmapper(i, jarpaths):
    count = 0
    class_to_jarmap = dict()
    for jarpath in jarpaths:
        count += 1
        if count % 100 == 0:
            print
            "JMAPPER", i, count, len(jar_details)
        jar = jarpath[len("/extra/lopes1/mondego-data/jars/"):]
        for line in jar_details[jarpath]:
            if line.endswith(".class"):
                class_to_jarmap.setdefault(line, set()).add(jar)
    print
    "Converting set to list", i
    convert_set_to_list(class_to_jarmap)
    print
    "Converted set to list", i
    json.dump(class_to_jarmap, open("saves/jarpathmapper_%d" % i, "w"))
    print
    "Done", i


def jarpathreducer():
    for i in range(THREADCOUNT):
        partmap = json.load(open("saves/jarpathmapper_%d" % i))
        for cls in partmap:
            class_to_jarmap_full.setdefault(cls, set()).update(set(partmap[cls]))
        print
        "Completed saves/jarpathmapper_%d" % i


jmappers = list()
jarslist = list(jar_details)
# for i in range(THREADCOUNT):
#  jmappers.append(Process(target = jarpathmapper, args = (i, jarslist[i::THREADCOUNT])))
#  jmappers[-1].daemon = True
#  jmappers[-1].start()

# print "JMAPPERS started"

# for i in range(THREADCOUNT):
#  jmappers[i].join()

print
"JMAPPERS FINISHED"

# jarpathreducer()

print
"JREDUCE DONE"
fqn_to_jarmap_full = dict()
print
"Inverted jar details", len(class_to_jarmap_full)


def expand_mapper(i, lines):
    fqn_to_jarmap = dict()
    count = 0
    for cls in lines:
        count += 1
        if count % 100 == 0:
            print
            "EXTHREAD", i, count, len(lines)
        all_fqns = get_all_fqns_from_line(cls)
        if all_fqns != set():
            for fqn in all_fqns:
                if fqn and fqn != "org" and fqn != "com":
                    fqn_to_jarmap.setdefault(fqn, set()).update(class_to_jarmap_full[cls])
    print
    "Converting set to list", i
    convert_set_to_list(fqn_to_jarmap)
    print
    "Finished converting set to list", i
    json.dump(fqn_to_jarmap, open("saves/expandmapper_%d" % i, "w"))
    print
    "Done", i


def expand_reducer():
    for i in range(THREADCOUNT):
        part_map = json.load(open("saves/expandmapper_%d" % i))
        for key in part_map:
            fqn_to_jarmap_full.setdefault(key, set()).update(set(part_map[key]))
    print
    "Completed saves/expandmapper_%d" % i


# cPickle.dump(class_to_jarmap_full, open("class_to_jarmap_full.json", "w"))
class_to_jarmap_full = shelve.open("saves/class_to_jarmap_full")
# for key, values in cPickle.load(open("class_to_jarmap_full.json")).iteritems():
#  try:
#    class_to_jarmap_full[str(key)] = values
#    class_to_jarmap_full.sync()
#  except UnicodeEncodeError:
#    continue

emappers = list()
alllines = list(class_to_jarmap_full)
for i in range(THREADCOUNT):
    emappers.append(Process(target=expand_mapper, args=(i, alllines[i::THREADCOUNT])))
    emappers[-1].daemon = True
    emappers[-1].start()

print
"STarted all expand mappers"
for i in range(THREADCOUNT):
    emappers[i].join()
print
"Completed all expand mappers"
expand_reducer()
print
"Completed expand reducer"
convert_set_to_list(fqn_to_jarmap_full)
print
"Converted set to list"
json.dump(fqn_to_jarmap_full, open("fqn_to_jars.json.new", "w"), indent=4, separators=(',', ': '), sort_keys=True)
print
"Done"
