#!/usr/bin/env python

#Takes a folder as input, looks at all subfolders, finds jar files 
#and figures out FQNs that exist in them
#
# Usage: ./compile_checker.py -r <Root Directory>

import os, zipfile, shelve, shutil, json, sys, re, argparse, time
from multiprocessing import Process, Lock, Queue
from threading import Thread
from subprocess32 import check_output, call, CalledProcessError, STDOUT, Popen, PIPE, TimeoutExpired

import output_analyzer, encode_fixer, dependency_matcher

from constants import PARTMAP, TEMPDIR, TIMEOUT_SECONDS

THREADCOUNT = 50
PATH_logs = "logs"
JAR_REPO = ""
ignore_projects = set()

# Causes infinite loop
def FindAll(output, error_type):
  return [item for item in output if item["error_type"] == error_type]

def TryNewBuild(project, threadid, output):
  project["create_build"] = True
  return True, output, project

def OwnBuild(project, threadid, output):
  project["create_build"] = False
  try:
    srcdir = TEMPDIR.format(i)
    project["has_own_build"] = check_output(["find", srcdir, "-name", "build.xml"]) != ""
  except CalledProcessError:
    project["has_own_build"] = False

  return True, output, project

def EncodeFix(project, threadid, output):
  all_encoding = FindAll(output, "unmappable character")
  if not all_encoding:
    return False, output, project
  files = [item["filename"] for item in all_encoding]
  succ, project = encode_fixer.FixEncoding(threadid, files, project)
  return succ, output + ([{"error_type": "Too many encoding types detected"}] if not succ else []), project

def FixMissingDeps(project, threadid, output):
  all_package_errors = FindAll(output, "package not found")
  if not all_package_errors:
    return False, output, project
  packages = [item["package"] for item in all_package_errors]
  succ, project = dependency_matcher.FixDeps(threadid, packages, project)
  return succ, output + ([{"error_type": "Missing packages"}] if not succ else []), project  

def FixMissingDepsWithOwnJars(project, threadid, output):
  all_package_errors = FindAll(output, "package not found")
  if not all_package_errors:
    return False, output, project
  packages = [item["package"] for item in all_package_errors]
  succ, project = dependency_matcher.FixDepsWithOwnJars(threadid, packages, project)
  return succ, output + ([{"error_type": "Missing packages"}] if not succ else []), project  


def build_as_is(project, threadid, output):
  return True, output, project

def Analyze(output):
  return output_analyzer.Categorize(output)

def Compile(threadid, generated_build):
  try:
    srcdir = TEMPDIR.format(threadid)
    findjava = check_output(["find", srcdir, "-name", "*.java"], timeout = TIMEOUT_SECONDS)
    if findjava == "":
      return False, [{"error_type": "No Java Files"}], "", ""
    if not generated_build:
      findbuild = check_output(["find", srcdir, "-name", "build.xml"], timeout = TIMEOUT_SECONDS).split()
      if findbuild != []:
        try:
          findbuild = findbuild[0]
          command = " ".join(["ant", "-f", findbuild.strip()[len(srcdir):], "compile"])
          #print findbuild.strip()
          return True, check_output(["ant", "-f", findbuild.strip(), "compile"], stderr = STDOUT, timeout = TIMEOUT_SECONDS), command, ""
        except CalledProcessError, e:
          return False, Analyze(e.output), command, e.output
    else:
      try:
        command = "ant -f build.xml compile"
        project["timing"].append(("start_build", time.time()))
        output = check_output(["ant", "-f", os.path.join(srcdir, "build.xml"), "compile"], stderr = STDOUT, timeout = TIMEOUT_SECONDS)
        project["timing"].append(("end_build", time.time()))
        return True, output, command, ""
      except CalledProcessError, e:
        return False, Analyze(e.output), command, e.output
    return False, [{"error_type": "No Build File"}], "", ""
  except TimeoutExpired:
    return False, [{"error_type": "Timeout expired"}], "", ""


