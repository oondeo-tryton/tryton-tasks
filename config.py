import os
import ConfigParser
from invoke import Collection, task, run
from .utils import read_config_file, get_config_files
from .scm import get_repo
from collections import OrderedDict
from bucket.repository import list_repos
from datetime import datetime
import codecs,re

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

def encode(s):
    if type(s) is unicode:
        return s.encode('ascii','ignore')
    else:
        return s

def config_update_walk(scmtype="bucket",unstable=False,include_arr=[],exclude_arr=[]):
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
            exclude_file = os.path.join(r, "exclude.txt")
            if os.path.isfile(exclude_file):
                with f = open(exclude_file,'r'):
                    exclude_arr += f.read().splitlines()            
            exclude_file = os.path.join(r, user, ".exclude")
            if os.path.isfile(exclude_file):
                with f = open(exclude_file,'r'):
                    exclude_arr += f.read().splitlines()
            if os.path.isfile(path):
                # Check if file exists because it may be a symlink to
                # ../local.cfg and it might not exist.
                Config = ConfigParser.ConfigParser()
                for repo in list_repos(user,project):
                    if type(repo) is int:
                        continue
                    try:
                        name = repo["name"]
                        #If include filter is not defined all is accepted
                        if include_arr == []:
                            include_config = True
                        else:
                            include_config = False
                        for include in include_arr:
                            if re.match(include,name):
                                include_config = True
                        for exclude in exclude_arr:                                
                            if re.match(exclude,name):
                                include_config = False 
                        if name.startswith("trytond-") and not name.startswith("trytond-doc"):
                            dest_path = "./trytond/trytond/modules"
                            name = name.replace("trytond-","")
                        else: 
                            dest_path = "./"+user
                        if not Config.has_section(name):
                            Config.add_section(name)
                        Config.set(name,"exclude",not include_config)
                        Config.set(name,"path",dest_path)
                        if is_unstable:
                            Config.set(name,"unstable",True)
                        Config.set(name,"repo",encode(repo["scm"]))
                        Config.set(name,"url",encode(repo["links"]["clone"][0]["href"]))
                        Config.set(name,"branch",encode(repo["mainbranch"]["name"]))
                        Config.set(name,"scm",encode(repo["scm"]))
                        if repo["website"] != "":
                            Config.set(name,"website",encode(repo["website"]))
                        Config.set(name,"name",encode(repo["name"]))
                        Config.set(name,"has_wiki",encode(repo["has_wiki"]))
                        Config.set(name,"created_on",encode(datetime.strptime(repo["created_on"][0:-6],'%Y-%m-%dT%H:%M:%S.%f')))
                        Config.set(name,"updated_on",encode(datetime.strptime(repo["updated_on"][0:-6],'%Y-%m-%dT%H:%M:%S.%f')))
                        Config.set(name,"has_issues",encode(repo["has_issues"]))
                        Config.set(name,"size",encode(repo["size"]))
                        if repo["description"] != "":
                            Config.set(name,"description",encode(repo["description"]))
 
                    except Exception as e:
                        print e 
                        print name
                        if Config.has_section(name):   
                            Config.remove_section(name)
                f=open(path,"w+")
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