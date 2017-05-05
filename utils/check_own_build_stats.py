import json, os, sys
projects = [os.path.join(f1, f2) for f1 in os.listdir(sys.argv[2]) for f2 in os.listdir(os.path.join(sys.argv[2], f1))]
pd = dict((pid, json.load(open(os.path.join(sys.argv[2], pid, "build-result.json")))) for pid in projects)
pd_new = dict((pid, pd[pid]) for pid in pd if "has_own_build" in pd[pid] and pd[pid]["has_own_build"])
pd_old = dict((pid, json.load(open(os.path.join(sys.argv[1], pid, "build-result.json")))) for pid in pd_new)

print "Total Projects compares: ", len(pd_new)
print "Total success in new: ", len([pid for pid in pd_new if pd_new[pid]["success"]])
print "Total success in old: ", len([pid for pid in pd_old if pd_old[pid]["success"]])
print "Ant success in new: ", len([pid for pid in pd_new if pd_new[pid]["success"] and pd_new[pid]["use_command"][0] == "ant"])
print "Ant success in old: ", len([pid for pid in pd_new if pd_old[pid]["success"] and pd_new[pid]["use_command"][0] == "ant"])
print "Mvn success in new: ", len([pid for pid in pd_new if pd_new[pid]["success"] and pd_new[pid]["use_command"][0] == "mvn"])
print "Mvn success in old: ", len([pid for pid in pd_new if pd_old[pid]["success"] and pd_new[pid]["use_command"][0] == "mvn"])
print "Gradle success in new: ", len([pid for pid in pd_new if pd_new[pid]["success"] and pd_new[pid]["use_command"][0] == "gradle"])
print "Gradle success in new: ", len([pid for pid in pd_new if pd_old[pid]["success"] and pd_new[pid]["use_command"][0] == "gradle"])
open("success_ours_failed_theirs.txt", "w").write("\n".join([pid for pid in pd_new if not pd_new[pid]["success"] and pd_old[pid]["success"]]) + "\n")
open("success_theirs_failed_ours.txt", "w").write("\n".join([pid for pid in pd_new if pd_new[pid]["success"] and not pd_old[pid]["success"]]) + "\n")
print "Success in both: ", len([pid for pid in pd_new if pd_new[pid]["success"] and pd_old[pid]["success"]])
print "Success only in theirs: ", len([pid for pid in pd_new if pd_new[pid]["success"] and not pd_old[pid]["success"]])
print "Succes only in ours: ", len([pid for pid in pd_new if not pd_new[pid]["success"] and pd_old[pid]["success"]])
print "Both Fail: ", len([pid for pid in pd_new if not pd_new[pid]["success"] and not pd_old[pid]["success"]])

