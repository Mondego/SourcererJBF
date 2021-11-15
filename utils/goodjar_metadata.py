import zipfile
from multiprocessing import Process
# from sourcererjbf.fqn_to_jar_map_generator import get_all_fqns_from_path
import shelve, os, json
from subprocess import check_output, call, CalledProcessError, STDOUT

goodjars = open("goodjars.txt").read().split("\n")[:-1]
THREADCOUNT = 1120
ROOT = "/extra/lopes1/mondego-data/jars"
processes = list()


def scrape(i, jars):
    count = 0
    saver = shelve.open("saves/scrape.shelve.%d" % i)
    for j in jars:
        count += 1
        if count % 100 == 0:
            print
            "THREAD", i, count, len(jars)
        try:
            zf = zipfile.ZipFile(os.path.join(ROOT, j))
            saver[j] = zf.namelist()
            saver.sync()
        except Exception as e:
            print
            "There was exception.", e, j
            try:
                saver[j] = check_output(["jar", "tf", os.path.join(ROOT, j)], stderr=STDOUT).split("\n")
                saver.sync()
            except Exception as e:
                print
                "There was another exception.", e, j


# for i in range(THREADCOUNT):
#  processes.append(Process(target = scrape, args = (i, goodjars[i::THREADCOUNT])))
#  processes[-1].daemon = True
#  processes[-1].start()

# for i in range(THREADCOUNT):
#  processes[i].join()

full_namelist = dict()
for i in range(THREADCOUNT):
    full_namelist.update(dict(shelve.open("saves/scrape.shelve.%d" % i)))

json.dump(full_namelist, open("jar_details.json", "w"), indent=4, sort_keys=True, separators=(',', ': '))
