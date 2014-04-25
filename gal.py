#!/usr/bin/env python
import os
import sys
import time
import subprocess
import hgapi
import random
from decimal import Decimal
from invoke import task

from .utils import t

directory = os.path.abspath(os.path.normpath(os.path.join(os.getcwd(),
                    'trytond')))
proteus_directory = os.path.abspath(os.path.normpath(os.path.join(os.getcwd(),
                    'proteus')))

if os.path.isdir(directory):
    sys.path.insert(0, directory)
if os.path.isdir(proteus_directory):
    sys.path.insert(0, proteus_directory)

try:
    from proteus import config as pconfig, Model, Wizard
except:
    pass


def check_output(*args):
    t.bold(' '.join(args))
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    process.wait()
    data = process.stdout.read()
    data += process.stderr.read()
    return data

def connect_database(database=None, password='admin',
        database_type='postgresql'):
    if database is None:
        database = 'gal'
    global config 
    config = pconfig.set_trytond(database, database_type=database_type,
        password=password, config_file='trytond.conf')

def database_name():
    import uuid
    return uuid.uuid4()


def dump(dbname=None):
    if dbname is None:
        dbname = 'gal'
    from trytond import backend
    Database = backend.get('Database')
    Database(dbname).close()
    # Sleep to let connections close
    time.sleep(1)
    dump_file = 'gal.sql'
    check_output('pg_dump', '-f', gal_path(dump_file), dbname)
    gal_repo().hg_add(dump_file)

def restore(dbname=None):
    if dbname is None:
        dbname = 'gal'
    dump_file = 'gal.sql'
    print check_output('dropdb', dbname)
    print check_output('createdb', dbname)
    print check_output('psql', '-f', gal_path(dump_file), dbname)

def gal_path(path=None):
    res = 'gal'
    if path:
        res = os.path.join(res, path)
    return res

def gal_repo():
    path = gal_path()
    if os.path.exists(path) and not os.path.isdir(path):
        t.red('Error: gal file exists')
        sys.exit(1)
    if os.path.isdir(path) and not os.path.isdir(os.path.join(path, '.hg')):
        t.red('Invalid gal repository')
        sys.exit(1)
    repo = hgapi.Repo(path)
    if not os.path.exists(path):
        os.mkdir(path)
        repo.hg_init()
    return repo

def gal_action(action, **kwargs):
    global commit_msg
    commit_msg = ', '.join(["%s='%s'" % (k, v) for k, v in kwargs.iteritems()])
    commit_msg = '%s(%s)' % (action, commit_msg)

def gal_commit():
    dump()
    gal_repo().hg_commit(commit_msg)

@task
def create(language=None, password=None):
    gal_action('create', language=language, password=password)
    connect_database()
    gal_commit()

@task
def replay(commit=None):
    repo = gal_repo()
    for revision in repo.revisions(slice(0, 'tip')):
        # TODO: This is not safe. Run with care.
        eval(revision.desc)

@task
def get(name):
    """
    Restores current gal database with the given database name
    """
    restore(name)

@task
def set(name):
    """
    Saves the given database as current gal database
    """
    gal_action('set')
    dump(name)
    gal_commit()

def upgrade_modules(modules=None, all=False):
    '''
    Function get from tryton_demo.py in tryton-tools repo:
    http://hg.tryton.org/tryton-tools
    '''
    assert all or modules

    Module = Model.get('ir.module.module')
    if all:
        modules = Module.find([
                ('state', '=', 'installed'),
                ])
    else:
        modules = Module.find([
                ('name', 'in', modules),
                ('state', '=', 'installed'),
                ])

    Module.upgrade([x.id for x in modules], config.context)
    Wizard('ir.module.module.install_upgrade').execute('upgrade')

    ConfigWizardItem = Model.get('ir.module.module.config_wizard.item')
    for item in ConfigWizardItem.find([('state', '!=', 'done')]):
        item.state = 'done'
        item.save()

    upgraded_modules = [x.name for x in Module.find([
                ('state', '=', 'to_upgrade'),
                ])]
    return upgraded_modules

@task
def set_active_languages(lang_codes=None):
    gal_action('set_active_languages', lang_codes=lang_codes)
    restore()
    connect_database()
    if lang_codes:
        lang_codes = lang_codes.split(',')

    Lang = Model.get('ir.lang')
    User = Model.get('res.user')

    if not lang_codes:
        lang_codes = ['ca_ES', 'es_ES']
    langs = Lang.find([
            ('code', 'in', lang_codes),
            ])
    assert len(langs) > 0

    Lang.write([l.id for l in langs], {
            'translatable': True,
            }, config.context)

    default_langs = [l for l in langs if l.code == lang_codes[0]]
    if not default_langs:
        default_langs = langs
    users = User.find([])
    if users:
        User.write([u.id for u in users], {
                'language': default_langs[0].id,
                }, config.context)

    # Reload context
    User = Model.get('res.user')
    config._context = User.get_preferences(True, config.context)

    if not all(l.translatable for l in langs):
        # langs is fetched before wet all translatable
        print "Upgrading all because new translatable languages has been added"
        upgrade_modules(config, all=True)
    gal_commit()

