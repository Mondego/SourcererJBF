import chardet, os

TEMPDIR = "TBUILD_{0}/"

def detect(filename):
  return chardet.detect(open(filename).read())["encoding"]

def FixEncoding(threadid, files, project):
  all_encodes = set([detect(file) for file in files])
  if len(all_encodes) != 1:
    return False, project
  project["encoding"] = all_encodes.pop()
  project["create_build"] = True
  return True, project
