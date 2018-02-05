import sys, os
import json
import shutil
import logging
from zipfile import ZipFile
from javatools import unpack_classfile
from multiprocessing import Process, Pool
from subprocess import check_output, STDOUT, CalledProcessError

# Set:
# PROJECTS_BUILDS_DIR as builds/ output of JBF
# PROJECTS_SOURCES_DIR as projects' zips path
# N_PROCESSES as best suits
# Finally, simply run the script

PROJECTS_BUILDS_DIR = os.path.abspath('some-path/builds')
# Need sources to grab local jar files
PROJECTS_SOURCES_DIR = os.path.abspath('some-path/java-projects')
JARS_DIR = 'some-path/jars'
N_PROCESSES = 2

#### SHOULD not need to touch anything below ####
# Where all the OUTPUT_FILE's are written:
OUTPUT_FOLDER = 'output'
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, 'bytecode-info-%s.csv')
LOGS_PATH = 'logs'

# Strings to search within method names and imports to find main and junit, respectively
main_search_string = 'main'
junit_search_string = 'junit'

FILE_EXTENSIONS = ['.class']


def run_main(root_path, file_path):
    # Example: 'java -cp .:lava-master/build/: com.golaszewski.lava.evaluate.REPL'
    cmd_main = 'java -cp .:%s: %s'

    cmd_path = root_path[:root_path.find('/build/') + 7]
    class_path = os.path.join(root_path, file_path)
    class_path = class_path[class_path.find('/build/') + 7:-6].replace('/', '.')

    cmd = cmd_main % (cmd_path, class_path)
    print(cmd)

    try:
        o = check_output(cmd, stderr=STDOUT, shell=True)
        returncode = 0
    except CalledProcessError as ex:
        o = ex.output
    output = o.decode('utf-8')

    return output


# Finds reachable methods from main
# TODO check with christian the strange behavior of wiretap
def reachable_methods_from_main(root_path, file_path, jar_paths, pid):
    temp_folder = pid + '-wiretap'

    # Example: 'java -cp .:lava-master/build/: -javaagent:wiretap.jar -Dwiretap.recorder=ReachableMethods com.golaszewski.lava.evaluate.REPL'
    cmd_wiretap = 'java -cp .:%s:%s: -javaagent:wiretap.jar -Dwiretap.outfolder=\"' + temp_folder + '\" -Dwiretap.recorder=ReachableMethods %s'

    cmd_path = root_path[:root_path.find('/build/') + 7]
    class_path = os.path.join(root_path, file_path)
    class_path = class_path[class_path.find('/build/') + 7:-6].replace('/', '.')

    cmd = cmd_wiretap % (cmd_path, jar_paths, class_path)
    logging.info(cmd)

    try:
        o = check_output(cmd, stderr=STDOUT, shell=True)
        returncode = 0
    except CalledProcessError as ex:
        o = ex.output
    output = o.decode('utf-8')

    print(cmd+'\n'+output)

    total_reachable_methods = 0
    with open(os.path.join(temp_folder, 'reachable.txt'), 'r') as reachable:
        total_reachable_methods = len(reachable.readlines())
    shutil.rmtree(temp_folder)
    return total_reachable_methods


# Returns True if all tests passed, False otherwise
def all_junit_tests(root_path, file_path, jar_paths):
    """
    Example: 'java -cp .:junit-4.12.jar:hamcrest-core-1.3.jar:/Users/nhoca/Trabalho/auto-builds-paper/bytecode-analysis
    /java-builds/35/bodawei-JPEGFile/build/: org.junit.runner.JUnitCore bdw.formats.jpeg.data.ExtraFfTest
    """

    cmd_main = 'java -cp .:junit-4.12.jar:hamcrest-core-1.3.jar:%s:%s: org.junit.runner.JUnitCore %s'

    cmd_path = root_path[:root_path.find('/build/') + 7]
    class_path = os.path.join(root_path, file_path)
    class_path = class_path[class_path.find('/build/') + 7:-6].replace('/', '.')

    cmd = cmd_main % (cmd_path, jar_paths, class_path)
    logging.info(cmd)

    try:
        o = check_output(cmd, stderr=STDOUT, shell=True)
        returncode = 0
    except CalledProcessError as ex:
        o = ex.output
    output = o.decode('utf-8')

    for line in output.split('\n'):
        if 'OK (' in line:
            return True

    return False


