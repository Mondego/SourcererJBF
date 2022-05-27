#!/usr/bin/env python
import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--root', type=str,
                        help='The directory under which all the java projects to be compiled exist.')
    parser.add_argument('-b', '--rebuild_from_scratch', action='store_true',
                        help='Rebuild the projects from scratch. Dependency rematching implies that all projects '
                             'might not recompile successfully.')
    parser.add_argument('-f', '--file', type=str, default="AUTOGEN",
                        help='The file with project paths to be build. Paths in file are considered relative to the '
                             'root directory.')
    parser.add_argument('-d', '--outfolder', default="builds", type=str,
                        help='The directory under which all the output build directories will be put.')
    parser.add_argument('-o', '--output', default="project_details.json", type=str,
                        help='An output file that will contain all the output information consolidated.')
    parser.add_argument('-j', '--jars', default="jars", type=str, help='The root of the java repository')
    parser.add_argument('-ftj', '--fqn_to_jar', default="fqn-to-jars.shelve", type=str,
                        help='The file that represents the mapping of fqn to jar in repository.')
    parser.add_argument('-t', '--threads', default=10, type=int, help='The number of base threads to be run.')
    parser.add_argument('-tpb', '--try_project_build', action='store_true',
                        help='Use project build files first if it exists.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Forces javac output to be verbose. Default False')
    parser.add_argument('-opb', '--only_project_build', action='store_true', help='Only use project build files.')
    args = parser.parse_args()
    root, infile, outdir, outfile, cc.THREADCOUNT = args.root, args.file, args.outfolder, args.output, args.threads
    cc.JAR_REPO = args.jars
    cc.VERBOSE = args.verbose

    if args.rebuild_from_scratch and not args.only_project_build:
        ftjmg.ROOT = args.jars
        dm.load_fqns(args.jars, args.fqn_to_jar, args.threads)
    if not os.path.exists("TBUILD"):
        os.makedirs("TBUILD")
    if args.rebuild_from_scratch:
        projects = cc.getProjects(root, infile)
    else:
        projects = list()
        for item in json.load(open(outfile)).values():
            item["file"] = str(item["file"])
            projects.append(item)
    cc.make_dir(outdir, keep_old=True)

    if args.rebuild_from_scratch:
        if args.only_project_build:
            methods = [cc.OwnBuild]
        else:
            methods = [cc.OwnBuild, cc.TryNewBuild, cc.EncodeFix, cc.FixMissingDeps] if args.try_project_build else [
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
