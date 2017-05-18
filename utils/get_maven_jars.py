import sys, os
import xml.etree.ElementTree as ET
import zipfile
from subprocess import check_output
import logging
from multiprocessing import Process, Value, Queue
import datetime as dt
import time

# If a path needs to be appended to the list of project paths
projects_abs_path = '' #'/extra/lopes1/mondego-data/projects/di-stackoverflow-clone/github-repo/java-projects'

JAR_FOLDER = 'JARS'
EXTRACT_FOLDER = 'extractEnv'
N_PROCESSES = 2
PROJECTS_BATCH = 2

# This function grabs a zip, searches for a pom.xml file, if it exists
# downloads all the dependencies using maven to a ./target/dependencies
def get_maven_dependencies_from_zip(zip_path, process_num, logging, jar_folder, extract_folder):

  pom_file = None

  with zipfile.ZipFile(os.path.join(projects_abs_path,zip_path)) as z:
    for line in z.namelist():
      line_strip = line.strip()
      if line_strip.endswith("pom.xml"):
        pom_file = line_strip
        break

    if pom_file is None:
      logging.info('No pom.xml file on '+zip_path)
      return

    logging.info(pom_file+' found for '+zip_path)

    z.extractall(extract_folder)

    #with open(os.path.join(working_dir,'pom.xml'),'w') as file:
    #  file.write(z.read(pom_file))
  output = ''
  try:
    output = check_output(["mvn", "dependency:copy-dependencies", "-DoutputDirectory="+jar_folder, "-f", os.path.join(extract_folder,pom_file)])
  except Exception as e:
    logging.info('Maven exception on '+zip_path)

  new_jars = 0
  jar_already_existed = 0

  for line in output.split('\n'):
    if 'already exists in destination.' in line:
      jar_already_existed += 1
    else:
      if '[INFO] Copying' in line:
        new_jars += 1

  logging.info(zip_path+' has ended with '+str(new_jars)+' new JARs and '+str(jar_already_existed)+' existing ones')
  
  # A little dirty, but so is life
  os.system('rm -rf '+os.path.join(extract_folder+'/*'))

def process_projects(process_num, list_projects, global_queue, working_dir, jar_folder):
  extract_folder = os.path.join(working_dir,EXTRACT_FOLDER+str(process_num))
  if not os.path.isdir(extract_folder):
    os.makedirs(extract_folder)

  # Logging code
  FORMAT = '[%(levelname)s] (%(threadName)s) %(message)s'
  logging.basicConfig(level=logging.DEBUG,format=FORMAT)
  file_handler = logging.FileHandler(os.path.join(working_dir,'LOG'+str(process_num)+'.log'))
  file_handler.setFormatter(logging.Formatter(FORMAT))
  logging.getLogger().addHandler(file_handler)

  #with open(inputt,'r') as projects_path:
  #  for path in projects_path:
  #    logging.info('Reading '+path.strip())

  for proj in list_projects:
    logging.info('Starting '+proj.strip())
    get_maven_dependencies_from_zip(proj.strip(), process_num, logging, jar_folder, extract_folder)

  time.sleep(2)
  global_queue.put(process_num)
  sys.exit(0)


def get_dependencies(pom_path):
  tree = ET.parse(pom_path)
  root = tree.getroot()

  namespace = {'xmlns' : root.tag.split('}')[0].strip('{')}

  depend = root.findall(".//xmlns:dependency",namespace)

#    <dependency>
#      <groupId>com.saucelabs</groupId>
#      <artifactId>sauce_junit</artifactId>
#      <version>2.1.23</version>
#      <scope>test</scope>
#    </dependency>

  for d in depend:
    groupId    = d.find("xmlns:groupId",    namespaces=namespace)
    artifactId = d.find("xmlns:artifactId", namespaces=namespace)
    version    = d.find("xmlns:version",    namespaces=namespace)
    scope      = d.find("xmlns:scope",      namespaces=namespace)
    print ('%s\t%s\t%s') % (groupId.text,artifactId.text,version.text) # artifactId.text + '\t' + version.text

def start_child(processes, global_queue, proj_paths, batch, working_dir, jar_folder):
  # This is a blocking get. If the queue is empty, it waits
  pid = global_queue.get()
  # OK, one of the processes finished. Let's get its data and kill it
  kill_child(processes, pid)

  # Get a new batch of project paths ready
  paths_batch = proj_paths[:batch]
  del proj_paths[:batch]

  print "Starting new process %s" % (pid)
  p = Process(name='Process '+str(pid), target=process_projects, args=(pid, paths_batch, global_queue, working_dir, jar_folder, ))
  processes[pid] = p
  p.start()

def kill_child(processes, pid,):
  if processes[pid] != None:
    processes[pid] = None
    
  print "Process %s finished." % (pid)

def active_process_count(processes):
  count = 0
  for p in processes:
    if p != None:
      count +=1
  return count

if __name__ == "__main__":
  p_start = dt.datetime.now()

  # If someone wants to change the working dir later only has to direct
  # STDIN to this var
  working_dir = os.path.join(os.getcwd(),'dependenciesEnv')
  print 'Working dir',working_dir

  # jar_folder is shared for all the processes, and is where all jars are downloaded to
  # by maven
  jar_folder = os.path.join(working_dir,JAR_FOLDER)

  # This code will need to be in the beginning of each subprocess
  if not os.path.isdir(working_dir):
    os.makedirs(working_dir)
  if not os.path.isdir(jar_folder):
    os.makedirs(jar_folder)

  proj_paths = []
  with open(sys.argv[1],'r') as f:
    for line in f:
      proj_paths.append(line.strip())
  
  n_projects = len(proj_paths)

  # Multiprocessing with N_PROCESSES
  # [process, project_count]
  processes = [None for i in xrange(N_PROCESSES)]
  # The queue for processes to communicate back to the parent (this process)
  global_queue = Queue()
  for i in xrange(N_PROCESSES):
    global_queue.put(i)

  # Start all other projects
  print "*** Starting projects..."
  while len(proj_paths) > 0:
    start_child(processes, global_queue, proj_paths, PROJECTS_BATCH, working_dir, jar_folder)

  print "*** No more projects to process. Waiting for children to finish..."
  while active_process_count(processes) > 0:
    pid = global_queue.get()
    kill_child(processes, pid)

  p_elapsed = dt.datetime.now() - p_start
  print "*** All done. %s projects in %s" % (n_projects, p_elapsed)

    #print 'Reading pom:',pom_file
    #get_dependencies(pom_file)
