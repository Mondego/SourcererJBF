import os
import sys
import zipfile
from subprocess import check_output, run, call, CalledProcessError, STDOUT, PIPE
from multiprocessing import Process, Queue

# This script, extracts a zip file into a temp directory, searches for AndroidManifest.xml
# If found moved that zip into a destination directory

NUMBER_OF_THREADS = 10


def create_subprocess_of_android_filtering(repo_location, unzip_path, moved_path, tc):
    global NUMBER_OF_THREADS
    NUMBER_OF_THREADS = tc
    threads = []
    for i in range(NUMBER_OF_THREADS):
        threads.append(Process(target=search_android_repository,
                               args=(repo_location[i::NUMBER_OF_THREADS], unzip_path, moved_path, i)))
        threads[-1].daemon = True
        threads[-1].start()

    for i in range(NUMBER_OF_THREADS):
        threads[i].join()


def is_android_repository(unzip_path):
    var = check_output(["find", unzip_path, "-name", "AndroidManifest.xml"], encoding='utf8')
    if not var:
        return False
    else:
        return True


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


def move_repository(zip_path, moved_path):
    try:
        check_output(["mv", zip_path, moved_path], encoding='utf8')
        return True
    except Exception as e:
        print('FAILURE -in MOVING', e)
        return False


def get_zip_locations_from_file(file_path):
    with open(file_path) as f:
        paths = f.read().splitlines()
        return paths


def clean_unzip_dir(folder):
    call(["rm", "-r", "-f", folder])
    os.makedirs(folder)
    print("Cleaning up..." + folder)


def filter_android_repository(zip_path, unzip_path, moved_dir, tc):
    try:
        print("Processing. started..." + zip_path + "by the Thread: " + str(tc))
        if unzip_repository(zip_path, unzip_path):
            if is_android_repository(unzip_path):
                if move_repository(zip_path, moved_dir):
                    print(zip_path + "----> successfully moved to --->" + moved_dir)
                    clean_unzip_dir(unzip_path)
                    return True
        clean_unzip_dir(unzip_path)

    except Exception as e:
        print("FAILED TO PROCESS:.." + zip_path + "for--" + e)
        clean_unzip_dir(unzip_path)
        return False


def search_android_repository(zip_locations, unzip_path, moved_dir, tc):
    unzip_folder_for_thread = unzip_path + "/" + "dir_" + str(tc)
    check_output(["mkdir", unzip_folder_for_thread], encoding='utf8')
    print("Making folder for thread: " + str(tc))
    count = 0
    total = len(zip_locations)
    for path in zip_locations:
        if filter_android_repository(path, unzip_folder_for_thread, moved_dir, tc):
            print("Processing is done .. " + path + "by the Thread: " + str(tc))
        count += 1
        if count % 100 == 0:
            print("Thread " + str(tc) + ": " + str(count) + "/" + str(total))


if __name__ == '__main__':

    if len(sys.argv) < 5:
        print("Usage: ./android-filter.py <file_with_zip_locations> <temp_unzip_dir_path> <moved_dir_path> <threads>")
        sys.exit(0)
    if len(sys.argv) == 5:
        zip_file_paths = sys.argv[1]
        unzip_dir_path = sys.argv[2]
        moved_dir_path = sys.argv[3]
        threads = int(sys.argv[4])
        locations = get_zip_locations_from_file(zip_file_paths)
        create_subprocess_of_android_filtering(locations, unzip_dir_path, moved_dir_path, threads)