# Returns java-ready, ':' separated list of full paths of jars
def handle_dependencies(proj_path, pid):
    proj_zip_path = None
    jar_paths = list()

    print(proj_path)

    with open(os.path.join(proj_path, 'build-result.json'), 'r') as file:
        json_file = json.load(file)
        if 'depends' in json_file:
            for dep in json_file['depends']:
                if dep[5]:
                    if proj_zip_path is None:
                        proj_zip_path = os.path.join(PROJECTS_SOURCES_DIR, json_file['file'] + '.zip')
                        # print(proj_zip_path)
                    with ZipFile(proj_zip_path, 'r') as proj_zip:
                        proj_zip.extract(member=dep[4], path=pid)
                        jar_paths.append(os.path.join(pid, dep[4]))
                else:
                    jar_paths.append(os.path.join(JARS_DIR, dep[4]))
        else:
            return ' '

    # print(jar_paths)
    return ':'.join(jar_paths)


# main call
def process(list_projs):
    pid = os.getpid()
    print('Starting process', pid, '...')

    # Logging code
    FORMAT = '[%(levelname)s] (%(threadName)s) %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    file_handler = logging.FileHandler(os.path.join(LOGS_PATH, 'LOG-' + str(pid) + '.log'))
    file_handler.setFormatter(logging.Formatter(FORMAT))
    logging.getLogger().addHandler(file_handler)

    proj_counter = 0

    # TODO Make script start from a list of files intead of the results of JBF
    with open(OUTPUT_FILE % pid, 'w') as output_file:
        output_file.write('proj_name,n_class_files,reachable_mains,reachable_methods,with_junit,passed_junit\n')

        for full_proj_folder in list_projs:
            # print(full_proj_folder)
            proj_counter += 1

            if not os.path.exists(str(pid)):
                os.makedirs(str(pid))
            else:
                raise Exception('Folder ' + str(pid) + ' already exists!')
            jar_paths = handle_dependencies(full_proj_folder, str(pid))
            # print(jar_paths)

            # These counts are class files/per project
            reachable_mains = 0
            reachable_methods = 0  # Per class file with main() found
            with_junit = 0
            passed_junit = 0
            n_class_files = 0

            # Search for Class files
            for root, dirnames, filenames in os.walk(full_proj_folder):
                for filename in filenames:
                    if filename.endswith('.class'):
                        full_filename = os.path.join(root, filename)
                        # print('Analyzing file', full_filename)

                        try:
                            n_class_files += 1
                            ci = unpack_classfile(full_filename)
    
                            # Search for main methods and run the respective class files
                            main_methods = main_search_string in [m.get_name() for m in ci.methods]
                            if main_methods:
                                # print('Has main:', full_filename)
                                reachable_mains += 1
                                res = 0 # reachable_methods_from_main(root, filename, jar_paths, str(pid))
                                # res = run_main(root, filename)
                                reachable_methods += res
    
                            # Search for junit and run the respective class files
                            junit_imports = [m for m in ci.get_requires() if junit_search_string in m]
                            if len(junit_imports) > 0:
                                # print('Has junit:', full_filename)

                                with_junit += 1
                                # res = all_junit_tests(root, filename, jar_paths)

                                if res:
                                    # print('All tests OK!')
                                    passed_junit += 1

                        except:
                            continue
            shutil.rmtree(str(pid))

            result = full_proj_folder + ',' + str(n_class_files) + ',' + str(reachable_mains) + ',' + str(
                reachable_methods) + ',' + str(with_junit) + ',' + str(passed_junit)

            if (proj_counter % 10) == 0:
                print('-----------------------------------------')
                print('Process', pid, 'analyzed', proj_counter, '/', len(list_projs), 'projects...')
                print(result)

            output_file.write(result + '\n')


if __name__ == '__main__':
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    if not os.path.exists(LOGS_PATH):
        os.makedirs(LOGS_PATH)

    list_projects = []
    for proj_folder in os.listdir(PROJECTS_BUILDS_DIR):
        for proj in os.listdir(os.path.join(PROJECTS_BUILDS_DIR, proj_folder)):
            full_proj_folder = os.path.join(os.path.join(PROJECTS_BUILDS_DIR, proj_folder), proj)
            list_projects.append(full_proj_folder)
            print('Found project', full_proj_folder, '...')

    list_projects_split = [list_projects[i::N_PROCESSES] for i in range(N_PROCESSES)]

    p = Pool(N_PROCESSES)
    p.map(process, list_projects_split)
