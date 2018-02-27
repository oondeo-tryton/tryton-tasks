#!/usr/bin/env python
from invoke import task, Collection
from .util import post, get, prettyprint


@task()
def create(name, owner=None, private=False, description=''):

    if owner:
        url = "https://api.github.com/orgs/{owner}/repos"
        url = url.format(owner=owner)
    else:
        url = "https://api.github.com/user/repos"

    data = {
        'name': name,
        'is_private': private,
        'description': description,
        'fork_policy': 'allow_forks',
        'language': 'python',
        'has_issues': True,
        'has_wiki': False,
    }

    res = post(url, data)
    prettyprint(res)


def print_repo(repo, detail=True):

    print "Repo:", repo['full_name'].ljust(75, ' '), "created:", \
     repo['created_on'], "updated:", repo['updated_on'], \
     "Private:", repo['is_private']


@task()
def show(team='nantic',project=None):
    for line in list_repos(team,project):
        if type(line) is int:
            print "Repositories: ", line
        else:
            print_repo(line)

def list_repos(team='nantic',project=None):
    #url = "https://api.bitbucket.org/2.0/teams/{teamname}/repositories"
    url = 'https://api.github.com/users/{teamname}/repos'
    #if project:
    #    url += '?q=project.key="{projectname}"'
    url = url.format(teamname=team,projectname=project)
    data = {}
    #next_query = url
    while True:
        res = get(next_query, data)
        try:
            for i in res.iteritems():
                if num_repos == 0:
                    yield num_repos
                num_repos += 1
        except:
            break
        if url == next_query:
            num_repos = res.get('size')
            #print "Repositories:", num_repos
            yield num_repos

        next_query = res.get('next')
        for repo in res['values']:
            #print_repo(repo)
            yield repo

RepoCollection = Collection()
RepoCollection.add_task(create)
RepoCollection.add_task(show)
