#!/usr/bin/env python
import json, sys, os

pbs = dict((os.path.join(f1, f2), json.load(open(os.path.join(sys.argv[1], f1, f2, "build-result.json")))) for f1 in
           os.listdir(sys.argv[1]) for f2 in os.listdir(os.path.join(sys.argv[1], f1)))
print
"Total projects", len(pbs)
success_count = len([id for id in pbs if pbs[id]["success"]])
print
"Total Success", success_count, float(success_count) * 100 / float(len(pbs)), "%"
print
"Projects that build successfully on first try: ", len(
    [id for id in pbs if pbs[id]["success"] and "depends" not in pbs[id]])
print
"Projects that build successfully with encoding fixed", len(
    [id for id in pbs if pbs[id]["success"] and "encoding" in pbs[id]])
print
"Projects that build successfully with dependencies met", len(
    [id for id in pbs if pbs[id]["success"] and "depends" in pbs[id]])


def get_details(pid, details):
    success = details["success"]
    was_android = "was_android" in details and details["was_android"]
    had_encoding_fixed = "encoding" in details
    had_dependencies_fixed = "depends" in details
    their_build_file_used = details["create_build"]
    has_own_build = details["has_own_build"]
    total_time_spent = details["timing"][-1][1] - details["timing"][0][1]
    build_start_index = [i for i in range(len(details["timing"])) if details["timing"][i][0] == "start_build"]
    number_of_build_tries = len(build_start_index)
    try:
        time_of_last_build = details["timing"][build_start_index[-1] + 1][1] - details["timing"][build_start_index[-1]][
            1]
    except Exception:
        time_of_last_build = -1
    number_of_unique_errors = len(set(err["error_type"] for err in details["output"])) if type(
        details["output"]) == list else 0
    if "use_command" in details:
        use_ant = details["use_command"][0] == "ant"
        use_mvn = details["use_command"][0] == "mvn"
        use_gradle = details["use_command"][0] == "gradle"
    else:
        use_ant, use_mvn, use_gradle = True, False, False
    return [pid,
            success,
            was_android,
            had_encoding_fixed,
            had_dependencies_fixed,
            their_build_file_used,
            has_own_build,
            total_time_spent,
            # build_start_index,
            number_of_build_tries,
            time_of_last_build,
            number_of_unique_errors,
            use_ant, use_mvn, use_gradle]


detailed_info = [",".join(map(str, get_details(p, details))) for p, details in pbs.iteritems()]
with open(sys.argv[2], "w") as wf:
    wf.write(
        "pid,success,was_android,had_encoding_fixed,had_dependencies_fixed,our_build_file_used,has_own_build,total_time_spent,number_of_build_tries,time_of_last_build,unique_err_count,used_ant,used_mvn,used_gradle\n")
    wf.write("\n".join(detailed_info) + "\n")
