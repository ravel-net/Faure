# Fauré

Fauré is a network management platform built atop the Ravel controller. Ravel is a software-defined networking (SDN) controller that uses a standard SQL abstraction to represent and update the network (For more information on Ravel, see [https://github.com/ravel-net/ravel](https://github.com/ravel-net/ravel) or [http://ravel-net.org](http://ravel-net.org) or follow the [walkthrough](http://ravel-net.org/walkthrough). In addition to the familiar interface of traditional databases inherited from Ravel, Fauré incorporates and implements the new theories of incomplete database, allowing direct modeling and new verification methods of networks that are only partially known (For more information, see the [Fauré paper](https://doi.org/10.1145/3484266.3487391) at [HotNets'21](https://conferences.sigcomm.org/hotnets/2021/)).

## New Features

- `sarasate` application. Relational Algebra for Conditional Table.
  
  For the details, see [`README_sarasate.md`](apps/README_sarasate.md)

- `bgp` application. BGP simulation by using Sarasate application

  For the details, see [`README_bgp.md`](apps/README_bgp.md)

## Prerequisites

- Ubuntu 20.04(recommended) or greater
- Python 3
- pip3


## Installation

For installation instructions, see [`INSTALL`](INSTALL).

We assume your system has matched prerequisites, the `INSTALL` can successfully run under these prerequisites. Thus, before installing Fauré, please check whether the prerequisites are available.

## Fauré Command-Line Arguments

Fauré command-line arguments:

  * `--help`, `-h`: show the help message and exit
  * `--clean`, `-c`: cleanup Ravel and Mininet 
  * `--onlydb`, `-o`: start Ravel without Mininet
  * `--reconnect`, `-r`: reconnect to an existing database, skipping reinit
  * `--noctl`, `-n`: start without controller (Mininet will still attempt to connect to a remote controller)
  * `--db`, `-d`: PostgreSQL database name
  * `--user`, -`u`: PostgreSQL username
  * `--password`, `-p`: force prompt for PostgreSQL password
  * `--verbosity`, `-v`: set logging output verbosity (debug|info|warning|critical|error)

For example, to run Fauré under `--onlydb` with default database *ravel* and user *ravel*

    sudo python3 ravel.py --onlydb

To run Fauré under `--onlydb` with other databases and users:

    sudo python3 ravel.py --onlydb --db=dbname --user=username --password=password

## Fauré CLI Commands

The Fauré CLI has a number of commands to monitor and control applications and the network:

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

- Fauré 1.0 support Python 3!

- We upgrade Python 2 to Python 3 in Fauré. If still want to use the Python 2 version, see [Ravel](https://github.com/ravel-net/ravel).

## Notes

In Fauré system, we are not openning all modes provided in Ravel system. In the future, we will open all modes related to Mininet in the Fauré system.