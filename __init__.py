import bootstrap
import utils
from .scm import *
import patch
import tryton
from invoke import Collection
import reviewboard
import tests
import config
import gal


ns = Collection()
ns.add_task(clone)
ns.add_task(status)
ns.add_task(resolve)
ns.add_task(diff)
ns.add_task(summary)
ns.add_task(outgoing)
ns.add_task(pull)
ns.add_task(update)
ns.add_task(repo_list)
ns.add_task(fetch)
ns.add_task(unknown)
ns.add_task(stat)
ns.add_task(branch)
ns.add_task(module_diff)
ns.add_task(add2virtualenv)
ns.add_collection(Collection.from_module(bootstrap), 'bs')
ns.add_collection(Collection.from_module(utils))
ns.add_collection(Collection.from_module(patch))
ns.add_collection(Collection.from_module(tryton))
ns.add_collection(Collection.from_module(tests))
ns.add_collection(Collection.from_module(reviewboard), 'rb')
ns.add_collection(Collection.from_module(config))
ns.add_collection(Collection.from_module(gal))
