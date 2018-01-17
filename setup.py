from setuptools import setup, find_packages

setup(
        name='dockls',
        version='1.5',
        description='CLI Client for interacting with docker registry v2 configured with token auth',
        url='',
        author='Adam Lamers',
        author_email='adamlamers@gmail.com',
        install_requires = ['click', 'requests', 'docker[tls]'],
        packages=['dockls'],
        entry_points={
            'console_scripts': [
                    'dockls=dockls.dockls:cli'
                ]
            }

)
