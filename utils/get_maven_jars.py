import sys, os
import xml.etree.ElementTree as ET
import zipfile
from subprocess import check_output

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
      sys.exit(0)

    with open(os.path.join(working_dir,'pom.xml'),'w') as file:
      file.write(z.read(pom_file))

  output = check_output(["mvn", "-f", working_dir, "dependency:copy-dependencies"])
  print output

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

  inputt = sys.argv[1]

  working_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'dependenciesEnv')

  # This code will need to be in the beginning of each subprocess
  if not os.path.isdir(working_dir):
    os.makedirs(working_dir)
  else:
    if os.path.isfile(os.path.join(working_dir,'pom.xml')):
      os.remove(os.path.join(working_dir,'pom.xml'))

  get_maven_dependencies_from_zip(inputt,working_dir)
  
  #print 'Reading pom:',pom_file
  #get_dependencies(pom_file)

