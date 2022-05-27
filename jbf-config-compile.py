#!/usr/bin/env python
import configparser
import os
from subprocess import run, CalledProcessError, PIPE

import simplejson as json

import sourcererjbf.compile_checker as cc
import sourcererjbf.dependency_matcher as dm
import sourcererjbf.fqn_to_jar_map_generator as ftjmg


def save_to_json(output_file, projects_build_json):
    json_string = json.dumps(projects_build_json, sort_keys=True, indent=4, separators=(',', ': '))
    with open(output_file, "w") as file:
        file.write(json_string)
    print("Saving Done")


def clean_up_all():
    print("Cleaning Up All")
    clean_up_directories()
    clean_up_files()
    print("Cleaning Done")


def clean_up_directories():
    try:
        output = run(["rm", "-rf", "TBUILD", "Uncompress", "builds"],
                     encoding='utf8',
                     check=True, stdout=PIPE).stdout.strip()
    except CalledProcessError:
        print("Cleaning Directories Interrupted")


def clean_up_files():
    try:
        output = run(["rm", "-rf", "badjars.txt", "badjars_*", "save_*", "fqn_to_jar.log"], encoding='utf8',
                     check=True, stdout=PIPE).stdout.strip()
    except CalledProcessError:
        print("Cleaning Files Interrupted")


if __name__ == "__main__":

    config = configparser.ConfigParser()
    config.read('jbf.config')
    root = config.get('DEFAULT', 'root')
    rebuild_from_scratch = config.getboolean('DEFAULT', 'rebuild_from_scratch')
    file = config.get('DEFAULT', 'file')
    outfolder = config.get('DEFAULT', 'outfolder')
    output = config.get('DEFAULT', 'output')
    jars = config.get('DEFAULT', 'jars')
    fqn_to_jar = config.get('DEFAULT', 'fqn_to_jar')
    threads = config.getint('DEFAULT', 'threads')
    try_project_build = config.getboolean('DEFAULT', 'try_project_build')
    verbose = config.getboolean('DEFAULT', 'verbose')
    only_project_build = config.getboolean('DEFAULT', 'only_project_build')

    root, infile, outdir, outfile, cc.THREADCOUNT = root, file, outfolder, output, threads
    cc.JAR_REPO = jars
    cc.VERBOSE = verbose

    if rebuild_from_scratch and not only_project_build:
        ftjmg.ROOT = jars
        dm.load_fqns(jars, fqn_to_jar, threads)
    if not os.path.exists("TBUILD"):
        os.makedirs("TBUILD")
    if rebuild_from_scratch:
        projects = cc.getProjects(root, infile)
    else:
        projects = list()
        for item in json.load(open(outfile)).values():
            item["file"] = str(item["file"])
            projects.append(item)
    cc.make_dir(outdir, keep_old=True)

    if rebuild_from_scratch:
        if only_project_build:
            methods = [cc.OwnBuild]
        else:
            methods = [cc.OwnBuild, cc.TryNewBuild, cc.EncodeFix, cc.FixMissingDeps] if try_project_build else [
                cc.TryNewBuild, cc.EncodeFix, cc.FixMissingDepsWithOwnJars]

        project_json = cc.main(root, projects, outdir, methods)
        save_to_json(outfile, project_json)
        clean_up_all()
    else:
        methods = [cc.build_as_is]
        success_map = cc.main(root, projects, outdir, methods)
        print(len([id for id in success_map if success_map[id]["success"]]), "built successfully from",
              len(success_map), "projects")
        clean_up_all()
