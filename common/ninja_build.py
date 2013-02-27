#/usr/bin/python

import os;
import commands;
from optparse import OptionParser;

def info(msg):
    print "[INFO] " + msg + ".";

def error(msg):
    print "[ERROR] " + msg + "!";

def hasOutDir(name):
    outputDir = options.srcDir + "/out/" + buildTypeStr;
    if not os.path.exists(outputDir):
        info(outputDir + " doesn't exist. Will create the directory for you and perform a clean build");
        commands.getstatusoutput("mkdir -p " + outputDir);
        return False;

    return True;

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-t", "--build-type", dest="buildType", help="assign the build type", metavar="DEBUG|RELEASE|ALL", default="Debug");
    parser.add_option("-d", "--src-dir", dest="srcDir", help="assign src directory of Chromium", metavar="SRCDIR", default="/workspace/project/chromium/git_upstream/src");
    parser.add_option("-s", "--build-system", dest="buildSystem", help="assign build system", metavar="ninja", default="ninja");
    parser.add_option("-c", "--clean-build", action="store_true", dest="cleanBuild", help="need a clean build", default=False);
    (options, args) = parser.parse_args();

    if options.buildType.upper() == "DEBUG":
        buildTypeStr = "Debug";
    elif options.buildType.upper() == "RELEASE":
        buildTypeStr = "Release";
    elif options.buildType.upper() == "ALL":
        buildTypeStr = "All";
    else:
        error("The build type is wrong");
        exit -1;
        
    if options.buildSystem != "ninja":
        error("Currently only the build system ninja is supported");
        exit -1;    
    
    if buildTypeStr == "All":
        if not hasOutDir("Debug") and not hasOutDir("Release"):
            options.cleanBuild = True;
    else:
        if not hasOutDir(buildTypeStr):
            options.cleanBuild = True;

    
    print "== Build Environment ==";
    print "Directory of src: " + options.srcDir;
    print "Build type: " + options.buildType;
    print "Build system: " + options.buildSystem;
    print "Need clean build: " + str(options.cleanBuild);
    print "======================="

    os.chdir(options.srcDir);
    os.putenv("GYP_GENERATORS", "ninja");
    os.putenv("GYP_DEFINES", "werror= disable_nacl=1 component=shared_library enable_svg=0");
    if options.cleanBuild:
        commands.getstatusoutput("build/gyp_chromium");
    
    if buildTypeStr == "Debug" or buildTypeStr == "All":
        os.system("time " + options.buildSystem + " -C out/Debug chrome");

    if buildTypeStr == "Release" or buildTypeStr == "All":
        os.system("time " + options.buildSystem + " -C out/Release chrome");
    