@task
def install_modules(modules):
    '''
    Function taken from tryton_demo.py in tryton-tools repo:
    http://hg.tryton.org/tryton-tools
    '''
    gal_action('install_modules', modules=modules)
    restore()
    connect_database()
    modules = modules.split(',')

    Module = Model.get('ir.module.module')
    modules = Module.find([
            ('name', 'in', modules),
            #('state', '!=', 'installed'),
            ])
    Module.install([x.id for x in modules], config.context)
    modules = [x.name for x in Module.find([
                ('state', 'in', ('to install', 'to_upgrade')),
                ])]
    Wizard('ir.module.module.install_upgrade').execute('upgrade')

    ConfigWizardItem = Model.get('ir.module.module.config_wizard.item')
    for item in ConfigWizardItem.find([('state', '!=', 'done')]):
        item.state = 'done'
        item.save()

    installed_modules = [m.name
        for m in Module.find([('state', '=', 'installed')])]

    gal_commit()
    return modules, installed_modules

def create_party(name, street=None, zip=None, city=None,
        subdivision_code=None, country_code='ES', phone=None, website=None,
        address_name=None,
        account_payable=None, account_receivable=None):
    Address = Model.get('party.address')
    ContactMechanism = Model.get('party.contact_mechanism')
    Country = Model.get('country.country')
    Party = Model.get('party.party')
    Subdivision = Model.get('country.subdivision')

    parties = Party.find([('name', '=', name)])
    if parties:
        return parties[0]

    country, = Country.find([('code', '=', country_code)])
    if subdivision_code:
        subdivision, = Subdivision.find([('code', '=', subdivision_code)])
    else:
        subdivision = None

    party = Party(name=name)
    party.addresses.pop()
    party.addresses.append(
        Address(
            name=address_name,
            street=street,
            zip=zip,
            city=city,
            country=country,
            subdivision=subdivision))
    if phone:
        party.contact_mechanisms.append(
            ContactMechanism(type='phone',
                value=phone))
    if website:
        party.contact_mechanisms.append(
            ContactMechanism(type='website',
                value=website))

    if account_payable:
        party.account_payable = account_payable
    if account_receivable:
        party.account_receivable = account_receivable

    party.save()
    return party

@task
def create_parties():
    gal_action('create_parties')
    restore()
    connect_database()

    with open('tasks/companies.txt', 'r') as f:
        companies = f.read().split('\n')
    with open('tasks/streets.txt', 'r') as f:
        streets = f.read().split('\n')
    with open('tasks/names.txt', 'r') as f:
        names = f.read().split('\n')
    with open('tasks/surnames.txt', 'r') as f:
        surnames = f.read().split('\n')
    phones = ['93', '972', '973', '977', '6', '900']
    for x in xrange(4000):
        company = random.choice(companies)
        name = random.choice(names)
        surname1 = random.choice(surnames)
        surname2 = random.choice(surnames)
        street = random.choice(streets)
        name = '%s %s, %s' % (surname1, surname2, name)
        street = '%s, %d' % (street, random.randrange(1, 100))
        phone = random.choice(phones)
        while len(phone) < 9:
            phone += str(random.randrange(9))
        create_party(company, street=street, zip=None, city=None,
            subdivision_code=None, country_code='ES', phone=phone,
            website=None, address_name=name)

    gal_commit()

def create_product(name, code="", template=None, cost_price=None,
        list_price=None, type='goods', unit=None, consumable=False):

    ProductUom = Model.get('product.uom')
    Product = Model.get('product.product')
    ProductTemplate = Model.get('product.template')
    Account = Model.get('account.account')
    Company = Model.get('company.company')
    company = Company(1)

    product = Product.find([('name', '=', name), ('code', '=', code)])
    if product:
        return product[0]

    if not cost_price:
        cost_price = random.randrange(0, 1000)

    if not list_price:
        list_price = cost_price * random.randrange(1, 2)

    if unit is None:
        unit = ProductUom(1)

    if template is None:
        template = ProductTemplate()
        template.name = name
        template.default_uom = unit
        template.type = type
        template.consumable = consumable
        template.list_price = Decimal(str(list_price))
        template.cost_price = Decimal(str(cost_price))

        if hasattr(template, 'account_expense'):
            expense = Account.find([
                ('kind', '=', 'expense'),
                ('company', '=', company.id),
                ])
            if expense:
                template.account_expense = expense[0]
        if hasattr(template, 'account_revenue'):
            revenue = Account.find([
                ('kind', '=', 'revenue'),
                ('company', '=', company.id),
                ])
            if revenue:
                template.account_revenue = revenue[0]

        template.products[0].code = code
        template.save()
        product = template.products[0]
    else:
        product = Product()
        product.template = template
        product.code = code
        product.save()
    return product

@task
def create_products():
    gal_action('create_parties')
    restore()
    connect_database()

    import xmltodict
    with open('tasks/catalog.xml', 'r') as f:
        xml = xmltodict.parse(f.read())
    count = 0
    for item in xml.get('ICECAT-interface').get('files.index').get('file'):
        name = item.get('@Model_Name')
        create_product(name)
        count += 1
        if count >= 400:
            break

    gal_commit()


# TODO: Add get and set functions to allow dumping a database with a given name
# and adding to the repository a snapshot of a given database
