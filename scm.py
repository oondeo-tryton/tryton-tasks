#!/usr/bin/env python

from invoke import task, run
import hgapi
from multiprocessing import Process
from .utils import t, read_config_file
import os
import sys
from blessings import Terminal

MAX_PROCESSES = 20


def wait_processes(processes, maximum=MAX_PROCESSES):
    i = 0
    while len(processes) > MAX_PROCESSES:
        if i >= len(processes):
            i = 0
        p = processes[i]
        p.join(0.1)
        if not p.is_alive():
            del processes[i]
        i += 1


def hg_clone(url, repo_path):
    command = 'hg clone -q %s %s' % (url, repo_path)
    try:
        run(command)
    except:
        print >> sys.stderr, "Error running " + t.bold(command)
        raise
    print "Repo " + t.bold(repo_path) + t.green(" Cloned")


@task()
def clone(config=None):
    # Updates config repo to get new repos in config files
    hg_pull('config', '.', True)

    Config = read_config_file(config)
    p = None
    processes = []
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        url = Config.get(section, 'url')
        path = Config.get(section, 'path')
        func = hg_clone
        if repo != 'hg':
            print >> sys.stderr, "Not developet yet"
            continue
        repo_path = os.path.join(path, section)
        if not os.path.exists(repo_path):
            print "Adding Module " + t.bold(section) + " to clone list"
            p = Process(target=func, args=(url, repo_path))
            p.start()
            processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_status(module, path, verbose):
    repo_path = os.path.join(path, module)
    if not os.path.exists(repo_path):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(repo_path)
        return
    repo = hgapi.Repo(repo_path)
    st = repo.hg_status(empty=True)
    if not st and verbose:
        print t.bold_green('\[' + module + ']')
        return
    if not st and not verbose:
        return

    msg = [t.bold_red("\n[" + module + ']')]

    if st.get('A'):
        for file_name in st['A']:
            msg.append(t.green('A ' + file_name))
    if st.get('M'):
        for file_name in st['M']:
            msg.append(t.yellow('M ' + file_name))
    if st.get('R'):
        for file_name in st['R']:
            msg.append(t.red('R ' + file_name))
    if st.get('!'):
        for file_name in st['!']:
            msg.append(t.bold_red('! ' + file_name))
    if st.get('?'):
        for file_name in st['?']:
            msg.append(t.blue('? ' + file_name))

    print "\n".join(msg)


@task
def status(config=None, verbose=False):
    Config = read_config_file(config)
    processes = []
    p = None
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_status
        if repo != 'hg':
            print >> sys.stderr, "Not developet yet"
            continue
        p = Process(target=func, args=(section, path, verbose))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_diff(module, path, verbose, rev1, rev2):
    t = Terminal()
    try:
        msg = []
        path_repo = os.path.join(path, module)
        if not os.path.exists(path_repo):
            print >> sys.stderr, (t.red("Missing repositori:")
                + t.bold(path_repo))
            return

        if not verbose:
            result = run('cd %s;hg diff --stat' % path_repo, hide='stdout')
            if result.stdout:
                msg.append(t.bold(module + "\n"))
                msg.append(result.stdout)
                print "\n".join(msg)
            return
        repo = hgapi.Repo(path_repo)
        msg = []
        for diff in repo.hg_diff(rev1, rev2):
            if diff:
                d = diff['diff'].split('\n')
                for line in d:
                    if line and line[0] == '-':
                        line = t.red + line + t.normal
                    elif line and line[0] == '+':
                        line = t.green + line + t.normal

                    if line:
                        msg.append(line)
        if msg == []:
            return
        msg.insert(0, t.bold('\n[' + module + "]\n"))
        print "\n".join(msg)
    except:
        msg.insert(0, t.bold('\n[' + module + "]\n"))
        msg.append(str(sys.exc_info()[1]))
        print >> sys.stderr, "\n".join(msg)


@task
def diff(config=None, verbose=True, rev1='default', rev2=None):
    Config = read_config_file(config)
    processes = []
    for section in Config.sections():
        path = Config.get(section, 'path')
        p = Process(target=hg_diff, args=(section, path, verbose, rev1, rev2))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_summary(module, path, verbose):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return
    repo = hgapi.Repo(path_repo)
    cmd = ['summary', '--remote']
    summary = repo.hg_command(*cmd)
    print t.bold("= " + module + " =")
    print summary


@task
def summary(config=None, verbose=False):
    Config = read_config_file(config)
    processes = []
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_summary
        if repo != 'hg':
            print >> sys.stderr, "Not developet yet"
            continue
        p = Process(target=func, args=(section, path, verbose))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_outgoing(module, path, verbose):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return
    repo = hgapi.Repo(path_repo)
    cmd = ['outgoing']
    if verbose:
        cmd.append('-v')
    try:
        out = repo.hg_command(*cmd)
    except:
        #TODO:catch correct exception
        print >> sys.stderr, "Error running " + t.bold(*cmd)
        return
    print t.bold("= " + module + " =")
    print out


@task
def outgoing(config=None, verbose=False):
    Config = read_config_file(config)
    processes = []
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_outgoing
        if repo != 'hg':
            print >> sys.stderr, "Not developet yet"
            continue
        p = Process(target=func, args=(section, path, verbose))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_pull(module, path, update):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return

    cwd = os.getcwd()
    os.chdir(path_repo)

    cmd = ['hg', 'pull']
    if update:
        cmd.append('-u')
    result = run(' '.join(cmd), warn=True, hide='both')

    if not result.ok:
        print >> sys.stderr, t.red("= " + module + " = KO!")
        print >> sys.stderr, result.stderr
        os.chdir(cwd)
        return

    if "no changes found" in result.stdout:
        os.chdir(cwd)
        return

    print t.bold("= " + module + " =")
    print result.stdout
    os.chdir(cwd)


@task
def pull(config=None, update=True):
    Config = read_config_file(config)
    processes = []
    p = None
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_pull
        if repo != 'hg':
            print >> sys.stderr, "Not developet yet"
            continue
        p = Process(target=func, args=(section, path, update))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)


def hg_update(module, path, clean):
    path_repo = os.path.join(path, module)
    if not os.path.exists(path_repo):
        print >> sys.stderr, t.red("Missing repositori:") + t.bold(path_repo)
        return

    cwd = os.getcwd()
    os.chdir(path_repo)

    cmd = ['hg', 'update']
    if clean:
        cmd.append('-C')
    result = run(' '.join(cmd), warn=True, hide='both')

    if not result.ok:
        print >> sys.stderr, t.red("= " + module + " = KO!")
        print >> sys.stderr, result.stderr
        os.chdir(cwd)
        return

    if (u"0 files updated, 0 files merged, 0 files removed, 0 "
            u"files unresolved\n") in result.stdout:
        os.chdir(cwd)
        return

    print t.bold("= " + module + " =")
    print result.stdout
    os.chdir(cwd)


@task
def update(config=None, clean=False):
    Config = read_config_file(config)
    processes = []
    p = None
    for section in Config.sections():
        repo = Config.get(section, 'repo')
        path = Config.get(section, 'path')
        func = hg_update
        if repo != 'hg':
            print >> sys.stderr, "Not developet yet"
            continue
        p = Process(target=func, args=(section, path, clean))
        p.start()
        processes.append(p)
        wait_processes(processes)
    wait_processes(processes, 0)
