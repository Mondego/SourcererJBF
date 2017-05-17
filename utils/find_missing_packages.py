# usage python find_missing_packages.py fqn-to-jars.json project_details.json builds
import json, sys

fqn_map = json.load(open(sys.argv[1]))

ps = dict((pid, json.load(open(sys.argv[3] + "/" + pid + "/build-result.json")))for pid in json.load(open(sys.argv[2])))
really_missing = sorted(list(set([err["package"] for pid, details in ps.iteritems() if not details["success"] for err in details["output"] if "package" in err and err["package"] not in fqn_map])))
open("really_missing.txt", "w").write("\n".join(really_missing) + "\n")
