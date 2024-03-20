# dataportals-web
Website code of the registry.commondata.io
Website made with Flask web server and HTML templates

# Requirements
Python 3+
Mongo Server(Mongo Atlas)

# How to run app localy with docker
0. Install docker compose if you don't have it
```
brew install docker-compose
```
1. Run MondoDB in within Docker

```
docker-compose up -d 

```


2. Install requirement 
```
python3 -m venv venv && venv/bin/pip install -r requirements.txt

```

3. Enrich data of catalogs and populate DB

```
cd scripts
../venv/bin/python builder.py update
../venv/bin/python builder.py rebuild
```

3. Run app 
```
cd ..
cd src
../venv/bin/python /registry.py
```


