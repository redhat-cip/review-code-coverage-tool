#!/usr/bin/python

import argparse
import commands
import coverage
import json
import os
import prettytable
import shutil
import sys

def get_prj_and_ref(output):
    '''
    parse and return the project name and 
    reference for the current patch set.
    '''
    json_op = json.loads(output)
    return json_op['project'], json_op['currentPatchSet']['ref']

def get_diff_files(s):
    '''
    parse and return the list of modified file names.
    '''
    lines = s.split('\n')
    my_list = []
    for l in lines:
        if l.startswith(r'diff --git'):
            l = l.split(' ')
            my_list.append(l[2][2:])
    return my_list

def get_test_files(lst):
    '''
    filter the list of test files
    from the list of modified files.
    '''
    test_files = []
    for l in lst:
        if r'/tests/' in l:
            test_files.append(l)
    return test_files

def get_modified_line_nos(fileName, diff):
    '''
    parse and return the list of modified
    line numbers for the give filename from
    the give git log message.
    '''
    lines = diff.split('\n')
    line_nos = []
    s = r'+++ b/{0}'.format(fileName)
    from_idx = lines.index(s) + 1
    to_idx = len(lines)
    n = 0
    for x in range(from_idx, to_idx):
        if lines[x].startswith(r'diff --git'):
            break
        if lines[x].startswith(r'@@'):
            n = int(lines[x].split(' ')[2].split(',')[0][1:])
            continue
        if lines[x].startswith('+'):
            line_nos.append(n)
        if not lines[x].startswith('-'):
            n = n + 1
    return line_nos

def cleanup(path):
    '''
    deletes the cloned file.
    '''
    shutil.rmtree('../' + path)

def main ():
    '''
    Gets the review id or review Url and disply
    the not executed newly added lines.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('review_id', help='review id or review url')
    parser.add_argument('--work_dir', default=r'/tmp/tmp',
                        help='defaults to /tmp/tmp')
    args = parser.parse_args()
    if not args.review_id:
        sys.exit(1)
    #if it is review_url, parse the review_id from it
    if args.review_id.startswith("https://review.openstack.org/#/c/"):
        review_id = args.review_id.replace(
        "https://review.openstack.org/#/c/", '').replace('/', '')
    else:
        review_id = args.review_id

    temp_dir = args.work_dir
    status, output = commands.getstatusoutput('mkdir -p {0}'.format(temp_dir))
    if status != 0:
        print "ERROR :: not able to create working dir.\n", output
        sys.exit(1)

    os.chdir(temp_dir)

    gerrit_query = "ssh -x -p 29418 review.openstack.org 'gerrit query \
    --format=JSON --comments --current-patch-set change: %s'" \
    % review_id
    print "Excecuting gerrit query..."
    status, output = commands.getstatusoutput(gerrit_query)
    if status != 0:
        print "ERROR :: ", output
        sys.exit(1)
    output = output.split('\n')
    prj, ref = get_prj_and_ref(output[0])
    cherry_pick_cmd = "git fetch https://review.openstack.org/{0} {1} \
    && git cherry-pick FETCH_HEAD".format(prj, ref)

    path = prj.split('/')[1]
    #clone the project from git
    git_clone_cmd = "git clone https://github.com/{0}.git".format(prj)
    print "Git cloning..."
    status, output = commands.getstatusoutput(git_clone_cmd)
    if status != 0:
        print "ERROR :: ", output
        sys.exit(1)

    os.chdir(path)

    #cherry-pick the patch
    print "cherry-picking the patch..."
    status, output = commands.getstatusoutput(cherry_pick_cmd)
    if status != 0:
        print "ERROR :: ", output
        cleanup(path)
        sys.exit(1)

    status, output = commands.getstatusoutput("git log -p -1")
    if status != 0:
        print "ERROR :: ", output
        cleanup(path)
        sys.exit(1)
    log = output

    mod_files = get_diff_files(output)
    if len(mod_files) == 0:
        print "ERROR :: No file modified"
        cleanup(path)
        sys.exit(1)

    mod_test_files = get_test_files(mod_files)

    if not os.path.isfile("run_tests.sh"):
        print "ERROR :: run_tests.sh file not found"
        cleanup(path)
        sys.exit(1)
    print "Running tests... Takes some moments, please wait..."
    status, output = commands.getstatusoutput("./run_tests.sh -V -c")
    if status != 0:
        #print "ERROR :: ", output
        #workarround for the bug #1263940
        #need to remove this workarround
        print "Running again...."
        status, output = commands.getstatusoutput("./run_tests.sh -V -c")
        if status != 0:
            print "ERROR :: ", output
            cleanup(path)
            sys.exit(1)

    c = coverage.coverage()
    c.load()
    cover_report = {}
    for f in mod_files:
        if f in mod_test_files:
            continue
        not_covered = []
        lines = get_modified_line_nos(f, log)
        t = c.analysis(f)
        for l in lines:
            if l in t[1] and l in t[2]:
                not_covered.append(l)
        cover_report[f] = not_covered
    pt = prettytable.PrettyTable(['File Name', 'Not executed lines No.'])
    for k, v in cover_report.iteritems():
        pt.add_row([k, v])
    print pt
    cleanup(path)

if __name__ == '__main__':
    main()
