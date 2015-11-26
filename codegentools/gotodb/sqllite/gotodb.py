import os
import subprocess
import json
import pprint


HOME = os.getenv("HOME")
MODEL_NAME = 'genmodels'
GO_MODEL_BASE_PATH = HOME + "/git/snaproute/generated/src/%s/" % MODEL_NAME
CODE_GENERATION_PATH = HOME + "/git/reltools/codegentools/gotodb/sqllite/"

goToSqlliteTypeMap = {
  'bool':          {"native_type": "bool"},
  'uint8':            {"native_type": "INTEGER", "unsigned": True},
  'uint16':           {"native_type": "INTEGER", "unsigned": True},
  'uint32':           {"native_type": "INTEGER", "unsigned": True},
  'uint64':           {"native_type": "INTEGER", "unsigned": True},
  'string':           {"native_type": "TEXT","unsigned": None },
  'float64':          {"native_type": "REAL", "unsigned": False},
  'int8':             {"native_type": "INTEGER", "unsigned": False},
  'int16':            {"native_type": "INTEGER", "unsigned": False},
  'int32':            {"native_type": "INTEGER", "unsigned": False},
  'int64':            {"native_type": "INTEGER", "unsigned": False},
}

gDryRun =  False
def executeGoFmtCommand (fd, command, dstPath) :
    out = ''
    if type(command) != list:
        command = [ command]
    for cmd in command:
        if gDryRun :
            print cmd
        else:
            process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
            out,err = process.communicate()
            # create a go format version, at this point the fd is still
            # open so this is a .tmp file, lets strip this for the new
            # file
            print out, err
            dir = CODE_GENERATION_PATH
            fmt_name_with_dir = dir + fd.name
            print fmt_name_with_dir
            if not os.path.exists(dir):
              os.makedirs(dir)
            #nfd = open(fmt_name_with_dir, 'w+')
            #nfd.write(out)
            #nfd.close()

            #process = subprocess.Popen("ls".split(), stdout=subprocess.PIPE)
            #out,err = process.communicate()
            #print out, err

            renameCmd = "mv %s %s" %(fmt_name_with_dir, dir+fd.name)
            process = subprocess.Popen(renameCmd.split(), stdout=subprocess.PIPE)
            out,err = process.communicate()
            print out, err

            out = executeCopyCommand(dir+fd.name, dstPath)

        return out

def executeCopyCommand (name, dstPath) :
    dir = dstPath
    if not os.path.exists(dir):
      os.makedirs(dir)

    copyCmd = "cp %s %s" %(name, dstPath,)
    process = subprocess.Popen(copyCmd.split(), stdout=subprocess.PIPE)
    out,err = process.communicate()

    print out, err

    return out

def executeLocalCleanup():

    for name in os.listdir(CODE_GENERATION_PATH):
        if name.endswith(".go"):
            cmd = "rm %s" %(CODE_GENERATION_PATH+name,)
            process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
            out,err = process.communicate()
            print out, err

def scan_dir_for_go_files(dir):
    for name in os.listdir(dir):
        #print "x", dir, name
        path = os.path.join(dir, name)
        if name.endswith('.go'):
            if os.path.isfile(path) and "_enum" not in path and "_func" not in path and "_db" not in path:
                yield (dir, name)
        elif not "." in name:
            for d, f  in scan_dir_for_go_files(path):
                yield (d, f)

def build_gosqllite_from_go():
    # generate thrift code from go code
    goStructToListersDict = {}

    # lets determine from the json file the structs and associated listeners
    for dir, gofilename in scan_dir_for_go_files(GO_MODEL_BASE_PATH):
        if '_func' in gofilename and '_enum' in gofilename and '_db' in gofilename:
            continue

        dbFileName = gofilename.rstrip('.go') + "_db.go"

        dbFd = open(dbFileName, 'w')
        dbFd.write("package genmodels\n")

        dbFd.write("""import (
        	"database/sql"
                   "fmt"
                   )""")
        generate_gosqllite_funcs(dbFd, dir, gofilename)

        dbFd.close()
        executeGoFmtCommand(dbFd, ["gofmt -w %s" % dbFd.name], GO_MODEL_BASE_PATH)


