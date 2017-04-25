import re

errorre = re.compile("\[javac\]\s+(.*?):\d+:\s+error:\s+(.*)")

rclasspublic = re.compile("class .*? is public, should be declared in a file named.*")
rpackage = re.compile("package\s+(.*?)\s+does not exist")
runmappable = re.compile("unmappable character for encoding\s+(.*)")

def errortype(item):
  if rpackage.match(item):
    return {
        "error_type": "package not found",
        "package": rpackage.match(item).groups()[0]
    }
  elif rclasspublic.match(item):
    return { "error_type": "class should be in its own file." }
  elif runmappable.match(item):
    return {
        "error_type": "unmappable character",
        "encoding": runmappable.match(item).groups()[0]
    }
  elif "wrong number of type arguments" in item:
    return { "error_type": "wrong number of type arguments" }
  elif "cannot be accessed from outside package" in item:
    return { "error_type": "cannot be accessed from outside package" }
  elif "is never thrown in body" in item:
    return { "error_type": "exception is never thrown in body" }
  elif "cannot be inherited with different arguments" in item:
    return { "error_type": "class cannot be inherited with different arguments" }
  elif "is not within bounds of" in item:
    return { "error_type": "not within bounds" }
  elif "non-static" in item and "static context" in item:
    return { "error_type": "non-static used in static context" }
  elif "inherits unrelated defaults for" in item:
    return { "error_type": "inherits unrelated defaults" }
  elif "might not have been initialized" in item:
    return { "error_type": "not initialized" }
  elif "is already defined in" in item:
    return { "error_type": "redeclaration" }
  elif "illegal" in item:
    return { "error_type": "illegal use" }
  elif "cannot be accessed from outside the package" in item:
    return { "error_type": "private class cannot be accessed outside package" }
  elif "no suitable" in item and "found for" in item:
    return { "error_type": "no suitable definition found" }
  elif "not allowed here" in item:
    return { "error_type": "modifier not allowed" }
  elif "required, but" in item and "found" in item:
    return { "error_type": "mismatched types" }
  elif "unreported exception" in item:
    return { "error_type": "unreported exception" }
  elif "has private access" in item:
    return { "error_type": "private access error" }
  elif "cannot access" in item:
    return { "error_type": "illegal access" }
  elif "does not take parameters" in item:
    return { "error_type": "too many parameters" }
  elif "has protected access" in item:
    return { "error_type": "protected access error" }
  elif "expected" in item:
    return { "error_type": "expected symbol not found" }
  elif "cannot be applied" in item:
    return { "error_type": "cannot be applied" }
  elif "cannot override" in item:
    return { "error_type": "override error" }
  elif "cannot implement" in item:
    return { "error_type": "cannot implement error" }
  elif "reference to" in item and "is ambiguous" in item:
    return { "error_type": "ambiguious reference" }
  elif "is abstract" in item or "is not abstract" in item or "abstract method" in item:
    return { "error_type": "abstraction error" }
  elif "UTF8 representation for string" in item:
    return { "error_type": "UTF representation error" }
  elif "duplicate class" in item:
    return {
        "error_type": "duplicate class",
        "class": item.split(":")[1].strip()
    }
  elif "duplicate element" in item:
    return { "error_type": "duplicate element" }
  elif "clashes with" in item:
    return { "error_type": "domain/signature clash" }
  elif "has already been annotated" in item:
    return { "error_type": "package has already been annotated" }
  elif "cannot inherit from final" in item:
    return { "error_type": "cannot inherit from final class" }
  elif "defined in an inaccessible" in item:
    return { "error_type": "defined in an inaccessible class or interface" }
  elif "bad operand type" in item:
    return { "error_type": "bad operand type" }
  elif "import requires canonical name for" in item:
    return { "error_type": "import requires canonical name" }
  elif "inherited with the same signature" in item:
    return { "error_type": "inherited with the same signature" }
  elif "cannot directly extend" in item:
    return { "error_type": "cannot directly extend class" }
  elif "cyclic inheritance" in item:
    return { "error_type": "cyclic inheritance error" }
  elif "is missing" in item and "default value" in item:
    return { "error_type": "annotation is missing a default value" }
  elif "Illegal static declaration" in item:
    return { "error_type": "illegal static declaration" }
  elif "cannot assign a value to final variable" in item:
    return { "error_type": "cannot assign to final variable" }
  elif "an enclosing instance that contains" in item:
    return { "error_type": "instance of enclosing class type is required" }
  elif "not initialized in the default constructor" in item:
    return { "error_type": "member not initialized in the default constructor" }
  elif "exception" in item and "has already been caught" in item:
    return { "error_type": "exception has already been caught" }
  elif "a generic class may not extend" in item:
    return { "error_type": "a generic class cannot extend a specific class" }
  elif "cannot infer type arguments" in item:
    return { "error_type": "cannot infer type arguments" }
  elif ":" in item:
    return {
        "error_type": item.split(":")[0].strip()
    }
  else:
    return { "error_type": item }

def Categorize(output):
  filtered_errors = [{
            "filename": errorre.match(dline.strip()).groups()[0],
            "error": errorre.match(dline.strip()).groups()[1]
        } for dline in output.split("\n")
        if errorre.match(dline.strip())
  ] if "impossible to resolve dependencies" not in output else [{
            "filename": "ivy.xml",
            "error": "unresolved dependencies"
  }]
  for i in range(len(filtered_errors)):
    filtered_errors[i].update(errortype(filtered_errors[i]["error"]))
  return filtered_errors

