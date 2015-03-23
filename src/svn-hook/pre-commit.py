#!/usr/bin/env python 
"""Subversion pre-commit hook script that runs PMD static code analysis.

Functionality:
Runs PMD checks on java source code.
Commit will be rejected if PMD rules are voilated.
If there are more than 40 files committed at once - commit will be rejected.
Don't kill SVN server - commit in smaller chunks. 
To avoid PMD checks - put NOPMD into SVN log.
The script expects a pmd-check.conf file placed in the conf dir under
the repo the commit is for."""
 
import sys
import os
import subprocess
import fnmatch
import tempfile
 
# Deal with the rename of ConfigParser to configparser in Python3
try:
    # Python >= 3.0
    import configparser
except ImportError:
    # Python < 3.0
    import ConfigParser as configparser
 
class Commands:
    """Class to handle logic of running commands"""
    def __init__(self, config):
        self.config = config
 
    def svnlook_changed(self, repo, txn):
        """Provide list of files changed in txn of repo"""
        svnlook = self.config.get('DEFAULT', 'svnlook')
        cmd = "%s changed -t %s %s" % (svnlook, txn, repo)
        # sys.stderr.write("Command:: %s\n" % cmd)
        p = subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
 
        lines = (line.strip() for line in p.stdout)
        # Only if the contents of the file changed (by addition or update)
        # directories always end in / in the svnlook changed output
        changed = [line[4:] for line in lines if line[-1] != "/"
            and line[0] in ("A","U") ]

        # wait on the command to finish so we can get the
        # returncode/stderr output
        data = p.communicate()
        if p.returncode != 0:
            sys.stderr.write(data[1].decode())
            sys.exit(2)
 
        return changed
 
    def svnlook_getlog(self, repo, txn):
        """ Gets content of svn log"""
        svnlook = self.config.get('DEFAULT', 'svnlook')
 
        cmd = "%s log -t %s %s" % (svnlook, txn, repo)
 
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
        data = p.communicate()
 
        return (p.returncode, data[0].decode())
 
   
    def svnlook_getfile(self, repo, txn, fn, tmp):
        """ Gets content of svn file"""
        svnlook = self.config.get('DEFAULT', 'svnlook')
 
        cmd = "%s cat -t %s %s %s > %s" % (svnlook, txn, repo, fn, tmp)
 
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
        data = p.communicate()
 
        return (p.returncode, data[1].decode())
 
    def pmd_command(self, repo, txn, fn, tmp):
        """ Run the PMD scan over created temporary java file"""
        pmd = self.config.get('DEFAULT', 'pmd')
        pmd_rules = self.config.get('DEFAULT', 'pmd_rules')
 
        cmd = "%s -f text -R %s -d %s" % (pmd, pmd_rules, tmp)
 
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
        data = p.communicate()
 
        # pmd is not working on error codes ..
        return (p.returncode, data[0].decode())
 
 
def main(repo, txn):
    exitcode = 0
    config = configparser.SafeConfigParser()
    config.read(os.path.join(repo, 'conf', 'pmd-check.conf'))
    commands = Commands(config)
 
    # check if someone put magic string to not process code with PMD
    (returncode, log) = commands.svnlook_getlog(repo, txn)
    if returncode != 0:
        sys.stderr.write(
            "\nError retrieving log from svn " \
            "(exit code %d):\n" % (returncode))
        sys.exit(returncode);
       
    if "NOPMD" in log:
        sys.stderr.write("No PMD check - mail should be sent instead.")
        sys.exit(0)
       
    # get list of changed files during this commit
    changed = commands.svnlook_changed(repo, txn)
 
    # this happens when you adding new project to repo
    if len(changed) == 0:
        sys.stderr.write("No files changed in SVN!!!\n")
        sys.exit(0)
 
    # we don't want to kill svn server or wait hours for commit
    if len(fnmatch.filter(changed, "*.java")) >= 40:
                sys.stderr.write(
            "Too many files to process, try commiting " \
            " less than 40 java files per session \n" \
            " Or put 'NOPMD' in comment, if you need " \
            " to work with bigger chunks!\n")
                sys.exit(1)
 
    # create temporary file
    f = tempfile.NamedTemporaryFile(suffix='.java',prefix='x',delete=False)
    f.close()
 
    # only java files
    for fn in fnmatch.filter(changed, "*.java"):
        (returncode, err_mesg) = commands.svnlook_getfile(
            repo, txn, fn, f.name)
        if returncode != 0:
            sys.stderr.write(
                "\nError retrieving file '%s' from svn " \
                "(exit code %d):\n" % (fn, returncode))
            sys.stderr.write(err_mesg)
           
        (returncode, err_mesg) = commands.pmd_command(
            repo, txn, fn, f.name)
        if returncode != 0:
            sys.stderr.write(
                "\nError validating file '%s'" \
                "(exit code %d):\n" % (fn, returncode))
            sys.stderr.write(err_mesg)
            exitcode = 1
        if len(err_mesg) != 0:
            sys.stderr.write(
                "\nPMD violations in file '%s' \n" % fn)
            sys.stderr.write(err_mesg)
            exitcode = 1
           
    os.remove(f.name)
    return exitcode
 
if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stderr.write("invalid args\n")
        sys.exit(1)
 
    try:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    except configparser.Error as e:
       sys.stderr.write("Error with the pmd-check.conf: %s\n" % e)
    sys.exit(1)

