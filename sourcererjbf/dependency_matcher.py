import ujson as json, os
from shutil import copyfile


FQN_TO_JAR_MAP = {}
FOLDER_PATH = ""
#KNOWN_JARS = json.load(open("known_jars.json"))

def load_fqns(folderpath, filename, threads):
  global FQN_TO_JAR_MAP, FOLDER_PATH
  FQN_TO_JAR_MAP = load_or_create(folderpath, filename, threads)
  FOLDER_PATH = folderpath

def load_or_create(folderpath, filename, threads):
  if not os.path.exists(filename):
    from fqn_to_jar_map_generator import get_locations_from_folder, search_and_save
    search_and_save(get_locations_from_folder(folderpath), filename, threads)
  return json.load(open(filename))

def find_depends(packages):
  if len(packages) == 0:
    return True, []
  jar_to_fqn = {}
  for package in packages:
    if package not in FQN_TO_JAR_MAP:
      return False, []
    for jar in FQN_TO_JAR_MAP[package]:
      jar_to_fqn.setdefault(jar, set()).add(package)
  item = sorted(jar_to_fqn.items(), key= lambda x: len(x[1]), reverse = True)[0][0]
  return True, [item] + find_depends(packages - jar_to_fqn[item])[1]

def create_jar_depends(depends):
  return [(None, None, None, False, copy_and_retrieve_path(depend)) for depend in depends]  

def FixDeps(threadid, packages, project):
  succ, depends = find_depends(set(packages))
  if not succ:
    return False, project

  project["depends"] = create_jar_depends(depends)
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
