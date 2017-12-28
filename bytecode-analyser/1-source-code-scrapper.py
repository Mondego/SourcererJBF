import sys, os
import zipfile

# Set:
# PROJECTS_DIR as the path of the projects zip containers
# Finally simply run the script. It will search for
# imports in FILE_EXTENSIONS files of import_search

PROJECTS_DIR = '/Users/nhoca/Trabalho/auto-builds-paper/bytecode-analysis/java-projects'
FILE_EXTENSIONS = ['.java']
import_search = 'junit'
main_string_search = 'public static void main'

projects = []
for root, dirnames, filenames in os.walk(PROJECTS_DIR):
    for filename in filenames:
        if filename.endswith('.zip'):
            projects.append(os.path.join(root, filename))

projPath_mainsAndJunit = dict()  # Mapping proj paths constituent files with main() or junit

print('project,files_with_junit,files_with_main')
for proj in projects:
    junit_imports = 0  # count in number of files
    number_mains = 0

    with zipfile.ZipFile(proj, 'r') as proj_zip:

        projPath_mainsAndJunit[proj] = dict()
        print(proj)

        for file in proj_zip.infolist():
            if os.path.splitext(file.filename)[1] not in FILE_EXTENSIONS:
                continue
            with proj_zip.open(file.filename, 'r') as my_zip_file:
                if my_zip_file is None:
                    continue  # Shouldn't happen, but...
                try:
                    zip_string = my_zip_file.read().decode('utf-8')

                    if main_string_search in zip_string:
                        print(file.filename,'has main')
                        number_mains += 1

                    imports = [f for f in zip_string.split('\n') if f.startswith('import')]
                    # print(imports)
                    imports = [import_search in f for f in imports]
                    if any(imports):
                        junit_imports += 1
                except:
                    continue

    #print(proj, junit_imports, number_mains)




