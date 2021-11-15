import sys, os
from subprocess import check_output, call, CalledProcessError, STDOUT, Popen, PIPE

if len(sys.argv) != 5:
    print
    "Wrong number of args"
    sys.exit(0)
infold, outfold, num_per_folder = sys.argv[1], sys.argv[2], sys.argv[3]


def change_structure(infold, outfold, num_per_folder):
    current_folder_count = 0
    file_count = 0
    final_paths = []
    print
    "Writing into folder", current_folder_count
    for f in os.listdir(infold):
        current_path = os.path.join(infold, f)
        final_folder = os.path.join(outfold, current_folder_count)
        if not os.path.exists(final_folder):
            os.makedirs(final_folder)
        final_path = os.path.join(final_folder, f)
        check_output(["cp", current_path, final_path])
        final_paths.append(os.path.join(current_folder_count, f))
        file_count += 1
        if file_count == num_per_folder:
            file_count = 0
            current_folder_count += 1
            print
            "Writing into folder", current_folder_count
    return final_paths


final_paths = change_structure(infold, outfold, num_per_folder)
open(sys.argv[4], "w").write("\n".join(final_paths))
