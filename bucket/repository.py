#!/usr/bin/env python
from invoke import task, Collection
from .util import post, get, prettyprint


@task()
def create(name, owner, private=False, description=''):

    url = "https://api.bitbucket.org/2.0/repositories/{owner}/{name}"
    url = url.format(owner=owner, name=name)

    data = {
        'scm': "hg",
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
    url = 'https://api.bitbucket.org/2.0/repositories/{teamname}'
    if project:
        url += '?q=project.key="{projectname}"'
    url = url.format(teamname=team,projectname=project)
    data = {}
    next_query = url
    print(url)
    while next_query:
        res = get(next_query, data)
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
