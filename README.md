# dockls

dockls is a tool for viewing private docker registries configured behind token authentication

## Installation

`pip install git+https://github.com/adamlamers/dockls`

## Usage

`dockls login <repository URL>`

Authenticate against a private docker registry

`dockls [-r]`

List all available docker repositories at the configured registry
`-r` flag will recursively list all tags for every repository.

`dockls tags <repository>`

List the tags for a specific repository.


`dockls --help`

Show help information




