## Scrips to analyse the results of JBF


`bytecode-analyzer.py` goes through the resulting `*.class` files from JBF and finds:

* The ones with a `main()`, and run them.

* The ones with `junit` tests, and runs the tests.

This script contains various variables that can be setup right in the beginning.

Resulting are `csv` files with the header: `proj_name, n_class_files, reacheable_mains, with_junit, passed_junit` 
