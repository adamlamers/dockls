import requests
import re
import click
import os
import sys
import json
import time

class DockerCredentials(object):

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password

    def __repr__(self):
        return "<DockerCredentials: {}>".format(self.username)

class DockerTag(object):
    def __init__(self, repository, name):
        self.repository = repository
        self.name = name

    @property
    def manifest(self):
        url = "/v2/{}/manifests/{}".format(self.repository.name, self.name)
        data = self.repository.registry.get_object(url)
        return data

class DockerRepository(object):

    def __init__(self, registry, name):
        self.registry = registry
        self.name = name

    @property
    def tags(self):
        data = self.registry.get_object("/v2/{}/tags/list".format(self.name))['tags']
        return [DockerTag(self, name) for name in data]

    def __repr__(self):
        return '<DockerRepository: {}>'.format(self.name)

class DockerRegistry(object):

    def __init__(self, url, username, password):
        self.url = url
        self.credentials = DockerCredentials(username=username, password=password)
        self.token = None
        self.authenticated = False
        self._auth_data = None

    def auth_required(self, url):
        response = requests.get(self.url + url)
        if response.status_code == 401:
            auth_header = response.headers['www-authenticate']
            s = auth_header.split(" ")

            auth_type = s[0]
            auth_data = s[1]

            s = auth_data.split(",")
            d = {}
            for item in s:
                x = item.split("=")

                if x[1].startswith("\""):
                    x[1] = x[1][1:]
                if x[1].endswith("\""):
                    x[1] = x[1][:-1]

                d[x[0]] = x[1]

            self._auth_data = { 'type': auth_type,
                                'data': d }

            return True
        elif response.status_code == 200:
            return False

    def authenticate(self):
        if self._auth_data['type'] == 'Bearer':

            params = { 'account' : self.credentials.username,
                       'client_id' : 'docker',
                       'offline_token': True,
                       'service': 'auth.docker.telkonet.com',
                       'scope' : self._auth_data['data']['scope']}

            response = requests.get(self._auth_data['data']['realm'],
                    auth=(self.credentials.username,
                        self.credentials.password),
                    params=params)

            if response.status_code == 200:
                self.token = response.json()['token']
                return True

            return False

    def get_object(self, path):
        self.auth_required(path)

        if not self.authenticate():
            print("Authentication failed.")
            sys.exit(2)

        headers = { 'Authorization' : 'Bearer {}'.format(self.token) }
        r = requests.get(self.url + path, headers=headers)
        return r.json()

    @property
    def repositories(self):
        data = self.get_object('/v2/_catalog')
        return [DockerRepository(self, name) for name in data['repositories']]

class Cache(dict):

    def __getitem__(self, key):
        return super(Cache, self).get(key)

    def __setitem__(self, key, value):
        super(Cache, self).__setitem__(key, { 'value': value, 'created': time.time() })

def _config():
    try:
        with open(os.path.expanduser("~/.dockls"), "rb") as f:
            return json.loads(f.read().decode())
    except IOError:
        return {}

config = _config()
cache = Cache()

try:
    with open("/tmp/dockls_cache.cache", "r") as f:
        cache = json.loads(f.read())
except Exception:
    pass

def get_tags(name):
    d = DockerRegistry('https://' + config['repo'], config['username'], config['password'])
    print("---------- [{}] Tags ----------".format(name))
    for repo in d.repositories:
        if repo.name == name:
            for i, tag in enumerate(repo.tags):
                print('    {}'.format(tag.name))

@click.group(invoke_without_command=True)
@click.option('--recurse', '-r', is_flag=True, help="Display tags of all repositories")
@click.pass_context
def cli(ctx, recurse):
    if ctx.invoked_subcommand is None:
        if recurse:
            d = DockerRegistry('https://' + config['repo'], config['username'], config['password'])
            for i, repo in enumerate(d.repositories):
                print("---------- [{}/{}] {} ----------".format(i+1, len(d.repositories), repo.name))
                for i, tag in enumerate(repo.tags):
                    print('    {}'.format(tag.name))
        else:
            images()

@cli.command(help="List images in repository")
def images():
    d = DockerRegistry('https://' + config['repo'], config['username'], config['password'])
    print("---------- [{}] Repositories ----------".format(config['repo']))
    for repo in d.repositories:
        print("  {}".format(repo.name))

@cli.command(help="List tags for an image")
@click.argument("name")
def tags(name):
    get_tags(name)

@cli.command(help="Perform authentication with a repository")
@click.argument("repository")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
def login(repository, username, password):
    config['repo'] = repository
    config['username'] = username
    config['password'] = password
    with open(os.path.expanduser("~/.dockls"), "wb") as f:
        f.write(json.dumps(config).encode())

@cli.command(help="Pull an image from the remote repository\n(requires docker login)")
@click.argument("image")
@click.argument("tag", required=False)
@click.option("--all", "-a", is_flag=True, help="Pull all tags for this image")
def pull(image, tag, all):
    client = None
    try:
        import docker
        client = docker.from_env()
    except ImportError:
        print("Could not import the docker python library.")
        sys.exit(1)

    try:
        if tag is None and (click.confirm('Download all tags for {}?'.format(image)) or all):
            d = DockerRegistry('https://' + config['repo'], config['username'], config['password'])
            for repo in d.repositories:
                if repo.name == image:
                    for tag in repo.tags:
                        print('Pulling {}/{}:{}'.format(config['repo'], image, tag.name))
                        img = client.images.pull('{}/{}:{}'.format(config['repo'], image, tag.name))
        else:
            print('Pulling {}/{}:{}'.format(config['repo'], image, tag))
            img = client.images.pull('{}/{}:{}'.format(config['repo'], image, tag))
    except docker.errors.NotFound:
        print("Error: Image {}:{} does not exist on {}".format(image, tag, config['repo']))
        print("\n\nRun dockls -r to see all available repositories and tags.")
        sys.exit(1)

cli()
