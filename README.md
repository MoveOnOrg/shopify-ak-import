# Shopify ActionKit Import

This Python 3.6 script imports Shopify orders into ActionKit.

## Install

* $`pip install -r requirements.txt`
* $`cp settings.py.template settings.py`
* Fill in settings.

## Run

* $`python main.py`

## Options

`python main.py --help` will output all available options.

## Travis setup

Travis is setup to auto-deploy this repo on commits to the `main` branch. Deploying requires both `settings.py` and `zappa_settings.json`, which are excluded from the repo, but included in an encrypted tar file, `secrets.tar.enc`. If either of these files need to be updated, the process for updating what Travis uses for deploy is:

1. `tar cvf secrets.tar zappa_settings.json settings.py`
2. `travis encrypt-file secrets.tar --add`
3. `rm secrets.tar`
4. `git add .travis.yml`
5. `git add secrets.tar.enc`
