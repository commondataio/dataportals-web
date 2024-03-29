from flask import Flask, json, jsonify, redirect, render_template, send_file, send_from_directory, request, url_for, flash, Response
from pymongo import MongoClient
import collections

SERVER_NAME = 'localhost'
SERVER_PORT = 27017
DB_NAME = 'cdi'
SOFTWARE_COLL = 'software'
CATALOGS_COLL = 'catalogs'
COUNTRIES_COLL = 'countries'
STATS_COLL = 'statistics'

DEBUG = False
SECRET_KEY = "azt3eycglbkj30i6tdfg,xfkxflgkdrfogkotg,/vxlf"
REGISTRY_HOST = '127.0.0.1'
REGISTRY_PORT = 8089
CATALOGS_DATA_PATH = '../data/datasets/catalogs.jsonl'

PAGE_SIZE = 100

client = MongoClient(SERVER_NAME, SERVER_PORT)
db = client[DB_NAME]

def load_data(filename):
    data = {}
    f = open(filename, 'r', encoding='utf8')
    for row in f:
        record = json.loads(row)
        data[record['uid']] = record
    f.close()
    return data


def about_view():
    return render_template('about.tmpl')

def home_view():
    objects_ct = list(db[STATS_COLL].find({'slice': 'catalogs'}).sort('num', -1).limit(7))
    return render_template('home.tmpl', stats=objects_ct)

def analytics_view():
    objects_ct = db[STATS_COLL].find({'slice': 'catalogs'}).sort('num', -1)
    objects_ot = db[STATS_COLL].find({'slice': 'ownerstypes'}).sort('num', -1)
    objects_sf = db[STATS_COLL].find({'slice': 'software'}).sort('num', -1)
    objects_ln = db[STATS_COLL].find({'slice': 'langs'}).sort('num', -1)
    objects_am = db[STATS_COLL].find({'slice': 'access_modes'}).sort('num', -1)
    return render_template('analytics.tmpl', objects_ct=objects_ct, objects_ot=objects_ot, objects_sf=objects_sf, objects_ln=objects_ln, objects_am=objects_am)


def countries_list_view():
    return render_template('countries_list.tmpl', objects=db[COUNTRIES_COLL].find())

def countries_single_view(slug):
    obj = db[COUNTRIES_COLL].find_one({'id': slug})
    return render_template('country.tmpl', object=obj, catalogs_list=db[CATALOGS_COLL].find({'owner.location.country.id' : slug}))


def catalog_list_view():
    skip_num = 0
    skip_val = request.args.get('skip')
    if skip_val is not None and skip_val.isdigit() and int(skip_val) > 0:
        skip_num = int(skip_val)
    object_list = list(db[CATALOGS_COLL].find().skip(skip_num).limit(PAGE_SIZE))
    has_next = len(object_list) == PAGE_SIZE
    has_prev = skip_num != 0
    return render_template('catalogs_list.tmpl', objects=object_list, has_next=has_next, has_prev=has_prev, num_skip=skip_num)

def catalog_single_view(slug):
    obj = db[CATALOGS_COLL].find_one({'uid': slug})
    return render_template('catalog.tmpl', object=obj)

def catalog_view_json(slug):
    obj = db[CATALOGS_COLL].find_one({'uid': slug}, {'_id' : 0})
    return jsonify(obj)

def countries_single_view_json(slug):
    obj = db[COUNTRIES_COLL].find_one({'id': slug}, {'_id' : 0})
    obj['catalogs'] = list(db[CATALOGS_COLL].find({'owner.location.country.id' : slug}, {'_id' : 0}))
    return jsonify(obj)


def countries_single_view_csv(slug):
    obj = db[COUNTRIES_COLL].find_one({'id': slug}, {'_id' : 0})
    records = []
    obj['catalogs'] = list(db[CATALOGS_COLL].find({'owner.location.country.id' : slug}, {'_id' : 0}))
    return jsonify(obj)


def registry_view_json():
    return jsonify(list(db[CATALOGS_COLL].find()))


def add_views_rules(app):
    app.add_url_rule('/countries', 'countries', countries_list_view)
    app.add_url_rule('/browse', 'search', catalog_list_view)
    app.add_url_rule('/catalogs.json', '/catalogs.json', registry_view_json)
    app.add_url_rule('/catalog/<slug>', 'catalogs/<slug>', catalog_single_view)
    app.add_url_rule('/catalog/<slug>.json', 'catalogs/<slug>.json', catalog_view_json)
    app.add_url_rule('/country/<slug>', 'countries/<slug>', countries_single_view)
    app.add_url_rule('/country/<slug>.csv', 'countries/<slug>.csv', countries_single_view_csv)
    app.add_url_rule('/country/<slug>.json', 'countries/<slug>.json', countries_single_view_csv)
    app.add_url_rule('/', 'home', home_view)
    app.add_url_rule('/about', 'about', about_view)
    app.add_url_rule('/analytics', 'analytics', analytics_view)

def run_server():

    app = Flask("Data catalogs registry", static_url_path='/assets')
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['PROPAGATE_EXCEPTIONS'] = True

    add_views_rules(app)

    app.run(host=REGISTRY_HOST, port=REGISTRY_PORT, debug=DEBUG)


if __name__ == "__main__":
    run_server()
