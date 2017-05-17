import sys, os
import xml.etree.ElementTree as ET
import zipfile
from subprocess import check_output
import logging

# This function grabs a zip, searches for a pom.xml file, if it exists
# downloads all the dependencies using maven to a ./target/dependencies
def get_maven_dependencies_from_zip(zip_path, working_dir = os.path.dirname(os.path.abspath(__file__))):

  pom_file = None

  with zipfile.ZipFile(zip_path) as z:
    for line in z.namelist():
      line_strip = line.strip()
      if line_strip.endswith("pom.xml"):
        pom_file = line_strip
        break

    if pom_file is None:
      logging.info('No pom.xml file on '+zip_path)
      sys.exit(0)

    logging.info('pom.xml found for '+zip_path)

    with open(os.path.join(working_dir,'pom.xml'),'w') as file:
      file.write(z.read(pom_file))

  output = check_output(["mvn", "-f", working_dir, "dependency:copy-dependencies"])

  new_jars = 0
  jar_already_existed = 0


  for line in output.split('\n'):
    if 'already exists in destination.' in line:
      jar_already_existed += 1
    else:
      if '[INFO] Copying' in line:
        new_jars += 1

  logging.info(zip_path+' has ended with '+str(new_jars)+' new JARs and '+str(jar_already_existed)+' existing ones')
    

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

if __name__ == "__main__":
  working_dir = os.path.join(os.getcwd(),'dependenciesEnv')
  print 'Working dir',working_dir

  # This code will need to be in the beginning of each subprocess
  if not os.path.isdir(working_dir):
    os.makedirs(working_dir)
  if os.path.isfile(os.path.join(working_dir,'pom.xml')):
    os.remove(os.path.join(working_dir,'pom.xml'))
  if os.path.isfile(os.path.join(working_dir,'LOG.log')):
    print 'ERROR file',os.path.join(working_dir,'LOG.log'),'already exists'
    sys.exit(1)

  # Logging code
  FORMAT = '[%(levelname)s] (%(threadName)s) %(message)s'
  logging.basicConfig(level=logging.DEBUG,format=FORMAT)
  file_handler = logging.FileHandler(os.path.join(working_dir,'LOG.log'))
  file_handler.setFormatter(logging.Formatter(FORMAT))
  logging.getLogger().addHandler(file_handler)

  inputt = sys.argv[1]


  with open(inputt,'r') as projects_path:
    for path in projects_path:
      logging.info('Reading '+path.strip())

      get_maven_dependencies_from_zip(path.strip(),working_dir)

    #print 'Reading pom:',pom_file
    #get_dependencies(pom_file)