def copyrecursively(source_folder, destination_folder):
  #print "Hi Im here"
  for root, dirs, files in os.walk(source_folder):
    for item in files:
        src_path = os.path.join(root, item)
        dst_path = os.path.join(destination_folder, src_path.replace(source_folder+"/", ""))
        if os.path.exists(dst_path):
            if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                shutil.copy2(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
    for item in dirs:
        src_path = os.path.join(root, item)
        dst_path = os.path.join(destination_folder, src_path.replace(source_folder+"/", ""))
        if not os.path.exists(dst_path):
            os.mkdir(dst_path)
  #print "Hi Im leaving"

def unzip(zipFilePath, destDir):
  try:
    zip_ref = zipfile.ZipFile(zipFilePath, 'r')
    zip_ref.extractall(destDir)
    zip_ref.close()
    #print "Success ", zipFilePath, destDir
  except Exception as e:
    pass

def RemoveTouched(projects):
  if os.path.exists("TBUILD"):
    for f in os.listdir("TBUILD"):
      if f.endswith(".shelve"):
        save = shelve.open("TBUILD/" + f)
        projects = [project for project in projects if project["file"] not in save and project["file"] not in ignore_projects]
        save.close()
    return projects
  else:
    return projects

def MakeBuild(project, threadid):
  classpath = ""
  mavenline = ""
  if "depends" in project:
    depends = set([(a,b,c,d,e,f) for a,b,c,d,e,f in project["depends"]])
    mavendepends = set([d for d in depends if d[3]])
    mavenline = "\n  ".join([d[4] for d in mavendepends])
    jardepends = depends - mavendepends
    jarline = "\n        ".join(["<pathelement path=\"{0}\" />".format(os.path.join("../..", JAR_REPO, d[4].encode("ascii", "xmlcharrefreplace")) if not d[5] else d[4].encode("ascii", "xmlcharrefreplace")) for d in jardepends])
    if jarline or mavenline:
      if mavenline:
        classpath += "\n      <classpath refid=\"default.classpath\" />"
      if jarline:
        classpath= "\n      <classpath>\n        " + jarline + "\n      </classpath>"

  desc = project["description"] if "description" in project else ""
  ivyfile = open("xml-templates/ivy-template.xml", "r").read().format(project["name"]  if "name" in project else "compile_checker_build", mavenline)
  buildfile = open("xml-templates/build-template.xml", "r").read().format(project["name"] if "name" in project else "compile_checker_build", desc, classpath, "${build}", "${src}", project["encoding"] if "encoding" in project else "utf8", os.path.join("../..", JAR_REPO, "ext"))
  srcdir = TEMPDIR.format(threadid)
  open(os.path.join(srcdir, "ivy.xml"), "w").write(ivyfile)
  open(os.path.join(srcdir, "build.xml"), "w").write(buildfile)
  return ivyfile, buildfile

def TryCompile(trynumber, project, methods, threadid, output):
  ivyfile, buildfile, command = "", "", "ant -f build.xml compile"
  try:
    if project["type"] == "android":
      project["type"] = "normal"
      project["was_android"] = True
      return TryCompile(trynumber, project, methods, threadid, output)
    else:
      succ, output, project = methods[trynumber](project, threadid, output)
      project["timing"].append(("end_prep_%d" % trynumber, time.time()))
      if succ:
        if project["create_build"]:

          # LOG: 

          ivyfile, buildfile = MakeBuild(project, threadid)
          project["timing"].append(("end_make_buildfiles_try_%d" % trynumber, time.time()))
        succ, output, command, full_output = Compile(threadid, project["create_build"])
        project["timing"].append(("end_compile_try_%d" % trynumber, time.time()))
        project["full_output"] = full_output
        if succ:
          if not project["create_build"]:
            project["build_method"] = 'project_build_file'
          else:
            project["build_method"] = 'general_build_file'

          return succ, output, [("ivy.xml", ivyfile), ("build.xml", buildfile)], command
    
      trynumber += 1
      if trynumber == len(methods):
        return succ, output, [("ivy.xml", ivyfile), ("build.xml", buildfile)], command

      return TryCompile(trynumber, project, methods, threadid, output)
  except TimeoutExpired:
    return False, [{"error_type": "Timeout Expired"}]
  except Exception, e:
    raise
    return False, [{"error_type": "python exception", "error": str(e)}], [], ""

def CopyTarget(projectpath, threadid):
  copyrecursively(projectpath, TEMPDIR.format(threadid))
  check_output(["chmod", "-R", "+w", TEMPDIR.format(threadid)])

def CopyBuildFiles(project, threadid, outdir, buildfiles, succ):
  if succ:
    dstpath = os.path.join(outdir, project["file"], "build")
  dstpath2 = os.path.join(outdir, project["file"], "custom_build_script")
  
  if succ:
    check_output(["mkdir", "-p", dstpath])
  check_output(["mkdir", "-p", dstpath2])

  if succ:
    copyrecursively(os.path.join(TEMPDIR.format(threadid), "build"), dstpath)
  for (filename, content) in buildfiles:
    open(os.path.join(dstpath2, filename), "w").write(content)

def SaveOutput(save, project, succ, output, outdir, command):
  project.update({ "success": succ, "output": output })
  project_path = os.path.join(outdir, project["file"])
  if not os.path.exists(project_path):
    check_output(["mkdir", "-p", project_path])
  json.dump(project, open(os.path.join(project_path, "build-result.json"), "w"), sort_keys = True, indent = 4, separators = (",", ": "))
  open(os.path.join(project_path, "build.command"), "w").write(command)
  #print type(project["file"]), type(project)
  save[project["file"]] = project
  save.sync()

def make_dir(outdir, keep_old = False):
  if os.path.exists(outdir):
    if keep_old:
      return
    call(["rm", "-r", "-f", outdir])
  os.makedirs(outdir)

def CleanFolder(threadid):
  srcdir = TEMPDIR.format(threadid)
  make_dir(srcdir)

def isAndroid(threadid):
  srcdir = TEMPDIR.format(threadid)
  var = check_output(["find", srcdir, "-name", "AndroidManifest.xml"])
  if not var:
    return False
  else:
    return True

def IsCompressed(project):
  for item in os.listdir(project["path"]):
    #print item
    if item.endswith(".zip"):
      return True, os.path.join(project["path"], item)
  return False, ""

def Uncompress(comp_path, threadid):
  path = "Uncompress/uncompressed_{0}".format(threadid)
  if not os.path.exists(path):
    make_dir("Uncompress/uncompressed_{0}".format(threadid))
  else:
    check_output(["rm", "-rf", path])
    make_dir("Uncompress/uncompressed_{0}".format(threadid))
  unzip(comp_path, path)
  check_output(["chmod", "777", "-R", path])
  return path

def CompileAndSave(threadid, projects, methods, root, outdir):
  save = shelve.open(PARTMAP.format(threadid))
  #projects = RemoveTouched(save, projects)
  i = 0
  #count = len(projects)
  project = projects.get()
  project["timing"] = list()
  project["timing"].append(("start", time.time()))
  #print 'Starting project',project["path"]

  while project != "DONE":
  #for project in projects:
    #print project["file"], i, len(projects), threadid
    failtocopy = True
    is_compressed, comp_path = True,project["path"]
    
    temppath = Uncompress(comp_path, threadid)
    project["timing"].append(("end_uncompress", time.time()))
    project_path = temppath
    #print project_path
    #print project_path
    if not os.path.exists(project_path):
      continue
    CleanFolder(threadid)
    project["timing"].append(("end_clean_folder", time.time()))
    try:
      CopyTarget(project_path, threadid)
      project["timing"].append(("end_copy_to_tbuild", time.time()))
      # CHeck if is Android or not
      project["type"] = "android" if isAndroid(threadid) else "normal"
      failtocopy = False
      
    except Exception, e:
      print "Found Exception", e
      continue
    #if failtocopy:
    #  print os.listdir(temppath)
    succ, output, buildfs, command = TryCompile(0, project, methods, threadid, []) if not failtocopy else (False, [{"error_type": "Copy failure"}], [], "")
    project["timing"].append(("end_all_compile", time.time()))
    #print succ, project["file"]
    #print "command: ", command
    CopyBuildFiles(project, threadid, outdir, buildfs, succ)
    project["timing"].append(("end_copy_class_files", time.time()))
    SaveOutput(save, project, succ, output, outdir, command)
    project["timing"].append(("end_save_json", time.time()))
    i+=1
    if i % 10 == 0:
      print "Thread " + str(threadid) + ": " + str(i)
    project = projects.get()
  print "Done with Thread ", threadid
#  CleanFolder(threadid)

def ConsolidateOutput():
  reduced = {}
  final = {}
  for i in range(THREADCOUNT):
    reduced.update(dict(shelve.open(PARTMAP.format(i))))
  for key in reduced:
    data = reduced[key]
    if "depends" in data:
      for i in range(len(data["depends"])):
        a,b,c,d,e,f = data["depends"][i]        
        data["depends"][i] = (a,b,c,d,e.encode("ascii", "xmlcharrefreplace"),f)
    if "output" in data and len(data["output"]) > 0 and type(data["output"][0]) == type({}):
      for i in range(len(data["output"])):
        if data["output"][i]["error_type"] == "python exception":
          print data["output"][i]["error"]
          data["output"][i]["error"] = repr(data["output"][i]["error"])
        if "error" in data["output"][i]:
          try:
            data["output"][i]["error"] = data["output"][i]["error"].encode("ascii", "xmlcharrefreplace")
          except Exception, e:
            continue
     
    final[key] = data
  print "Writing json"
  return final

def main(root, projects, outdir, methods,):
  processes = []
  p = Queue()
  for proj in RemoveTouched(projects):
    p.put(proj)
  for i in range(THREADCOUNT):
    p.put("DONE")
  for i in range(THREADCOUNT):
    processes.append(Process(target = CompileAndSave, args = (i, p, methods, root, outdir)))
    processes[-1].daemon = True
    processes[-1].start()

  for i in range(THREADCOUNT):
    processes[i].join()
  print "Done with all threads."
  return ConsolidateOutput()

def generate_infile(root):
  return [{"file": os.path.join(fold, file)[:-4], "path": os.path.join(root, fold, file)} for fold in os.listdir(root) for file in os.listdir(os.path.join(root, fold)) if file.endswith(".zip")]

def getProjects(root, infile):
  if infile == "AUTOGEN":
    return generate_infile(root)
  else:
    return [{"file": line[:-4], "path": os.path.join(root, line)} for line in open(infile).read().split("\n") if line]

if __name__ == "__main__":
  global THREADCOUNT, JAR_REPO
  parser = argparse.ArgumentParser()
  parser.add_argument('-r', '--root', type=str, help ='The directory under which all the java projects to be compiled exist.')
  parser.add_argument('-f', '--file', type=str, default= "AUTOGEN", help ='The file with project paths to be build. Paths in file are considered relative to the root directory.')
  parser.add_argument('-d', '--outfolder', default = "builds", type=str, help ='The directory under which all the output build directories will be put.')
  parser.add_argument('-o', '--output', default = "project_success.json", type=str, help ='An output file that will contain all the output information consolidated.')
  parser.add_argument('-j', '--jars', default="jars", type=str, help ='The root of the java repository')
  parser.add_argument('-ftj', '--fqn_to_jar', default="fqn-to-jars.json", type=str, help ='The file that represents the mapping of fqn to jar in repository.')
  parser.add_argument('-t', '--threads', default=10, type=int, help ='The number of base threads to be run.')
  args = parser.parse_args()
  root, infile, outdir, outfile, THREADCOUNT = args.root, args.file, args.outfolder, args.output, args.threads
  dependency_matcher.load_fqns(args.jars, args.fqn_to_jar)
  JAR_REPO = args.jars
  if not os.path.exists("TBUILD"):
    os.makedirs("TBUILD")
  projects = getProjects(root, infile)
  make_dir(outdir, keep_old = True)
  methods = [OwnBuild, TryNewBuild, EncodeFix, FixMissingDeps]
  open(outfile, "w").write(json.dumps(
      main(root, projects, outdir, methods),
      sort_keys=True,
      indent=4,
      separators=(',', ': ')))



