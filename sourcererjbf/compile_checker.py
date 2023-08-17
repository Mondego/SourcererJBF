#!/usr/bin/env python

# Takes a folder as input, looks at all subfolders, finds jar files
# and figures out FQNs that exist in them
#
# Usage: ./compile_checker.py -r <Root Directory>
import configparser
import os, zipfile, shelve, shutil, sys, re, argparse, time, datetime
from pathlib import Path

import simplejson as json
from multiprocessing import Process, Lock, Queue
from threading import Thread
from subprocess import check_output, call, CalledProcessError, STDOUT, Popen, PIPE, TimeoutExpired

from sourcererjbf import output_analyzer, encode_fixer, dependency_matcher

from .constants import PARTMAP, TEMPDIR, TIMEOUT_SECONDS, bcolors

THREADCOUNT = 32
PATH_logs = "logs"
JAR_REPO = ""
VERBOSE = False
ignore_projects = set()


# Causes infinite loop
def FindAll(output, error_type):
    return [item for item in output if item["error_type"] == error_type]


def TryNewBuild(project, threadid, output):
    project["create_build"] = True
    try:
        srcdir = TEMPDIR.format(threadid)
        project["has_own_build"] = check_output(["find", srcdir, "-name", "build.xml"], encoding='utf8') != ""
    except CalledProcessError:
        project["has_own_build"] = False
    return True, output, project


def OwnBuild(project, threadid, output):
    # project["create_build"] = False
    try:
        srcdir = TEMPDIR.format(threadid)
        # precedence order of Gradle ⇒ Maven ⇒ Ant.
        # try gradle
        gradle_find = check_output(["find", srcdir, "-name", "build.gradle"], encoding='utf8')
        if gradle_find != "":
            project["use_command"] = ["gradle", "-b", gradle_find.split("\n")[0].strip(), "compileJava"]
            project["has_own_build"] = True
            project["create_build"] = False
            # print "Gradle: ", project["path"]
            return True, output, project

        # try maven
        mvn_find = check_output(["find", srcdir, "-name", "pom.xml"], encoding='utf8')
        if mvn_find != "":
            project["use_command"] = ["mvn", "-f", mvn_find.split("\n")[0].strip(), "compile"]
            project["has_own_build"] = True
            project["create_build"] = False
            # print "MVN: ", project["path"]
            return True, output, project

        # try ant
        ant_find = check_output(["find", srcdir, "-name", "build.xml"], encoding='utf8')
        if ant_find != "":
            project["use_command"] = ["ant", "-f", ant_find.split("\n")[0].strip()]
            project["has_own_build"] = True
            project["create_build"] = False
            # print "ANT: ", project["path"]
            return True, output, project

    except CalledProcessError:
        project["has_own_build"] = False
    project["has_own_build"] = False
    project["create_build"] = False
    return False, output, project


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


def Compile(threadid, generated_build, project):
    try:
        srcdir = TEMPDIR.format(threadid)
        # findjava = check_output(["find", srcdir, "-name", "*.java"], timeout = TIMEOUT_SECONDS)
        # if findjava == "":
        #  return False, [{"error_type": "No Java Files"}], "", ""
        if not generated_build:
            try:
                command = " ".join(project["use_command"])
                project["timing"].append(("start_build", time.time()))
                output = check_output(project["use_command"], encoding='utf8', stderr=STDOUT, timeout=TIMEOUT_SECONDS)
                project["timing"].append(("end_build", time.time()))
                return True, output, command, ""
            except CalledProcessError as e:
                return False, Analyze(e.output), command, e.output
        else:
            try:
                command = "ant -f build.xml compile"
                project["timing"].append(("start_build", time.time()))
                output = check_output(["ant", "-f", os.path.join(srcdir, "build.xml"), "compile"], encoding='utf8',
                                      stderr=STDOUT,
                                      timeout=TIMEOUT_SECONDS)
                project["timing"].append(("end_build", time.time()))
                return True, output, command, ""
            except CalledProcessError as e:
                return False, Analyze(e.output), command, e.output
        return False, [{"error_type": "No Build File"}], "", ""
    except TimeoutExpired:
        return False, [{"error_type": "Timeout expired"}], "", ""


