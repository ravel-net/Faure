# Faure

Faure is the newest version of Ravel which is a software-defined networking (SDN) controller that uses a standard SQL database to represent the network. For the more information of Ravel, see [https://github.com/ravel-net/ravel](https://github.com/ravel-net/ravel) or [http://ravel-net.org](http://ravel-net.org) or follow the [walkthrough](http://ravel-net.org/walkthrough). 


## Installation

For installation instructions, see [`INSTALL`](INSTALL).


## Faure Command-Line Arguments

Faure command-line arguments:

  * `--help`, `-h`: show the help message and exit
  * `--clean`, `-c`: cleanup Ravel and Mininet 
  * `--onlydb`, `-o`: start Ravel without Mininet
  * `--reconnect`, `-r`: reconnect to an existing database, skipping reinit
  * `--noctl`, `-n`: start without controller (Mininet will still attempt to connect to a remote controller)
  * `--db`, `-d`: PostgreSQL database name
  * `--user`, -`u`: PostgreSQL username
  * `--password`, `-p`: force prompt for PostgreSQL password
  * `--verbosity`, `-v`: set logging output verbosity (debug|info|warning|critical|error)

For example, to run Faure under `--onlydb` with default database *ravel* and user *ravel*

    sudo python3 ravel.py --onlydb

To run Faure under `--onlydb` with other databases and users:

    sudo python3 ravel.py --onlydb --db=dbname --user=username --password=password

## Faure CLI Commands

The Faure CLI has a number of commands to monitor and control applications and the network:

  * `help`: show list of commands
  * `apps`: list discovered applications
  * `stat`: show running configuration
  * `p`: execute SQL statement
  * `time`: print execution time
  * `profile`: print detailed execution time
  * `reinit`: truncate all database tables except topology
  * `watch`: spawn new xterm watching database tables
  * `orch load`: load a set of orchestrated applications (in ascending ordering of priority)
  * `orch unload`: unload one or more applications from the orchestrated set
  * `orch auto [on/off]`: auto-commit commands for orchestration

## Python 3 Support

- Faure 1.0 support Python 3!

- We upgrade Python 2 to Python 3 in Faure. If still want to use the Python 2 version, see [Ravel](https://github.com/ravel-net/ravel).

## New Features

- `sarasate` application. Relational Algebra for Conditional Table.
  
  For the details, see [`README_sarasate.md`](https://github.com/ravel-net/Faure/blob/main/apps/README_sarasate.md)

- `bgp` application. BGP simulation by using Sarasate application

  For the details, see [`README_bgp.md`](https://github.com/ravel-net/Faure/blob/main/apps/README_sarasate.md)
