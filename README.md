# Ravel

Ravel is a software-defined networking (SDN) controller that uses a standard SQL database to represent the network.  _Why a database?_ SDN fundamentally revolves around data representation--representation of the network topology and forwarding, as well as the higher-level abstractions useful to applications.

In Ravel, the entire network control infrastructure is implemented within a SQL database.  Abstractions of the network take the form of _SQL views_ expressed by SQL queries that can be instantiated and extended on the fly.  To allow multiple simultaneous abstractions to collectively drive control, Ravel automatically _orchestrates_ the abstractions to merge multiple views into a coherent forwarding behavior.

For more information, see [http://ravel-net.org](http://ravel-net.org) or follow the [walkthrough](http://ravel-net.org/walkthrough).


### Installation

For installation instructions, see `INSTALL`.


### Ravel Command-Line Arguments

Ravel command-line arguments:

  * `--help`, `-h`: show the help message and exit
  * `--clean`, `-c`: cleanup Ravel and Mininet 
  * `--onlydb`, `-o`: start Ravel without Mininet
  * `--reconnect`, `-r`: reconnect to an existing database, skipping reinit
  * `--noctl`, `-n`: start without controller (Mininet will still attempt to connect to a remote controller)
  * `--db`, `-d`: PostgreSQL database name
  * `--user`, -`u`: PostgreSQL username
  * `--password`, `-p`: force prompt for PostgreSQL password
  * `--topo`, `-t`: specify a Mininet topology argument
  * `--custom`, `-c`: specify custom classes or params for Mininet
  * `--script`, `-s`: execute a Ravel script immediately after startup
  * `--verbosity`, `-v`: set logging output verbosity (debug|info|warning|critical|error)

For example, to run Ravel with Mininet in the background, on a topology with a single switch and three hosts:

    sudo ./ravel.py --topo=single,3

To run only the database component of Ravel (i.e., no Mininet) on the same topology, using database `mydb` and username `myuser`:

    sudo ./ravel.py --topo=single,3 --onlydb --db=mydb --user=myuser


### Ravel CLI Commands

The Ravel CLI has a number of commands to monitor and control applications and the network:

  * `help`: show list of commands
  * `apps`: list discovered applications
  * `stat`: show running configuration
  * `m`: execute Mininet command
  * `p`: execute SQL statement
  * `time`: print execution time
  * `profile`: print detailed execution time
  * `reinit`: truncate all database tables except topology
  * `watch`: spawn new xterm watching database tables
  * `exec`: execute a Ravel script
  * `orch load`: load a set of orchestrated applications (in ascending ordering of priority)
  * `orch unload`: unload one or more applications from the orchestrated set
  * `orch auto [on/off]`: auto-commit commands for orchestration
  * `rt addflow [src] [dst]`: install a flow
  * `rt delflow [src] [dst]`, `rt delflow [flow id]`: remove a flow