def copyrecursively(source_folder, destination_folder):
    # print "Hi Im here"
    for root, dirs, files in os.walk(source_folder):
        for item in files:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(destination_folder, src_path.replace(source_folder + "/", ""))
            if os.path.exists(dst_path):
                if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                    shutil.copy2(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
        for item in dirs:
            src_path = os.path.join(root, item)
            dst_path = os.path.join(destination_folder, src_path.replace(source_folder + "/", ""))
            if not os.path.exists(dst_path):
                os.mkdir(dst_path)
    # print "Hi Im leaving"


def unzip(zipFilePath, destDir):
    try:
        zip_ref = zipfile.ZipFile(zipFilePath, 'r')
        zip_ref.extractall(destDir)
        zip_ref.close()
        # print "Success ", zipFilePath, destDir
    except Exception as e:
        pass


def RemoveTouched(projects, recordq):
    if os.path.exists("TBUILD"):
        if os.listdir("TBUILD") == []:
            return projects
        new_projects = list()
        for f in os.listdir("TBUILD"):
            if f.endswith(".shelve"):
                save = shelve.open("TBUILD/" + f)
                # new_projects = list()
                for project in projects:
                    if project["file"] not in save and project["file"] not in ignore_projects:
                        new_projects.append(project)
                    else:
                        recordq.put(save[project["file"]]["success"] if project["file"] in save else False)
                # projects = [project for project in projects if project["file"] not in save and project["file"] not in ignore_projects]
                save.close()
        return new_projects
    else:
        return projects


def MakeBuild(project, threadid):
    classpath = ""
    mavenline = ""
    if "depends" in project:
        depends = set([(a, b, c, d, e, f) for a, b, c, d, e, f in project["depends"]])
        mavendepends = set([d for d in depends if d[3]])
        mavenline = "\n  ".join([d[4] for d in mavendepends])
        jardepends = depends - mavendepends

        # ecoding won't work as d coming as a string not byte
        # jarline = "\n        ".join(["<pathelement path=\"{0}\" />".format(os.path.join("../.." ,JAR_REPO, d[4].encode("utf-8", "xmlcharrefreplace")) if not d[5] else d[4].encode("utf-8", "xmlcharrefreplace")) for d in jardepends])
        jarline = "\n        ".join(
            ["<pathelement path=\"{0}\" />".format(os.path.join("/", JAR_REPO, d[4]) if not d[5] else d[4]) for d in
             jardepends])

        if jarline or mavenline:
            if mavenline:
                classpath += "\n      <classpath refid=\"default.classpath\" />"
            if jarline:
                classpath = "\n      <classpath>\n        " + jarline + "\n      </classpath>"

    desc = project["description"] if "description" in project else ""
    ivyfile = open("xml-templates/ivy-template.xml", "r").read().format(
        project["name"] if "name" in project else "compile_checker_build", mavenline)
    buildfile = open("xml-templates/build-template.xml", "r").read().format(
        project["name"] if "name" in project else "compile_checker_build", desc, classpath, "${build}", "${src}",
        project["encoding"] if "encoding" in project else "utf8", os.path.join("../..", JAR_REPO, "ext"),
        "yes" if VERBOSE else "no")
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
                succ, output, command, full_output = Compile(threadid, project["create_build"], project)
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
    except Exception as e:
        return False, [{"error_type": "python exception", "error": str(e)}], [], ""


def CopyTarget(projectpath, threadid):
    copyrecursively(projectpath, TEMPDIR.format(threadid))
    check_output(["chmod", "-R", "+w", TEMPDIR.format(threadid)], encoding='utf8')


def CopyDependentJarFilesToOutputFolder(project, threadid, outdir, succ):
    dependents_jars_path = os.path.join(outdir, project["file"], "depends")
    if "depends" in project:
        list_of_jars = project["depends"]
        for jar in list_of_jars:
            jar_path = jar[4]
            if os.path.exists(os.path.join("/", jar_path)):
                check_output(["cp", os.path.join("/", jar_path), dependents_jars_path], encoding='utf8')
            else:
                project_unzip_path = os.path.join(TEMPDIR.format(threadid))
                merged_path = os.path.join(project_unzip_path, jar_path)
                if os.path.exists(merged_path):
                    check_output(["cp", merged_path, dependents_jars_path], encoding='utf8')


def UpdateBuildFiles(outdir, project, output_project_path):
    dependents_jars_path = os.path.join(outdir, project["file"], "depends")
    check_output(["mkdir", "-p", dependents_jars_path], encoding='utf8')
    classpath = ""
    mavenline = ""
    if "depends" in project:
        depends = set([(a, b, c, d, e, f) for a, b, c, d, e, f in project["depends"]])
        jarline = "\n        ".join(
            ["<pathelement path=\"{0}\" />".format("depends/" + Path(d[4]).name) for d in
             depends])

        if jarline:
            classpath = "\n      <classpath>\n        " + jarline + "\n      </classpath>"

    desc = project["description"] if "description" in project else ""
    ivyfile = open("xml-templates/ivy-template.xml", "r").read().format(
        project["name"] if "name" in project else "compile_checker_build", mavenline)
    buildfile = open("xml-templates/build-template.xml", "r").read().format(
        project["name"] if "name" in project else "compile_checker_build", desc, classpath, "${build}", "${src}",
        project["encoding"] if "encoding" in project else "utf8", os.path.join("../..", JAR_REPO, "ext"),
        "yes" if VERBOSE else "no")
    # srcdir = TEMPDIR.format(threadid)
    open(os.path.join(output_project_path, "ivy.xml"), "w").write(ivyfile)
    open(os.path.join(output_project_path, "build.xml"), "w").write(buildfile)
    return ivyfile, buildfile


def CopyBuildFiles(project, threadid, outdir, buildfiles, succ):
    project_zip_path = project['path']
    output_project_path = os.path.join(outdir, project["file"])
    config = configparser.ConfigParser()
    config.read('jbf.config')
    copy_source = config.getboolean('DEFAULT', 'copy_source')
    copy_jars = config.getboolean('DEFAULT', 'copy_jars')
    if succ:
        build_files_path = os.path.join(outdir, project["file"], "build")
        check_output(["mkdir", "-p", build_files_path], encoding='utf8')
        copyrecursively(os.path.join(TEMPDIR.format(threadid), "build"), build_files_path)
        UpdateBuildFiles(outdir, project, output_project_path)
        if copy_source:
            check_output(["cp", project_zip_path, output_project_path], encoding='utf8')
        if copy_jars:
            CopyDependentJarFilesToOutputFolder(project, threadid, outdir, succ)


def SaveOutput(save, project, succ, output, outdir, command):
    project.update({"success": succ, "output": output})
    project_path = os.path.join(outdir, project["file"])
    if not os.path.exists(project_path):
        check_output(["mkdir", "-p", project_path], encoding='utf8')
    json.dump(project, open(os.path.join(project_path, "build-result.json"), "w"), sort_keys=True, indent=4,
              separators=(",", ": "))
    open(os.path.join(project_path, "build.command"), "w").write(command)
    # print type(project["file"]), type(project)
    save[project["file"]] = project
    save.sync()


def make_dir(outdir, keep_old=False):
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
    var = check_output(["find", srcdir, "-name", "AndroidManifest.xml"], encoding='utf8')
    if not var:
        return False
    else:
        return True


def IsCompressed(project):
    for item in os.listdir(project["path"]):
        # print item
        if item.endswith(".zip"):
            return True, os.path.join(project["path"], item)
    return False, ""


def Uncompress(comp_path, threadid):
    path = "Uncompress/uncompressed_{0}".format(threadid)
    if not os.path.exists(path):
        make_dir("Uncompress/uncompressed_{0}".format(threadid))
    else:
        check_output(["rm", "-rf", path], encoding='utf8')
        make_dir("Uncompress/uncompressed_{0}".format(threadid))
    unzip(comp_path, path)
    check_output(["chmod", "777", path], encoding='utf8')
    return path


def make_tarball(project, outdir):
    ## archive the folder
    # tar -czvf file.tar.gz directory
    output_project_dir = os.path.join(outdir, project["file"])
    output_tar_file_path = "file.tar.gz"
    check_output(["tar", "-czvf", output_tar_file_path, output_project_dir], encoding='utf8')
    ## delete the directory


def CompileAndSave(threadid, projects, methods, root, outdir, reportq):
    save = shelve.open(PARTMAP.format(threadid))
    # projects = RemoveTouched(save, projects)
    i = 0
    # count = len(projects)
    project = projects.get()
    # project["timing"] = list()
    # project["timing"].append(("start", time.time()))
    # print 'Starting project',project["path"]

    while project != "DONE":
        project["timing"] = list()
        project["timing"].append(("start", time.time()))
        # for project in projects:
        # print project["file"], i, len(projects), threadid
        failtocopy = True
        is_compressed, comp_path = True, project["path"]

        temppath = Uncompress(comp_path, threadid)
        project["timing"].append(("end_uncompress", time.time()))
        project_path = temppath
        # print project_path
        # print project_path
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

        except Exception as e:
            # print "Found Exception", e
            continue
        srcdir = TEMPDIR.format(threadid)
        findjava = check_output(["find", srcdir, "-name", "*.java"], timeout=TIMEOUT_SECONDS, encoding='utf8')
        succ, output, buildfs, command = (TryCompile(0, project, methods, threadid, []) if not failtocopy else (
            False, [{"error_type": "Copy failure"}], [], "") if findjava != "" else (
            False, [{"error_type": "No Java Files"}], "", ""))
        project["timing"].append(("end_all_compile", time.time()))
        # print succ, project["file"]
        # print "command: ", command

        CopyBuildFiles(project, threadid, outdir, buildfs, succ)
        project["timing"].append(("end_copy_class_files", time.time()))
        SaveOutput(save, project, succ, output, outdir, command)
        project["timing"].append(("end_save_json", time.time()))
        # make_tarball(project, outdir)
        reportq.put(succ)
        # i+=1
        # if i % 10 == 0:
        #  print "Thread " + str(threadid) + ": " + str(i)
        project = projects.get()
    # print "Done with Thread ", threadid


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
                a, b, c, d, e, f = data["depends"][i]
                try:
                    data["depends"][i] = (a, b, c, d, e.encode("ascii", "xmlcharrefreplace"), f)
                except UnicodeDecodeError:
                    data["depends"][i] = (a, b, c, d, "UNICDOE ERROR JAR", f)
        if "output" in data and len(data["output"]) > 0 and type(data["output"][0]) == type({}):
            for i in range(len(data["output"])):
                if data["output"][i]["error_type"] == "python exception":
                    # print data["output"][i]["error"]
                    data["output"][i]["error"] = repr(data["output"][i]["error"])
                if "error" in data["output"][i]:
                    try:
                        data["output"][i]["error"] = data["output"][i]["error"].encode("ascii", "xmlcharrefreplace")
                    except Exception as e:
                        continue

        final[key] = data
    print("Writing json")
    return final


def progress(count, succ, fail, total, suffix=''):
    bar_len = 60
    succ_filled_len = int(round(bar_len * succ / float(total)))
    fail_filled_len = int(round(bar_len * fail / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = (bcolors.OKGREEN + ('|' * succ_filled_len) + bcolors.ENDC
           + bcolors.WARNING + ('|' * fail_filled_len) + bcolors.ENDC
           + ' ' * (bar_len - succ_filled_len - fail_filled_len))

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()  # As suggested by Rom Ruben


def progressbar(recordq, total):
    print("TOTAL NUMBER OF PROJECTS TO COMPILE:", total)
    count = 0
    succ = 0
    fail = 0
    start_t = time.time()
    progress(0, 0, 0, total, suffix="Initalizing Threads")
    item = recordq.get()
    while item != "DONE":
        count += 1
        if item:
            succ += 1
        else:
            fail += 1
        time_left = (total - count) * (time.time() - start_t) / count
        hrs = time_left / 3600
        strtime = "%d:%d:%d" % (time_left / 3600, (time_left % 3600) / 60, ((time_left % 3600) % 60))

        progress(count, succ, fail, total, suffix="%d(%.1fper)PASS, %d Total, ETA: %s" % (
            succ, float(succ) * 100 / float(succ + fail), succ + fail, strtime))
        item = recordq.get()
    print("\n")


def main(root, projects, outdir, methods):
    processes = []
    p = Queue()
    recordq = Queue()
    for proj in RemoveTouched(projects, recordq):
        p.put(proj)
    for i in range(THREADCOUNT):
        p.put("DONE")
    recorder = Thread(target=progressbar, args=(recordq, len(projects)))
    recorder.daemon = True
    recorder.start()
    for i in range(THREADCOUNT):
        processes.append(Process(target=CompileAndSave, args=(i, p, methods, root, outdir, recordq)))
        processes[-1].daemon = True
        processes[-1].start()
        time.sleep(0.5)

    for i in range(THREADCOUNT):
        processes[i].join()
    recordq.put("DONE")
    time.sleep(1)
    print("Done with all threads.")
    return ConsolidateOutput()


def generate_infile(root):
    return [{"file": os.path.join(fold, file)[:-4], "path": os.path.join(root, fold, file)} for fold in os.listdir(root)
            for file in os.listdir(os.path.join(root, fold)) if file.endswith(".zip")]


def getProjects(root, infile):
    if infile == "AUTOGEN":
        return generate_infile(root)
    else:
        return [{"file": line[:-4], "path": os.path.join(root, line)} for line in open(infile).read().split("\n") if
                line]


if __name__ == "__main__":
    # global THREADCOUNT, JAR_REPO
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--root', type=str,
                        help='The directory under which all the java projects to be compiled exist.')
    parser.add_argument('-f', '--file', type=str, default="AUTOGEN",
                        help='The file with project paths to be build. Paths in file are considered relative to the root directory.')
    parser.add_argument('-d', '--outfolder', default="builds", type=str,
                        help='The directory under which all the output build directories will be put.')
    parser.add_argument('-o', '--output', default="project_success.json", type=str,
                        help='An output file that will contain all the output information consolidated.')
    parser.add_argument('-j', '--jars', default="jars", type=str, help='The root of the java repository')
    parser.add_argument('-ftj', '--fqn_to_jar', default="fqn-to-jars.json", type=str,
                        help='The file that represents the mapping of fqn to jar in repository.')
    parser.add_argument('-t', '--threads', default=10, type=int, help='The number of base threads to be run.')
    args = parser.parse_args()
    root, infile, outdir, outfile, THREADCOUNT = args.root, args.file, args.outfolder, args.output, args.threads
    dependency_matcher.load_fqns(args.jars, args.fqn_to_jar, args.threads)
    JAR_REPO = args.jars
    if not os.path.exists("TBUILD"):
        os.makedirs("TBUILD")
    projects = getProjects(root, infile)
    make_dir(outdir, keep_old=True)
    methods = [OwnBuild, TryNewBuild, EncodeFix, FixMissingDeps]
    open(outfile, "w").write(json.dumps(
        main(root, projects, outdir, methods),
        sort_keys=True,
        indent=4,
        separators=(',', ': ')))
