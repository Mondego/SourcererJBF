#!/usr/bin/env python

#Takes a folder as input, looks at all subfolders, finds jar files 
#and figures out FQNs that exist in them
#
# Usage: ./fqn_to_jar_map_generator.py <file_with_jar_locations> <file_to_save_map> <root>

import sys, os, json, re, shelve
from multiprocessing import Process, Queue
from subprocess import check_output, call, CalledProcessError, STDOUT
from utils import create_logger

NUMBER_OF_THREADS = 20
logger = create_logger("fqn_to_jar")
ROOT = ""

def read_jar_locations(jaroutput):
  return open(jaroutput).read().split("\n")

def get_all_variations(fqn_parts):
  fqns = set([fqn_parts[0]])
  for i in range(1, len(fqn_parts) + 1):
    fqns.add(".".join(fqn_parts[:i]))
  return fqns

def invert(jar_to_fqn):
  fqn_to_jar = {}
  for jar in jar_to_fqn:
    for fqn in jar_to_fqn[jar]:
      fqn_to_jar.setdefault(fqn, []).append(jar)
  return fqn_to_jar

def shortened(path):
    if path.startwith(ROOT):
        return path[len(ROOT):]
    return path

def make_fqn_part(locations, threadid):
  logger.info("Starting thread " + str(threadid))
  jar_to_fqn_part = {}
  count = 0
  total = len(locations)
  shelveobj = shelve.open("save_" + str(threadid))
  badjarsshelve = shelve.open("badjars_" + str(threadid))
  for path in locations:
    bad = False
    try:
      check_output(["jarsigner", "-verify", path])
    except CalledProcessError, e:
      bad = "java.lang.SecurityException" in e.output
    if bad:
      badjarsshelve[path] = True
      badjarsshelve.sync()
      continue
    try:
      for line in check_output(["jar", "tf", path], stderr = STDOUT).split("\n"):
        if line.endswith(".class"):
          jar_to_fqn_part.setdefault(shortened(path), set()).update(
              get_all_variations([p for p in line[:-6].split("$")[0].split("/") if p != ".." or p != "."]))
      jar_to_fqn_part.setdefault(shortened(path), set())
      shelveobj[shortened(path)] = jar_to_fqn_part[shortened(path)]
      shelveobj.sync()

    except CalledProcessError, e:
      logger.error(path + "error" + str(e))
    except Exception, e:
      logger.error(path + "error" + str(e))
    count+=1
    if count%100 == 0:
      print "Thread " + str(threadid) + ": " + str(count) + "/" + str(total)

def reducequeue():
  jar_to_fqn = {}
  bad_jars = set()
  for i in range(NUMBER_OF_THREADS):
    print i
    part = dict(shelve.open("save_" + str(i)))
    for item in part:
      jar_to_fqn.setdefault(item, set()).update(part[item])
    badpart = dict(shelve.open("badjars_" + str(i)))
    bad_jars.update(set(badpart.keys()))
  open("badjars.txt", "w").write("\n".join(bad_jars) + "\n")
  return jar_to_fqn

def make_fqn_map(jar_locations, tc):
  global NUMBER_OF_THREADS
  NUMBER_OF_THREADS = tc
  threads = []
  jar_to_fqn = {}

  for i in range(NUMBER_OF_THREADS):
    threads.append(Process(target = make_fqn_part, args=(jar_locations[i::NUMBER_OF_THREADS], i)))
    threads[-1].daemon = True
    threads[-1].start()
   

  for i in range(NUMBER_OF_THREADS):
    threads[i].join()
  logger.info("Starting reduce and invert")
  return invert(reducequeue())
  

def search_and_save(jarlocations, savefile, threads):
  json.dump(
      make_fqn_map(jarlocations, threads),
      open(savefile, "w"),
      sort_keys=True, 
      indent=4, 
      separators=(',', ': '))

def get_locations_from_folder(location):
  try:
    return check_output(["find", location, "-name", "*.jar"]).split("\n")
  except CalledProcessError:
    print "Error when trying to find jars in folder", location

if __name__ == "__main__":
  global ROOT
  if len(sys.argv) < 3:
    print "Usage: ./fqn_to_jar_map_generator.py <file_with_jar_locations> <file_to_save_map> [<root>]"
    sys.exit(0)
  if len(sys.argv) == 4:
      ROOT = sys.argv[3]
  search_and_save(read_jar_locations(sys.argv[1]), sys.argv[2], NUMBER_OF_THREADS)




