import chardet

TEMPDIR = "TBUILD_{0}/"

ISO_WIN_MAP = {'Windows-1252': 'iso-8859-1',
               'Windows-1250': 'iso-8859-2',
               'Windows-1251': 'iso-8859-5',
               'Windows-1256': 'iso-8859-6',
               'Windows-1253': 'iso-8859-7',
               'Windows-1255': 'iso-8859-8',
               'Windows-1254': 'iso-8859-9',
               'Windows-1257': 'iso-8859-13'}


def detect(filename):
    rawdata = open(filename, 'rb').read()
    result = chardet.detect(rawdata)
    charenc = "UTF-8"
    if "Windows" in result['encoding']:
        charenc = ISO_WIN_MAP[result['encoding']]
    # chardet.detect(open(filename).read())["encoding"]
    return charenc


def FixEncoding(threadid, files, project):
    all_encodes = set([detect(file) for file in files])
    if len(all_encodes) != 1:
        return False, project
    project["encoding"] = all_encodes.pop()
    project["create_build"] = True
    return True, project
