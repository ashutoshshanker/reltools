import os
import json
from flexObject import FlexObject
from flexConfigObject import FlexConfigObject
from flexStateObject import FlexStateObject

class apiGenie (object) :
    def __init__ (self, outputDir, objDescriptors, attrDescriptionsDir) :
        self.outputDir = outputDir
        self.objDescriptors = objDescriptors
        self.attrBase = attrDescriptionsDir
        self.objDict = {}
        self.buildObjects() 

    def buildObjects (self) :
        for desc  in self.objDescriptors:
            with open(desc) as fileHdl:
                objMembersData = json.load(fileHdl)                                                                        
                for objName, objInfo in objMembersData.iteritems():
                    #if objName != 'BGPNeighbor':
                    #    continue
                    if 'w' in str(objInfo['access']):
                        self.objDict[objName] = FlexConfigObject (objName, 
                                                                  objInfo['access'],
                                                                  objInfo['multiplicity'],
                                                                  self.attrBase + objName + "Members.json"
                                                                  )
                    elif 'r' in str(objInfo['access']):
                        self.objDict[objName] = FlexStateObject  (objName,
                                                                  objInfo['access'],
                                                                  objInfo['multiplicity'],
                                                                  self.attrBase + objName + "Members.json"
                                                                  )

    def writeApiCode(self) :
        filePath = ''
        basePath= os.getenv('SR_CODE_BASE')
        if basePath!= None:
            filePath = basePath + '/reltools/codegentools/apigen/'
        outputFile = self.outputDir + 'flexswitchV2.py'
        with open(outputFile, 'w+') as fileHdl:
            with open(filePath + 'baseCode.txt', 'r') as base:
                fileHdl.writelines(base.readlines())
            for objName, obj in self.objDict.iteritems():
                obj.writeAllMethods(fileHdl)
        

if __name__ == '__main__':
    baseDir = os.getenv('SR_CODE_BASE',None)
    if not baseDir:
        print 'Environment variable SR_CODE_BASE is not set'
    
    objDescriptors = [ baseDir + '/snaproute/src/models/' + 'genObjectConfig.json', ]
    attrDescriptorsLocation = baseDir+'/reltools/codegentools/._genInfo/'
    outputDir = baseDir+'/snaproute/src/flexSdk/py/'
    gen = apiGenie( outputDir, objDescriptors, attrDescriptorsLocation)
    gen.writeApiCode()
