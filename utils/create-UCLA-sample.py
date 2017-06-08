import sys, os
from optparse import OptionParser
from shutil import copy2, copytree
import xml.etree.ElementTree as ET

JARS_LOCATION = '/extra/lopes1/mondego-data/jars/' # KEEP THE '/' in the end if you edit this

#Paths for output
PATH_result_projects = 'sample/projects'
PATH_result_jars     = 'sample/jars'
PATH_result_builds   = 'sample/builds'

def copy_projects(list_projects,projects_dir):
  for project in list_projects:
    path = os.path.join(PATH_result_projects,os.path.dirname(project))
    if not os.path.isdir(path):
      os.makedirs(path)

    copy2(os.path.join(projects_dir,project),os.path.join(PATH_result_projects,project))

def copy_builds(list_projects,builds_dir):
  for project in list_projects:
    project = project[:-4] # Remove .zip
    path = os.path.join(PATH_result_builds,os.path.dirname(project))
    if not os.path.isdir(path):
      os.makedirs(path)

    copytree(os.path.join(builds_dir,project),os.path.join(PATH_result_builds,project))

def copy_jars(list_projects):
  for project in list_projects:
    build_file = os.path.join(PATH_result_builds,project[:-4],'custom_build_script','build.xml')
    
    tree = ET.parse(build_file)
    root = tree.getroot()

    list_jars = set()

    for child in root.findall('target'):
      if child.get('name') == 'compile':
        for jars in child.find('javac').find('classpath').findall('pathelement'):
          if JARS_LOCATION in jars.get('path'):
            list_jars.add(jars.get('path'))

    for origin in list_jars:
      dest_jar  = os.path.join(PATH_result_jars,origin[len(JARS_LOCATION):])
      dest_path = os.path.dirname(dest_jar)
      if not os.path.isdir(dest_path):
        os.makedirs(dest_path)

      copy2(origin,dest_jar)

def yes_no():
  print """****** This scripts assumes that jar files are located at:
******     %s.
****** This script also assumes the extension of the archives of the projects has
******     3 characters (zip,tar).
****** Press enter to continue. """ % JARS_LOCATION

  while True:
    choice = raw_input().lower()
    return

if __name__ == "__main__":

  parser = OptionParser()
  parser.add_option("-l", "--listProjects", dest="listProjects", type="string", default=False,
                    help="List of projects that will be copied.")

  parser.add_option("-d", "--projectsDirectory", dest="projectsDirectory", type="string", default=False,
                    help="The path for the projects, relative to the projects from the projects list.")

  parser.add_option("-b", "--builds", dest="builds", type="string", default=False,
                    help="The path to the successfull builds from JBF, relative to the projects from the projects list.")

  (options, args) = parser.parse_args()

  list_projects = set()
  projects_dir  = None
  builds_dir    = None

  yes_no()

  if os.path.isdir(PATH_result_projects) or os.path.isdir(PATH_result_jars) or os.path.isdir(PATH_result_builds):
    print "Folders '%s', '%s' or '%s' already exist!" % (PATH_result_projects,PATH_result_jars,PATH_result_builds)
    sys.exit(0)

  if not len(sys.argv) > 1:
    print "No arguments were passed. Try running with '--help'."
    sys.exit(0)

  if not options.listProjects:
    print "Arguments '-l' missing. Try running with '--help'."
    sys.exit(0)
  else:
    with open(options.listProjects,'r') as file:
      for proj in file:
        list_projects.add(proj.strip())

  if not options.projectsDirectory:
    print "Arguments '-d' missing. Try running with '--help'."
    sys.exit(0)
  else:
    projects_dir = options.projectsDirectory

  if not options.builds:
    print "Arguments '-b' missing. Try running with '--help'."
    sys.exit(0)
  else:
    builds_dir = options.builds
  
  print 'Copying projects ...'
  copy_projects(list_projects,projects_dir)
  print 'Copying builds/ ...'
  copy_builds(list_projects,builds_dir)
  print 'Copying JAR files ...'
  copy_jars(list_projects)
  print "Finished. Results in 'sample/'."
