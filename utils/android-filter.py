import os
import sys
import zipfile
from subprocess import check_output, call


# this script, extract a zip file into a temp directory, search for AndroidManifest
# if found moved that zip into a destination directory

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
            print('SUCCESS -', zip_path)
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
    call(["rm", "-r", "-f", folder], encoding='utf8')
    os.makedirs(folder)


def filter_android_repository(zip_path, unzip_path, moved_dir):
    try:
        if unzip_repository(zip_path, unzip_path):
            if is_android_repository(unzip_path):
                if move_repository(zip_path, moved_dir):
                    print(zip_path + "----> successfully moved to --->" + moved_dir)
                    return True
    except Exception as e:
        print("FAILED TO PROCESS:.." + zip_path + "for--" + e)
        return False


def search_android_repository(zip_locations, unzip_path, moved_dir):
    count = 0
    for path in zip_locations:
        count += 1
        if filter_android_repository(path, unzip_path, moved_dir):
            print("Processing Done..." + path)
        print("Repository counting..." + str(count))
        clean_unzip_dir(unzip_path)
        print("Cleaning up..." + unzip_path)


if __name__ == '__main__':

    if len(sys.argv) < 4:
        print("Usage: ./android-filter.py <file_with_zip_locations> <unzip_dir_path> <moved_dir_path>")
        sys.exit(0)
    if len(sys.argv) == 4:
        zip_file_paths = sys.argv[1]
        unzip_dir_path = sys.argv[2]
        moved_dir_path = sys.argv[3]
        locations = get_zip_locations_from_file(zip_file_paths)
        search_android_repository(locations, unzip_dir_path, moved_dir_path)
