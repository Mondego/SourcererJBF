import os
import sys
from subprocess import check_output, run, call, CalledProcessError, STDOUT, PIPE
from multiprocessing import Process, Queue

NUMBER_OF_THREADS = 10


def create_subprocess_moving(zip_locations, moved_path, tc):
    global NUMBER_OF_THREADS
    NUMBER_OF_THREADS = tc
    threads = []
    for i in range(NUMBER_OF_THREADS):
        threads.append(Process(target=move_all_repos,
                               args=(zip_locations[i::NUMBER_OF_THREADS], moved_path, i)))
        threads[-1].daemon = True
        threads[-1].start()

    for i in range(NUMBER_OF_THREADS):
        threads[i].join()


def move_all_repos(zip_locations, moved_dir, tc):
    print("Process--" + str(tc) + "--started")
    moved_folder_for_thread = moved_dir + "/" + "dir_" + str(tc)
    check_output(["mkdir", moved_folder_for_thread], encoding='utf8')
    print("Making folder for thread: " + str(tc))
    count = 0
    total = len(zip_locations)
    for path in zip_locations:
        count += 1
        move_repo(path, moved_folder_for_thread)
        print(str(count) + "--out of--" + str(total) + "--moved by process" + str(tc))
    print("Process--" + str(tc) + "--end")


def move_repo(zip_path, moved_path):
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


if __name__ == '__main__':

    if len(sys.argv) < 4:
        print("Usage: ./repo_distributor.py <file_with_zip_locations> <moved_dir_path> <threads>")
        sys.exit(0)
    if len(sys.argv) == 4:
        zip_file_paths = sys.argv[1]
        moved_dir_path = sys.argv[2]
        threads = int(sys.argv[3])

        locations = get_zip_locations_from_file(zip_file_paths)
        create_subprocess_moving(locations, moved_dir_path, threads)
