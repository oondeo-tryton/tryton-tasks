import os
import ConfigParser
from invoke import Collection, task, run
from .utils import read_config_file, get_config_files
from .scm import get_repo
from collections import OrderedDict
from bucket.repository import list_repos

def get_config():
    """ Get config file for tasks module """
    parser = ConfigParser.ConfigParser()
    config_path = '%s/.tryton-tasks.cfg' % os.getenv('HOME')
    parser.read(config_path)
    settings = {}
    for section in parser.sections():
        usection = unicode(section, 'utf-8')
        settings[usection] = {}
        for name, value, in parser.items(section):
            settings[usection][name] = value
    return settings


@task()
def set_revision(config=None):
    """ Set branch on repository config files """

    if config is None:
        config_files = get_config_files()
    else:
        config_files = [config]

    for config_file in config_files:
        Config = read_config_file(config_file, type='all', unstable=True)
        f_d = open(config_file, 'w+')
        for section in Config.sections():
            if Config.has_option(section, 'patch'):
                continue
            repo = get_repo(section, Config, 'revision')
            revision = repo['function'](section, repo['path'], verbose=False)
            Config.set(section, 'revision', revision)

        Config.write(f_d)
        f_d.close()


@task()
def set_branch(branch, config=None):
    """ Set branch on repository config files """

    if config is None:
        config_files = get_config_files()
    else:
        config_files = [config]

    for config_file in config_files:
        Config = read_config_file(config_file, type='all', unstable=True)
        f_d = open(config_file, 'w+')
        for section in Config.sections():
            if Config.has_option(section, 'patch'):
                continue
            Config.set(section, 'branch', branch)

        Config.write(f_d)
        f_d.close()


@task()
def add_module(config, path, url=None):
    """ Add module to specified config file """
    Config = read_config_file(config, type='all', unstable=True)
    module = os.path.basename(path)
    url = run('cd %s; hg paths default' % (path)).stdout.split('\n')[0]
    if 'http' in url:
        url = 'ssh://hg@bitbucket.org/nantic/trytond-%s' % module
    branch = run('cd %s;hg branch' % (path)).stdout.split('\n')[0]
    cfile = open(config, 'w+')
    if not Config.has_section(module):
        Config.add_section(module)
        Config.set(module, 'branch', branch)
        Config.set(module, 'repo', 'hg')
        Config.set(module, 'url', url)
        Config.set(module, 'path', './trytond/trytond/modules')

    Config._sections = OrderedDict(sorted(Config._sections.iteritems(),
        key=lambda x: x[0]))
    Config.write(cfile)
    cfile.close()


def config_update_walk(scmtype="bucket",unstable=False):
    for r, _ , f in os.walk("./config/"+scmtype):
        for files in f:
            project = None
            is_unstable = None
            if not files.endswith(".cfg"):
                continue
            if not unstable and files.endswith("-unstable.cfg"):
                continue
            if files.endswith("-unstable.cfg"):
                files = files.replace("-unstable","")
                is_unstable = True
            if 'templates' in r:
                continue
            d = os.path.basename(r)
            if d != "bucket":
                if d.startswith("project_"):
                    project = d.replace("project_","")
            user = os.path.splitext(files)[0]
            path = os.path.join(r, files)
            if os.path.isfile(path):
                # Check if file exists because it may be a symlink to
                # ../local.cfg and it might not exist.
                Config = ConfigParser.ConfigParser()
                f=open(path,"r+")
                Config.readfp(f)
                for repo in list_repos(user,project):
                    if type(repo) is int:
                        continue
                    try:
                        print repo
                        name = repo["name"]
                        if not Config.has_section(name):
                            Config.add_section(name)
                        if name.startswith("trytond-"):
                            Config.set(name,"path","./trytond/trytond/modules")
                        else: 
                            continue
                            Config.set(name,"path","./")                    
                        if is_unstable:
                            Config.set(name,"unstable",True)
                        Config.set(name,"repo",repo["scm"])
                        Config.set(name,"url",repo["links"]["clone"][0]["href"])
                        Config.set(name,"branch",repo["mainbranch"]["name"])
                        for key,value in repo.iteritems():
                            if type(value) is str:
                                Config.set(files,key,value)   
                    except Exception as e:
                        print e 
                        if Config.has_section(name):   
                            Config.remove_section(name)
                Config.write(f)
                f.close()
  
@task()
def update(unstable=False):
    # Config = ConfigParser.ConfigParser() #Config.readfp(open(path))
    config_update_walk(scmtype='bucket',unstable=unstable)
    #for scm in scm_user_list:

    # for section in Config.sections():
    #     is_patch = (Config.has_option(section, 'patch')
    #             and Config.getboolean(section, 'patch'))
    #     if type == 'repos' and is_patch:
    #         Config.remove_section(section)
    #     elif type == 'patches' and not is_patch:
    #         Config.remove_section(section) 

ConfigCollection = Collection()
ConfigCollection.add_task(add_module)
ConfigCollection.add_task(set_branch)
ConfigCollection.add_task(set_revision)
ConfigCollection.add_task(update)