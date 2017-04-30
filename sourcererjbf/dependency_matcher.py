import ujson as json, os
from shutil import copyfile
from constants import PARTMAP, TEMPDIR, TIMEOUT_SECONDS
from subprocess32 import check_output, CalledProcessError
from fqn_to_jar_map_generator import get_all_fqns_from_path, invert
from fqn_to_jar_map_generator import get_locations_from_folder, search_and_save

FQN_TO_JAR_MAP = {}
FOLDER_PATH = ""
#KNOWN_JARS = json.load(open("known_jars.json"))

def load_fqns(folderpath, filename, threads):
  global FQN_TO_JAR_MAP, FOLDER_PATH
  FQN_TO_JAR_MAP = load_or_create(folderpath, filename, threads)
  FOLDER_PATH = folderpath

def load_or_create(folderpath, filename, threads):
  if not os.path.exists(filename):
    search_and_save(get_locations_from_folder(folderpath), filename, threads)
  return dict(json.load(open(filename)))

def build_fqn_to_jar(packages, fqn_map):
  jar_to_fqn = {}
  for package in packages:
    if package not in fqn_map:
      continue
    for jar in fqn_map[package]:
      jar_to_fqn.setdefault(jar, set()).add(package)
  return jar_to_fqn
  
def extract_deps_from_fqnmap(packages, jar_to_fqn):
  if len(packages) == 0:
    return True, []
  item = sorted(jar_to_fqn.iteritems(), key= lambda x: len(x[1]), reverse = True)[0][0]
  for jar in jar_to_fqn:
    if jar == item: continue
    jar_to_fqn[jar] = jar_to_fqn[jar] - jar_to_fqn[item]

def find_depends(packages, fqn_map):
  jar_to_fqn = build_fqn_to_jar(packages, fqn_map)
  sorted_jar_list = sorted(jar_to_fqn.items(), key= lambda x: len(x[1]), reverse = True)
  required_jars = list()
  found_packages = set()
  for jar, fqns in sorted_jar_list:
      found_packages.update(fqns)
      required_jars.append(jar)
      if found_packages == packages:
          break
  return found_packages == packages, required_jars

def create_jar_depends(depends, local = list()):
  return ([(None, None, None, False, copy_and_retrieve_path(depend), True) for depend in local]
          + [(None, None, None, False, copy_and_retrieve_path(depend), False) for depend in depends])

def FixDeps(threadid, packages, project):
  not_present = [pkg for pkg in set(packages) if pkg not in FQN_TO_JAR_MAP]
  if len(not_present) > 0:
    project["packages_not_in_fqnmap"] = not_present
    return False, project
      
  succ, depends = find_depends(set(packages), FQN_TO_JAR_MAP)
  if not succ:
    return False, project

  project["depends"] = create_jar_depends(depends)
  project["create_build"] = True
  return True, project

def FixDepsWithOwnJars(threadid, packages, project):
  local_fqn_map = find_and_scrape_jars(threadid, project)
  not_present_locally = [pkg for pkg in set(packages) if pkg not in local_fqn_map]
  remaining = set()
  depends = list()
  if len(not_present_locally) > 0:
    remaining = set(not_present_locally)
    not_present = [pkg for pkg in set(remaining) if pkg not in FQN_TO_JAR_MAP]
    if len(not_present) > 0:
      project["packages_not_in_fqnmap"] = not_present
      return False, project
  succ, depends_local = find_depends(set(packages), local_fqn_map)
  if len(remaining) > 0:
    succ, depends = find_depends(set(remaining), FQN_TO_JAR_MAP)
  if not succ:
    return False, project

  project["depends"] = create_jar_depends(depends, local = depends_local)
  project["create_build"] = True
  return True, project


def copy_file(depend_path, filename, existing_file_count):
  muse_jars = os.environ["MUSE_JARS"]
  splits = filename.split(".")
  filename = ".".join(splits[:-1])
  extension = splits[-1]
  folder = os.path.join(filename[0], filename)
  copy_path = os.path.join(folder, filename + str(existing_file_count) + "." + extension)
  fullfolder = os.path.join(muse_jars, folder) 
  fullpath = os.path.join(muse_jars, copy_path)
  if not os.path.exists(fullfolder):
    os.makedirs(fullfolder)
  copyfile(depend_path, fullpath)
  return copy_path

def copy_and_retrieve_path(depend_path):
  #filename = depend_path.split("/")[-1]
  #if filename in KNOWN_JARS:
  #  for actual_path, copy_path in KNOWN_JARS[filename]:
  #    if actual_path == depend_path:
  #      return "${env.MUSE_JARS}/" + copy_path
  #existing_file_count = len(KNOWN_JARS.setdefault(filename, []))
  #copy_path = copy_file(depend_path, filename, existing_file_count)
  #KNOWN_JARS[filename].append((depend_path, copy_path))
  return depend_path

def find_and_scrape_jars(threadid, project):
  srcpath = TEMPDIR.format(threadid)
  ownjars = [j for j in check_output(["find", srcpath, "-name", "*.jar"]).split("\n") if j != ""]
  jar_to_fqn_map = dict()
  for j in ownjars:
    try:
      check_output(["jarsigner", "-verify", j])
    except CalledProcessError, e:
      if "java.lang.SecurityException" in e.output: continue
    try:
      fqns = get_all_fqns_from_path(j)
      jar_to_fqn_map[j[len(srcpath):].lstrip("/")] = fqns
    except CalledProcessError:
      continue
  fqn_to_jars_local = invert(jar_to_fqn_map)
  return fqn_to_jars_local 
