#!/usr/bin/env python
# This script intended to enrich data of catalogs entries 

import typer
import datetime
# from urllib.request import urlretrieve
import requests

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import csv
import json
import os
import shutil
import pprint
from pymongo import MongoClient, ASCENDING

CATALOG_TYPES_KEYS = {"Open data portal" : "od", 
    "Geoportal" : "geo", 
    "Scientific data repository" : "research",
    "Indicators catalog" : "ind",
    "Microdata catalog" : "micro",
    "General research repository" : "generalresearch",
    "Machine learning catalog" : "ml",
    "Datasets list" : "datalist",
    "Data search engine" : "datasearch",
    "API Catalog" : "apicat",
    "Data marketplace" : "datamarket"
}                

TEXT = """
Data marketplace	5
API Catalog	7
Data search engine	7
Machine learning catalog	11
Datasets list	24
Microdata catalog	66
Indicators catalog	84
"""


app = typer.Typer()

SERVER_NAME = 'localhost'
SERVER_PORT = 27017
DB_NAME = 'cdi'
SOFTWARE_COLL = 'software'
CATALOGS_COLL = 'catalogs'
COUNTRIES_COLL = 'countries'
STATS_COLL = 'statistics'

SOFTWARE_INDEXES = ['id', 'category']
CATALOGS_INDEXES = ['id', 'uid', 'access_mode', 'catalog_type', 'owner.type', 'software.id', 'content_types', 'langs', 'coverage.location.country.id', 'status', 'tags', 'owner.location.country.id']

def file_to_coll(filename, host, port, dbname, collname, index_list = []):
    client = MongoClient(host, port)
    db = client[dbname]
    db[collname].drop()
    coll = db[collname]
    f = open(filename, 'r', encoding='utf8')
    for l in f:
        record = json.loads(l)
        coll.insert_one(record)
    f.close()
    print('Loaded %s' % (filename))
    for ind in index_list:
        coll.create_index([(ind, ASCENDING),])
        print('- added index %s' % (ind))


def build_countries_collection():
    client = MongoClient(SERVER_NAME, SERVER_PORT)
    db = client[DB_NAME]
    coll = db[CATALOGS_COLL]
    countries = []
    countries_ids = coll.distinct('owner.location.country.id')
    for country_id in countries_ids:
        country = {'id' : country_id, 
        'name' : coll.find_one({'owner.location.country.id' : country_id}, {'owner.location.country.name' : 1})['owner']['location']['country']['name'],
        'num_catalogs' : coll.count_documents({'owner.location.country.id' : country_id})
        }

        stat_keys = CATALOG_TYPES_KEYS.values()
        for key in stat_keys:
            country['num_' + key] = 0
        country['num_other'] = 0
        catalogs = coll.find({'owner.location.country.id' : country_id}, {'catalog_type' : 1})
        for catalog in catalogs:
            if catalog['catalog_type'] in CATALOG_TYPES_KEYS.keys():
                key = CATALOG_TYPES_KEYS[catalog['catalog_type']]
                country['num_' + key] += 1
            else:
                country['num_other'] += 1
        countries.append(country)        


    db[COUNTRIES_COLL].drop()
    db[COUNTRIES_COLL].insert_many(countries)
    print('Created countries collection')
    for ind in ['id', 'num_catalogs']:
        db[COUNTRIES_COLL].create_index([(ind, ASCENDING),])
        print('- added index %s' % (ind))


def calc_stats_by_key(client, catalog_key, stats_key, slice_name):
    db = client[DB_NAME]
    statscoll = db[STATS_COLL]
    coll = db[CATALOGS_COLL]

    records = []
    keys = coll.distinct(catalog_key)
    for key in keys:
        record = {'slice' : slice_name, stats_key : key, 'num' : coll.count_documents({catalog_key : key})}
        records.append(record)
    statscoll.insert_many(records)
    print('- generated %s slice' % (slice_name))
    


