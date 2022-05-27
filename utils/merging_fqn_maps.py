import os
import shelve
import sys


def merge_fqn_map(fqn_map_path_1, fqn_map_path_2, merge_output):
    map_1 = shelve.open(fqn_map_path_1, 'r')
    map_2 = shelve.open(fqn_map_path_2, 'r')
    glob_map = shelve.open(merge_output)

    count = 0
    for fqn in map_1:
        try:
            count += 1
            glob_map[str(fqn)] = map_1[fqn]
            glob_map.sync()
            print("Processing fqn no: " + str(count) + "==" + fqn)
        except Exception as e:
            print("Exception (probably decoding) when writing out fqn: " + fqn + e)
    for fqn in map_2:
        try:
            count += 1
            glob_map[str(fqn)] = map_2[fqn]
            glob_map.sync()
            print("Processing fqn no: " + str(count) + "==" + fqn)
        except Exception as e:
            print("Exception (probably decoding) when writing out fqn: " + fqn + e)

    print(fqn_map_path_1 + "==size==" + str(len(map_1)))
    print(fqn_map_path_2 + "==size==" + str(len(map_2)))
    print(merge_output + "==size==" + str(len(glob_map)))
    map_1.close()
    map_2.close()
    glob_map.close()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: ./fqn_to_jar_map_generator.py <map1_path> <map2_path> <merge_map_path>")
        sys.exit(0)
    if len(sys.argv) == 4:
        map1_path = sys.argv[1]
        map2_path = sys.argv[2]
        merge_map_path = sys.argv[3]
        merge_fqn_map(map1_path, map2_path, merge_map_path)
