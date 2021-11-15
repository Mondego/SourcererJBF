# from sourcererjbf.fqn_to_jar_map_generator import get_all_fqns_from_path
import sys, time, os, re
from subprocess import check_output, STDOUT
import ujson as json
from multiprocessing import Process, Lock, Queue
from sourcererjbf.utils import create_logger
from Queue import Empty


# logger = create_logger("fqn_to_jar")
def get_all_variations(fqn_parts):
    fqns = set([fqn_parts[0]])
    for i in range(1, len(fqn_parts) + 1):
        fqns.add(".".join(fqn_parts[:i]))
    return fqns


def get_all_fqns_from_path(path):
    all_paths = set()
    for line in check_output(["jar", "tf", path], stderr=STDOUT).split("\n"):
        if line.endswith(".class"):
            new_line = "/".join(l for l in line[:-6].split("$") if not re.match(r"\d+", l))
            if new_line == line[:-6].split("$")[0]:
                continue
            all_paths.update(get_all_variations([p for p in new_line.split("/") if p != ".." and p != "."]))
    return all_paths


fqnfile, root, THREADCOUNT = sys.argv[1], sys.argv[2], int(sys.argv[3])
print
"Loading jars"
start = time.time()
fqn_to_jars = json.load(open(fqnfile))
end = time.time() - start
print
"Loading complete", end

all_jars = set()
for fqn in fqn_to_jars:
    all_jars.update(set(fqn_to_jars[fqn]))
    fqn_to_jars[fqn] = set(fqn_to_jars[fqn])

all_jars = list(all_jars)


def mapper(threadid, jars, outq):
    count = 0
    logger = create_logger("logs/fqn_to_jar%d" % threadid)
    save = open("saves/fqn_to_jars_%d.sav" % threadid, "w")
    for jar_file in jars:
        count += 1
        if count % 100 == 0:
            print
            "THREAD %d, finished %d" % (threadid, count)
        try:
            jpath = os.path.join(root, jar_file)
            logger.info("Processing %s" % jpath)
            fqns = get_all_fqns_from_path(jpath)
            fqns_missing = set(fqn for fqn in fqns if fqn not in fqn_to_jars or jar_file not in fqn_to_jars[fqn])
            for mfqn in fqns_missing:
                outq.put((mfqn, jar_file))
                save.write("%s\t%s\n" % (mfqn, jar_file))
        except Exception:
            # raise
            print
            "Found Exception"
            continue


def reducer(outq):
    fqn_map = dict()
    count = 0
    while True:
        try:
            item = outq.get_nowait()
        except Empty:
            break
        fqn, jar = item
        fqn_map.setdefault(fqn, set()).add(jar)

    for f in fqn_map:
        fqn_to_jars.setdefault(f, set()).update(fqn_map[f])
    for f in fqn_to_jars:
        fqn_to_jars[f] = list(fqn_to_jars[f])


# p = Queue()
outq = Queue()
processes = list()
# for j in all_jars:
#    p.put(j)
# print "Added all jars into queue", len(all_jars)

# for i in range(THREADCOUNT):
#    p.put("DONE")
print
"Starting the threads."
for i in range(THREADCOUNT):
    processes.append(Process(target=mapper, args=(i, all_jars[i::THREADCOUNT], outq)))
    processes[-1].daemon = True
    processes[-1].start()
for p in processes:
    p.join()
print
"Starting reducer"
reducer(outq)
print
"Done with all threads."
json.dump(fqn_to_jars, open(fqnfile + ".new", "w"), indent=4, sort_keys=True, escape_forward_slashes=False)