def createDBTable(fd, structName, goMemberTypeDict):

    createfuncline = "\nfunc (obj %s) CreateDBTable(dbHdl *sql.DB) error {\n" % structName
    fd.write(createfuncline)
    fd.write(""" dbCmd := "CREATE TABLE IF NOT EXISTS %s \" +\n """ % structName)
    fd.write(""" \"( \" +\n""")
    keyList = []
    # loop through member and type
    for m, t in goMemberTypeDict[structName].iteritems():
        if 'Key' in m:
            keyList.append(m)
        if "LIST" in t:
            fd.write("""\" %s TEXT \" +\n""" %(m,))
        else:
            fd.write("""\" %s %s \" +\n""" %(m, t))

    fd.write(""" \"PRIMARY KEY(""")
    for i, k in enumerate(keyList):
        if i == len(keyList) - 1:
            fd.write("""%s)""" % k)
        else:
            fd.write("""%s, """ % k)
    fd.write(""" ) \"\n""")

    fd.write("""txn, err := dbHdl.Begin()
	    if err != nil {
		    fmt.Println("### Failed to strart a transaction")
	    }
	    fmt.Println("**** Executing DB command ", dbCmd)
	    _, err = dbHdl.Exec(dbCmd)
	    if err != nil {
		    fmt.Println("**** Failed to Create table", err)
	    }

	    err = txn.Commit()
	    if err != nil {
		    fmt.Println("### Failed to Commit transaction")
	    }
	    return nil
    }""")

def createStoreObjInDb(fd, structName, goMemberTypeDict):
    storefuncline = "\nfunc (obj %s) StoreObjectInDb(dbHdl *sql.DB) (int64, error) {\n" % structName
    fd.write(storefuncline)
    fd.write("""var objectId int64\n""")
    fd.write("""insertsql := fmt.Sprintf(\"INSERT INTO %s (""" % structName)
    # loop through member and type
    for i, (m, t) in enumerate(goMemberTypeDict[structName].iteritems()):
        if i == len(goMemberTypeDict[structName]) - 1:
            fd.write("""%s) VALUES (""" % m)
        else:
            fd.write("""%s, """ % m )
    for i, (m, t) in enumerate(goMemberTypeDict[structName].iteritems()):
        if i == len(goMemberTypeDict[structName]) - 1:
            fd.write("""%v);\",\n""")
        else:
            fd.write("""%v, """ )

    for i, (m, t) in enumerate(goMemberTypeDict[structName].iteritems()):
        if i == len(goMemberTypeDict[structName]) - 1:
            fd.write("""obj.%s)\n""" % m )
        else:
            fd.write("""obj.%s, """ % m )

    fd.write("""fmt.Println("**** Create Object called with ", obj)

	txn, err := dbHdl.Begin()
	if err != nil {
		fmt.Println("### Failed to strart a transaction")
	}
	fmt.Println("**** Executing DB command ", insertsql)
	result, err1 := dbHdl.Exec(insertsql)
	if err1 != nil {
		fmt.Println("**** Failed to Create table", err)
	}

	err = txn.Commit()
	if err != nil {
		fmt.Println("### Failed to Commit transaction")
	}
	objectId, err = result.LastInsertId()
	if err != nil {
		fmt.Println("### Failed to return last object id", err)
	} else {
		fmt.Println("### Object ID return ", objectId)
	}

	return objectId, nil
}\n""")

def generate_gosqllite_funcs(fd, dir, gofilename):
    goMemberTypeDict = {}

    path = os.path.join(dir, gofilename)
    gofd = open(path, 'r')
    deletingComment = False
    foundStruct = False
    currentStruct = None
    for line in gofd.readlines():
        if not deletingComment:
            if "struct" in line:
                lineSplit = line.split(" ")
                currentStruct = lineSplit[1]
                goMemberTypeDict[currentStruct] = {}
                foundStruct = True

            elif "}" in line and foundStruct:
                foundStruct = False
                # create the various functions for db
                createDBTable(fd, currentStruct, goMemberTypeDict)
                createStoreObjInDb(fd, currentStruct, goMemberTypeDict)

            # lets skip all blank lines
            # skip comments
            elif line == '\n' or \
                "//" in line or \
                "#" in line or \
                "package" in line:
                continue
            elif "/*" in line:
                deletingComment = True
            elif foundStruct:  # found element in struct
                # print "found element line", line
                lineSplit = line.split(' ')
                # print lineSplit
                elemtype = lineSplit[-3].rstrip('\n') if 'KEY' in lineSplit[-1] else lineSplit[-1].rstrip('\n')

                #print "elemtype:", lineSplit, elemtype
                if elemtype.startswith("[]"):
                    elemtype = elemtype.lstrip("[]")
                    # lets make all list an unordered list
                    nativetype = "LIST " + goToSqlliteTypeMap[elemtype]["native_type"]
                    goMemberTypeDict[currentStruct].update({lineSplit[0].lstrip(' ').rstrip(' ').lstrip('\t'):
                                                            nativetype})
                else:
                    if elemtype in goToSqlliteTypeMap.keys():
                        goMemberTypeDict[currentStruct].update({lineSplit[0].lstrip(' ').rstrip(' ').lstrip('\t'):
                                                                    goToSqlliteTypeMap[elemtype]["native_type"]})

        else:
            if "*/" in line:
                deletingComment = False


if __name__ == "__main__":

    build_gosqllite_from_go()
    #executeLocalCleanup()