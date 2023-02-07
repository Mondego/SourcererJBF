import json
import os
import shelve
import zipfile
from multiprocessing import Process
from os.path import exists
from subprocess import check_output, CalledProcessError, call

projects_abs_path = ""
NUMBER_OF_THREADS = 60


def create_subprocess(repo_location, unzip_path, base_path, path_copied_jars, tc):
    global NUMBER_OF_THREADS
    NUMBER_OF_THREADS = tc
    threads = []
    for i in range(NUMBER_OF_THREADS):
        threads.append(Process(target=find_dependency_collection_in_repo,
                               args=(repo_location[i::NUMBER_OF_THREADS], unzip_path, base_path, path_copied_jars, i)))
        threads[-1].daemon = True
        threads[-1].start()

    for i in range(NUMBER_OF_THREADS):
        threads[i].join()
    return merge_all_and_save()


def merge_all_and_save():
    all_repo_metrics = {}
    for i in range(NUMBER_OF_THREADS):
        print(i)
        part = dict(shelve.open("save_" + str(i)))
        for item in part:
            all_repo_metrics[item] = part[item]
    print("Merging_Done")
    save_to_shelve(all_repo_metrics)
    save_to_json(all_repo_metrics)


def save_to_shelve(project_jar_map):
    sh = shelve.open("project-to-jars-map.shelve")
    for p in project_jar_map:
        try:
            sh[str(p)] = project_jar_map[p]
            sh.sync()
        except Exception as e:
            print("Exception (probably decoding) when writing out project-jar-map: ", p, e)
            continue
    sh.close()


def save_to_json(all_repo_metrics):
    json_string = json.dumps(all_repo_metrics)
    with open("project-to-jars-map.json", "w") as text_file:
        text_file.write(json_string)
    print("Saving Done")


def unzip_repository(zip_path, unzip_path):
    try:
        with zipfile.ZipFile(zip_path) as zip_ref:
            zip_ref.extractall(unzip_path)
            zip_ref.close()
            check_output(["chmod", "777", unzip_path], encoding='utf8')
            print('SUCCESS Unzipping Done -', zip_path)
            return True
    except Exception as e:
        print('FAILURE -', zip_path, e)
        return False


def get_zip_locations_from_file(file_path):
    with open(file_path) as f:
        paths = f.read().splitlines()
        return paths


def get_zip_locations_path(root):
    return [os.path.join(root, fold, file) for fold in os.listdir(root)
            for file in os.listdir(os.path.join(root, fold)) if file.endswith(".zip")]


def clean_unzip_dir(folder):
    call(["rm", "-r", "-f", folder], encoding='utf8')
    os.makedirs(folder)
    print("Cleaning up..." + folder)


def search_jars_in_copied_folder(folder):
    all_jars = check_output(["find", folder, "-name", "*.jar"], encoding='utf8')
    jar_names = []
    if all_jars:
        jar_list = all_jars.split("\n")
        for j in jar_list:
            if j:
                filename = os.path.basename(j)
                jar_names.append(filename)
    return jar_names


def get_local_jars_unzip_folder(folder):
    all_jars = check_output(["find", folder, "-name", "*.jar"], encoding='utf8')
    jar_names = []
    if all_jars:
        jar_list = all_jars.split("\n")
        for j in jar_list:
            if j:
                filename = os.path.basename(j)
                jar_names.append(filename)
    return jar_names


def find_all_pom_files(folder):
    all_pom_xml = check_output(["find", folder, "-name", "pom.xml"], encoding='utf8')
    all_pom_xml = all_pom_xml.split("\n") if all_pom_xml else []
    all_pom_xml = [i for i in all_pom_xml if i]
    return all_pom_xml if all_pom_xml else []


def get_dependency_list(key, unzip_dir_path, copied_jar_paths):
    all_poms = find_all_pom_files(unzip_dir_path)
    for pom in all_poms:
        if exists(pom):
            try:
                output = check_output(
                    ["mvn", "dependency:copy-dependencies", "-DoutputDirectory=" + copied_jar_paths, "-f", pom],
                    encoding='utf8')
            except Exception as e:
                print("Failed while executing: " + pom)
    return search_jars_in_copied_folder(copied_jar_paths)


def get_dependency_jars_names(key, zip_path, unzip_path, copied_jar_path):
    repo = {}
    repo['prev_key'] = key
    repo["path"] = zip_path
    repo["dependencies"] = get_dependency_list(key, unzip_path, copied_jar_path)
    # repo["local_dependencies"] = get_local_jars_unzip_folder(unzip_path)
    return repo


def find_dependency_collection_in_repo(zip_paths, unzip_path, base_path, path_copied_jars, threadid):
    unzip_folder_for_thread = unzip_path + "/" + "dir_" + str(threadid)
    jar_copied_path_for_thread = path_copied_jars + "/" + "dir_" + str(threadid)
    clean_unzip_dir(unzip_folder_for_thread)
    clean_unzip_dir(jar_copied_path_for_thread)

    print("Making folder for thread: " + str(threadid))

    temp_shelve_map = shelve.open("save_" + str(threadid))
    for path in zip_paths:
        try:
            if unzip_repository(path, unzip_folder_for_thread):
                key = path.split(base_path)[1].split(".zip")[0]

                repo = get_dependency_jars_names(key, path, unzip_folder_for_thread, jar_copied_path_for_thread)
                temp_shelve_map[key] = repo
                temp_shelve_map.sync()
                clean_unzip_dir(unzip_folder_for_thread)
                clean_unzip_dir(jar_copied_path_for_thread)
        except CalledProcessError as e:
            print("Error found for repo: " + path)
            print(str(e))
            clean_unzip_dir(unzip_folder_for_thread)
            clean_unzip_dir(jar_copied_path_for_thread)
        except Exception as e:
            print("Error found for repo: " + path)
            print(str(e))
            clean_unzip_dir(unzip_folder_for_thread)
            clean_unzip_dir(jar_copied_path_for_thread)


if __name__ == '__main__':
    base_repo_path = "/Users/mrhmisu/previous-pc/test-bed/defect4j/projects/"
    # zip_file_paths = "/home/mdrh/JBF-Artifacts/maven_path.txt"
    unzip_dir_path = "/Users/mrhmisu/Repositories/SourcererJBF/env-test/temp"
    copied_jars_temp = "/Users/mrhmisu/Repositories/SourcererJBF/env-test/jars"

    # base_repo_path = "/Users/mrhmisu/Repositories/SourcererJBF/env-test/projects/"
    # zip_file_paths = "/Users/mrhmisu/Repositories/SourcererJBF/env-test/sample_maven.txt"
    # unzip_dir_path = "/Users/mrhmisu/Repositories/SourcererJBF/env-test/builds"
    # copied_jars_temp = "/Users/mrhmisu/Repositories/SourcererJBF/env-test/copy"

    threads = 2
    # repo_locations = get_zip_locations_from_file(zip_file_paths)
    repo_locations = get_zip_locations_path(base_repo_path)
    create_subprocess(repo_locations, unzip_dir_path, base_repo_path, copied_jars_temp, threads)
