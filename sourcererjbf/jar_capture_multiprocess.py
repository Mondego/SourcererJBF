#!/usr/bin/env python
import os
import sys
import shelve
from shutil import copyfile
import hashlib
import zipfile
from subprocess import check_output, run, call, CalledProcessError, STDOUT, PIPE
from multiprocessing import Process, Queue

NUMBER_OF_THREADS = 20


def unzip(zipFilePath, destDir):
    try:
        zip_ref = zipfile.ZipFile(zipFilePath, 'r')
        zip_ref.extractall(destDir)
        zip_ref.close()
        check_output(["chmod", "777", "-R", destDir], encoding='utf8')
        print('SUCCESS -', zipFilePath)
        return True
    except Exception as e:
        print('FAILURE -', zipFilePath, e)


def search(folder):
    all_jars = check_output(["find", folder, "-name", "*.jar"], encoding='utf8')
    return all_jars.split("\n") if all_jars else []


def final_dest(jar):
    try:
        filename = jar.split("/")[-1]
        if not filename.endswith(".jar"):
            return "", ""
        muse_jars = "jars"
        splits = filename.split(".")
        filename = ".".join(splits[:-1])
        extension = splits[-1]

        folder = os.path.join(filename[0], filename)
        fullfolder = os.path.join(muse_jars, folder)
        if not os.path.exists(fullfolder):
            os.makedirs(fullfolder)
        existing_file_count = len(os.listdir(fullfolder))

        copy_path = os.path.join(folder, filename + "_" + str(existing_file_count) + "." + extension)
        fullpath = os.path.join(muse_jars, copy_path)
        return fullpath, copy_path
    except Exception:
        print(jar)
        return "", ""


def record_it(record, jar, dest, sha_hash, project, tempfolder):
    rel_path = jar[len(tempfolder):]
    true_path = os.path.join(project, rel_path)
    record[dest] = (true_path, sha_hash)


def save_and_record(record, jars, project, tempfolder):
    for jar, sha_hash in jars:
        fulldest, partdest = final_dest(jar)
        if not fulldest:
            continue
        copyfile(jar, fulldest)
        record_it(record, jar, partdest, sha_hash, project, tempfolder)


def dedupe(jars, sobj, project, tempfolder):
    deduped_jars = []
    for jar in jars:
        if jar and os.path.isfile(jar):
            h = hashlib.sha512(open(jar, 'rb').read()).hexdigest()
            true_path = os.path.join(project, jar[len(tempfolder):])
            if h not in sobj:
                sobj[h] = [true_path]
                deduped_jars.append((jar, h))
            else:
                if true_path not in sobj[h]:
                    sobj[h] = sobj[h] + [true_path]
    return deduped_jars


def clean(folder):
    call(["rm", "-r", "-f", folder], encoding='utf8')
    os.makedirs(folder)


def copy_jars(projects, unzip_dir_path, sobj, record, tc):
    i = 0
    temp_folder = unzip_dir_path + "/" + "dir_" + str(tc)
    clean(temp_folder)
    check_output(["mkdir", temp_folder], encoding='utf8')
    for project in projects:
        if not os.path.isfile(project):
            continue
        res = unzip(project, temp_folder)
        if True:
            save_and_record(record, dedupe(search(temp_folder), sobj, project, temp_folder), project, temp_folder)
            clean(temp_folder)
        i += 1
        if i % 100 == 0:
            print(i, "/", len(projects))


def getProjects(infile):
    res = []
    with open(infile, 'r') as f:
        for line in f:
            res.append(line[:-1])
    return res


def create_subprocess_of_jar_capturing(projects, unzip_dir_path, sobj, record, tc):
    global NUMBER_OF_THREADS
    NUMBER_OF_THREADS = tc
    threads = []
    for i in range(NUMBER_OF_THREADS):
        threads.append(Process(target=copy_jars,
                               args=(projects[i::NUMBER_OF_THREADS], unzip_dir_path, sobj, record, i)))
        threads[-1].daemon = True
        threads[-1].start()

    for i in range(NUMBER_OF_THREADS):
        threads[i].join()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("The right usage is ./jar_capture.py <File with paths>")
        sys.exit(0)
    infile = sys.argv[1]
    unzip_dir_path = sys.argv[2]
    threads = int(sys.argv[3])
    projects = getProjects(infile)
    sobj = dict()  # shelve.open("jar_hashes.shelve")
    record = dict()  # shelve.open("jar_db_records.shelve")
    # copy_jars(projects, unzip_dir_path, sobj, record, threads)
    create_subprocess_of_jar_capturing(projects, unzip_dir_path, sobj, record, threads)
