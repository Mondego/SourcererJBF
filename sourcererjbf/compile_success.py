#!/usr/bin/env python
import json, sys
pbs = json.load(open(sys.argv[1]))
print "Total projects", len(pbs)
success_count =  len([id for id in pbs if pbs[id]["success"]])
print "Total Success", success_count, float(success_count) *100 / float(len(pbs)), "%"
print "Projects that build successfully on first try: ", len([id for id in pbs if pbs[id]["success"] and "depends" not in pbs[id]])
print "Projects that build successfully with encoding fixed", len([id for id in pbs if pbs[id]["success"] and "encoding" in pbs[id]])
print "Projects that build successfully with dependencies met", len([id for id in pbs if pbs[id]["success"] and "depends" in pbs[id]])

