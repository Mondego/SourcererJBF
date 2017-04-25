import json


all_projs = json.load(open("project_success.json"))
err_map = dict()
print "START"
c = 0
for i in all_projs:
	if not all_projs[i]["success"]:
		for err in all_projs[i]["output"]:
			err_map.setdefault(err["error_type"], set()).add(i)
	c += 1
	if c% 10000 == 0:
		print c, len(all_projs)



err_count = dict([(e, len(items)) for e, items in err_map.items()])
output = open("project_stats.txt", "w")
output.write("Number of errors %d\n" % len(err_count))
error_sorted = sorted(err_count.items(), key = lambda x: x[1], reverse = True)
for e, count in error_sorted:
	try:
		output.write(e + (" %d\n" % count))
	except Exception:
		continue
output.close()
#json.dump(err_map, open("project_error_map.json", "w"), sort_keys = True, indent = 4, separators=(',', ': '))
json.dump(dict((e, list(items)) for e, items in err_map.items()), open("project_error_map.json", "w"), sort_keys = True, indent = 4, separators=(',', ': '))
print "DONE"