def build_catalog_stats():
    print('Rebuilding statistics')
    client = MongoClient(SERVER_NAME, SERVER_PORT)
    client[DB_NAME][STATS_COLL].drop()
    calc_stats_by_key(client, catalog_key="catalog_type", stats_key="key", slice_name="catalogs")
    calc_stats_by_key(client, catalog_key="owner.type", stats_key="key", slice_name="ownerstypes")
    calc_stats_by_key(client, catalog_key="owner.location.country.name", stats_key="key", slice_name="ownerscountries")
    calc_stats_by_key(client, catalog_key="software.name", stats_key="key", slice_name="software")
    calc_stats_by_key(client, catalog_key="langs", stats_key="key", slice_name="langs")
    calc_stats_by_key(client, catalog_key="access_mode", stats_key="key", slice_name="access_modes")
    print('Adding indexes to statistics')
    for ind in ['slice', 'key', 'num']:
        client[DB_NAME][STATS_COLL].create_index([(ind, ASCENDING),])
        print('- added index %s' % (ind))


def retrieve(url, filename, force=True):
    if os.path.exists(filename) and not force:
        return
   
    response = requests.get(url)
    print('Downloading %s to %s' % (url, filename))
    if response.status_code == 200:
        with open(filename, "wb") as file:
            file.write(response.content)
    else:
        print("Failed to download the file. Status code:", response.status_code)

def update_with_dateno_stats():  
    client = MongoClient(SERVER_NAME, SERVER_PORT)
    # Update catalogs collection
    print('Updating catalogs with Dateno stats')
    coll_cat = client[DB_NAME][CATALOGS_COLL]
    f = open('../data/datasets/dateno_source_stats.json', 'r', encoding='utf8')
    data = json.load(f)
    f.close()
    for key, value in data.items():
        print('Updating %s' % (key))
        coll_cat.update_one({'uid' : key}, {'$set' : {"dateno" : {'indexed': True, "num_total" : int(value)}}}, upsert=False)
    coll_cat.update_many({'dateno': {'$exists' : False}}, {'$set' : {"dateno" : {'indexed': False, "num_total" : 0}}}, upsert=False)

    print('Updating countries with Dateno stats')
    coll_count = client[DB_NAME][COUNTRIES_COLL]
    f = open('../data/datasets/dateno_country_stats.json', 'r', encoding='utf8')
    data = json.load(f)
    f.close()
    for key, value in data.items():
        print('Updating %s' % (key))
        coll_count.update_one({'name' : key}, {'$set' : {"dateno" : {'indexed': True, "num_total" : int(value)}}}, upsert=False)

    coll_count.update_many({'dateno': {'$exists' : False}}, {'$set' : {"dateno" : {'indexed': False, "num_total" : 0}}}, upsert=False)

        


def update_datasets(force=True):
    print('Updating datasets')
    retrieve("https://raw.githubusercontent.com/commondataio/dataportals-registry/main/data/datasets/software.jsonl", filename='../data/datasets/software.jsonl', force=force),
    retrieve("https://raw.githubusercontent.com/commondataio/dataportals-registry/main/data/datasets/full.jsonl", filename='../data/datasets/catalogs.jsonl', force=force),
    retrieve("https://raw.githubusercontent.com/commondataio/dateno-stats/main/data/current/crawledsources.json", filename='../data/datasets/dateno_crawled_list.json', force=force),
    retrieve("https://raw.githubusercontent.com/commondataio/dateno-stats/main/data/current/stats_country_type.json", filename='../data/datasets/dateno_country_type_stats.json', force=force),
    retrieve("https://raw.githubusercontent.com/commondataio/dateno-stats/main/data/current/stats_sources.json", filename='../data/datasets/dateno_source_stats.json', force=force),
    retrieve("https://raw.githubusercontent.com/commondataio/dateno-stats/main/data/current/stats_countries.json", filename='../data/datasets/dateno_country_stats.json', force=force)

@app.command()
def rebuild(force:bool = False):
    """Recreate database from data files"""
    update_datasets(force)
    file_to_coll('../data/datasets/catalogs.jsonl', SERVER_NAME, SERVER_PORT, DB_NAME, CATALOGS_COLL, CATALOGS_INDEXES)
    file_to_coll('../data/datasets/software.jsonl', SERVER_NAME, SERVER_PORT, DB_NAME, SOFTWARE_COLL, SOFTWARE_INDEXES)
    build_countries_collection()
    build_catalog_stats()
    update_with_dateno_stats()


@app.command()
def getfiles(force:bool = False):
    """Download latest snapshots"""
    update_datasets(force)

@app.command()
def update():    
    """Update Dateno stats"""
    update_with_dateno_stats()

if __name__ == "__main__":    
    app()