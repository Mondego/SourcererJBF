# SourcererJBF:  A Java Build Framework For Large Scale Compilation

SourcererJBF or JBF is a build framework that is capable of building thousand of Java projects at scale.
JBF first takes a vast collection of Java projects as input and scrapes all the required external dependencies from
those projects or the web. Then it indexes these dependencies and compiles the projects in multiple stages. During the
compilation, JBF
fixes errors and resolves external dependencies.

<img src="doc/jbf-overview.png" alt="JBF High Level Architecture"/>

### Environment Setup & Requirements

- Java Version: JDK-8+ [Preferable Latest Java [OpenJDK17](https://openjdk.java.net/projects/jdk/17/)]
- Ant Version: any that uses ``javac`` from JDK-8+ [Ant](https://ant.apache.org/manual/install.html)
- Python Version: 3.9+
- JBF uses three python packages [subprocess32](), [chardet]() and [simplejson](). The following python packages are
  required to install before running JBF:

```
pip install subprocess32
pip install chardet
pip install simplejson
```

### SourcererJBF Directories and Files Structure

```
📦 SourcererJBF
 ┣ 📂 sourcererjbf           // The python package with scripts for building the projects.
 ┃ 📂 utils                 // The utlity package with scripts for analyzing Jars and projects.
 ┃ 📂 xml-templates        // The templates for creating normalized build scripts.
 ┃ 📂 doc                 // Resource for project documentation.           
 📜 jbf.config.txt       // Contains the configuration of JBF execution.
 📜 jbf-compile.py      // Main Entry point of JBF execution
 📜 clean-up.sh        // Script for cleaning all generated files & folders
 📜 README.md         // JBF documentation.
```

### Run JBF
JBF can be run in two-way. The easiest option is to edit the config file and run the simple command.
First edit the configuration file ``jbf.config`` with the required values and paths.
The file is self-explanatory and just need to updated according to host machine physical paths.

- #### Edit ``jbf.config``

``` yml
[DEFAULT]
# The directory under which all the java projects to be compiled exist.
root = /Users/username/projects
# Rebuild the projects from scratch. Dependency rematching implies 
# that all projects might not recompile successfully.
rebuild_from_scratch = True
# The file with project paths to be build. Paths in file are considered relative to the root directory.
file = AUTOGEN
# The directory under which all the output build directories will be put.
outfolder = /Users/username/builds/
# An output file that will contain all the output information consolidated.
output = /Users/username/builds/project_details.json
# The root of the java repository
jars =/Users/username/jars
# The file that represents the mapping of fqn to jar in repository.
fqn_to_jar = /Users/username/builds/fqn-to-jars.shelve
# The number of base threads to be run.
threads = 1
try_project_build = False
verbose = True
only_project_build = False
```

```bash 
python3 jbf-config-compile.py
```
- #### Using CMD
If you prefer to run JBF with command line arguments the use the following command and pass the required arguments as
shown in the following.

```bash
python3 jbf-cmd-compile.py [-h] [-r ROOT] [-b] [-f FILE] [-d OUTFOLDER] [-o OUTPUT]
[-j JARS] [-ftj FQN_TO_JAR] [-t THREADS]

```
#### jbf-cmd-compile.py help
```yml
python3 jbf-cmd-compile.py [-h] [-r ROOT] [-b] [-f FILE] [-d OUTFOLDER] [-o OUTPUT]
[-j JARS] [-ftj FQN_TO_JAR] [-t THREADS]

optional arguments:
-h, --help                    Show this help message and exit
-r ROOT, --root ROOT          The directory under which all the java projects to be compiled exist.
-b, --rebuild_from_scratch    Rebuild the projects from scratch. Dependency rematching implies that all projects might not recompile successfully.
-f FILE, --file FILE          The file with project paths to be build. Paths in file are considered relative to the root directory.
-d OUTFOLDER, --outfolder     OUTFOLDER The directory under which all the output build directories will be put.
-o OUTPUT, --output OUTPUT    An output file that will contain all the output information consolidated.
-j JARS, --jars JARS          The root of the java repository
-ftj FQN_TO_JAR, --fqn_to_jar FQN_TO_JAR The file that represents the mapping of fqn to jar in repository.
-t THREADS, --threads THREADS The number of base threads to be run.
```

### Configured and Generated Directories, Files Structure

```
 ┣ 📂 projects                     // All the projects that can be build. There are at most 1000 projects in each folder in projects
 ┣ 📂 builds                      // The output of the build process. Generated following the same heirarchy that is similar to ┣📂 projects/
 ┣ 📂 TBUILD                     // The python package with scripts for building the projects.
 ┃ 📂 Uncompress                // Temporary folder used to unzip the project files from their zip archives.
 📜 project_details.json       // Bookkeeping details for the projects that instruct the compilation script on how to build them.
 📜 fqn-to-jars.shelve        // The global mapping of FQNs to jars, from our huge repository.
 📜 *.log                    // Log files generated by worker threads in case of failures.
 📜 save_*.shelve           // JBF documentation.
```

#### Note:

Please delete all these generated files & folders before each new run of compile.py.

```bash
./clean-up.sh
```
