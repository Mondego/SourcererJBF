import sys, os
import xml.etree.ElementTree as ET
import zipfile
from subprocess import check_output
import logging
from multiprocessing import Process, Value, Queue
import datetime as dt
import time
from optparse import OptionParser

# If a path needs to be appended to the list of project paths
projects_abs_path = '' #'/extra/lopes1/mondego-data/projects/di-stackoverflow-clone/github-repo/java-projects'

JAR_FOLDER = 'JARS'
EXTRACT_FOLDER = 'extractEnv'
N_PROCESSES = 2
PROJECTS_BATCH = 5
TIMEOUT_MAVEM = 20 # seconds

# List with projects that were already processed
already_processed = set()

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
    #output = check_output(["timeout",str(TIMEOUT_MAVEM),"mvn", "dependency:copy-dependencies", "-DoutputDirectory="+jar_folder, "-f", os.path.join(extract_folder,pom_file)])
    output = check_output(["mvn", "dependency:copy-dependencies", "-DoutputDirectory="+jar_folder, "-f", os.path.join(extract_folder,pom_file)])
  except Exception as e:
    logging.info('Maven exception on '+zip_path)
    return

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

def process_projects(process_num, list_projects, global_queue, working_dir, jar_folder, already_processed):
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
    if proj.strip() not in already_processed:
      logging.info('Starting '+proj.strip())
      get_maven_dependencies_from_zip(proj.strip(), process_num, logging, jar_folder, extract_folder)

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

def start_child(processes, global_queue, proj_paths, batch, working_dir, jar_folder, already_processed):
  # This is a blocking get. If the queue is empty, it waits
  pid = global_queue.get()
  # OK, one of the processes finished. Let's get its data and kill it
  kill_child(processes, pid)

  # Get a new batch of project paths ready
  paths_batch = proj_paths[:batch]
  del proj_paths[:batch]

  print "Starting new process %s" % (pid)
  p = Process(name='Process '+str(pid), target=process_projects, args=(pid, paths_batch, global_queue, working_dir, jar_folder, already_processed, ))
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

def read_processed_from_LOGS(list_LOG_dirs):
  already_processed = set()

  for log_dir in list_LOG_dirs:
    paths = set()

    for file in os.listdir(log_dir):
      if file.endswith(".log"):
        paths.add(os.path.join(log_dir, file))

    if len(paths) > 0:
      for l in paths:
        with open(l,'r') as log:
          for line in log:
            if 'Starting' in line:
              line_split = (line.strip()).split(' ')
              already_processed.add(line_split[-1:][0])

  #for l in already_processed:
  #  print l

  return already_processed

def get_existing_jars(jars_folder):
  existing_jars = set()

  for subdir, dirs, files in os.walk(jars_folder):
    for file in files:
      ext = os.path.splitext(file)[-1].lower()
      if ext == '.jar':
        existing_jars.add(file)

  return existing_jars

def copy_and_organize_jars(from_folder,to_folder,existing_jars):
  return

def yes_no():
  print """****** Maven scripts pose a SERIOUS THREAT to your system.
****** Make sure you understand the risk of running code from undisclosed sources.
****** Containment through system access permissions is HIGHLY RECOMMENDED.
****** Do you want to continue? [yes|something else]"""

  while True:
    choice = raw_input().lower()
    if choice != "yes": #  sys.exit(0)
      print 'Be safe!'
      sys.exit(0)
    else:
      return

if __name__ == "__main__":

  parser = OptionParser()
  parser.add_option("-j", "--getMavenJars", dest="getMavenJars", type="string", default=False,
                    help="Get Jar files by running 'mvn dependency:copy-dependencies' for each project where it applies. Argument is a list of project paths. Includes automatic detection of Maven information.")

  parser.add_option("-w", "--workingDirectory", dest="workingDir", type="string", default=False,
                    help="[OPTIONAL] Set a directory where JAR files and LOGS will be saved to. Default is './dependenciesEnv/'.")

  parser.add_option("-l", "--logs", dest="logsDirs", type="string", default=False,
                    help="[OPTIONAL] Comma-separated list of directories to look for log files of previous runs. The script will read the logs and resume execution.")

  parser.add_option("-t", "--threads", dest="threadsCount", type="int", default=False,
                    help="[OPTIONAL] Number of processes. Multiprocessing calls by maven is OUTSIDE the scope of this parameter so be advised. Default is 2.")

  parser.add_option("-c", "--copyJars", dest="copyJars", type="string", default=False,
                    help="Copies and organizes JAR files from this location to a local 'organized_jars' folder. If optional argument '-e' is passed, JAR files that already exist in '-e' directory will not be copied.")

  parser.add_option("-e", "--existingJars", dest="existingJars", type="string", default=False,
                    help="[OPTIONAL] JAR files in this directory will not be copied by '-j'.")

  (options, args) = parser.parse_args()

  if not len(sys.argv) > 1:
    print "No arguments were passed. Try running with '--help'."
    sys.exit(0)

  if options.copyJars and options.getMavenJars:
    print "Arguments '-c' and '-j' are not compatible. Try running with '--help'."
    sys.exit(0)

  #### ARGUMENTS HANDLING MUST BE below
 
  ## existingJars
  existing_jars = set()
  if options.existingJars:
    print 'Searching for existing JAR files in:',options.existingJars
    existing_jars = get_existing_jars(options.existingJars)

  ## copyJars
  if options.copyJars:
    local_folder = os.path.join(os.getcwd(),'organized_jars')
    if os.path.isdir(local_folder):
      print 'Folder',local_folder,'already exists.'
    else:
      p_start = dt.datetime.now()
      os.makedirs(local_folder)
      copy_and_organize_jars(options.copyJars,local_folder,existing_jars)
      print "*** All JAR files copied in %s" % (dt.datetime.now() - p_start)
      sys.exit(0)

  ## getMavenJars
  working_dir = ''
  if options.workingDir:
    print 'Working directory:',options.workingDir
    working_dir = os.path.abspath(options.workingDir)
  else:
    working_dir = os.path.join(os.getcwd(),'dependenciesEnv')
  if not os.path.isdir(working_dir):
    os.makedirs(working_dir)

  ## logsDirs
  already_processed = []
  if options.logsDirs:
    print 'Searching for existing logs in:',options.logsDirs.split(',')
    already_processed = read_processed_from_LOGS(options.logsDirs.split(','))

  ## threadsCount
  if options.threadsCount:
    print 'Number of threads:',options.threadsCount
    N_PROCESSES = options.threadsCount

  ## getMavenJars
  if options.getMavenJars:
    p_start = dt.datetime.now()
    print 'Getting Maven JARs from:',options.getMavenJars

    yes_no()

    ## jar_folder is shared for all the processes, and is where all jars are downloaded to
    jar_folder = os.path.join(working_dir,JAR_FOLDER)
    print jar_folder
    if not os.path.isdir(jar_folder):
      os.makedirs(jar_folder)

    proj_paths = []
    with open(options.getMavenJars,'r') as f:
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
    #print "*** Starting projects..."
    while len(proj_paths) > 0:
      start_child(processes, global_queue, proj_paths, PROJECTS_BATCH, working_dir, jar_folder, already_processed)

    print "*** No more projects to process. Waiting for children to finish..."
    while active_process_count(processes) > 0:
      pid = global_queue.get()
      kill_child(processes, pid)

    p_elapsed = dt.datetime.now() - p_start
    print "*** All done. %s projects in %s" % (n_projects, p_elapsed)
    sys.exit(0)

