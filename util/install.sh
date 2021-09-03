#!/usr/bin/env bash

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

SRC_DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd -P )"
MN_VERSION="2.2.2"

DIST=Unknown
test -e /etc/debian_version && DIST="Debian"
grep Ubuntu /etc/lsb-release &> /dev/null && DIST="Ubuntu"
if [ "$DIST" = "Ubuntu" ] || [ "$DIST" = "Debian" ]; then
    install='sudo apt-get -y install'
    update='sudo apt-get update'
    remove='sudo apt-get -y remove'
    pkginst='sudo dpkg -i'
    addrepo='sudo apt-add-repository -y'
else
    echo "Only Ubuntu and Debian supported!"
    exit
fi

function all {
    printf 'installing all...\n' >&2
    echo "Install dir:" $SRC_DIR
    mininet
    postgres
    ravel
}

function mininet {
    echo "Installing mininet..."
    $update
    cd "$SRC_DIR"
    git clone git://github.com/mininet/mininet
    cd mininet
    git checkout $MN_VERSION
    sed -i 's/ iproute / iproute2 /g' util/install.sh #iproute package is deprecated
    ./util/install.sh -kmnvp
    cd "$SRC_DIR"

}

function postgres {
    sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    $install wget ca-certificates gnupg2
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
    $update
    $install postgresql-10
}

function ravel {
    $install python2.7 python-pip python-dev build-essential
    sudo pip install sqlalchemy sqlparse tabulate sysv_ipc

    $install postgresql-contrib postgresql-client \
	python-psycopg2 python-igraph postgis postgresql-plpython-10 \
	postgresql-10-pgrouting postgresql-10-plsh

    sudo -u postgres psql -c "CREATE DATABASE ravel;"
    sudo -u postgres psql -c "CREATE USER ravel WITH SUPERUSER;"
    sudo -u postgres psql -c "ALTER USER ravel WITH PASSWORD 'ravel';"
    sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS plpythonu;"
    sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS pgrouting;"

    printf -- '\n\n' >&2
    printf -- 'Ravel requires either "trust" or "md5" authentication for\n' >&2
    printf -- '"postgres" and "all" users in PostgreSQL.  Please modify\n' >&2
    printf -- 'the file /etc/postgresql/10/main/pg_hba.conf to:\n' >&2
    printf -- '     local    all    postgres    trust  #or md5\n' >&2
    printf -- '     local    all    all         trust  #or md5\n\n' >&2

    printf -- 'Or, choose yes below to automatically set to trust.\n' >&2
    read -p "Set authentication method to 'trust'? [y/N] " response
    response=${response,,}
    if [[ $response =~ ^(yes|y) ]]; then
	sudo sed -i -e '/^local/s/peer/trust/g' /etc/postgresql/10/main/pg_hba.conf
	sudo service postgresql restart
    fi
}

function usage {
    printf '\nUsage %s [-amprh]\n\n' $(basename $0) >&2

    printf 'Install and setup Ravel and its dependencies.\n\n' >&2

    printf 'options:\n' >&2
    printf -- ' -a: install (A)ll packages\n' >&2
    printf -- ' -m: install (Mininet) (with flags -kmnvp\n' >&2
    printf -- ' -p: install (P)ostgreSQL database\n' >&2
    printf -- ' -r: install (R)avel libraries and configure PostgreSQL\n' >&2
    printf -- ' -h: print this (H)elp message\n\n' >&2
}

if [ $# -eq 0 ]
then
    usage
else
    while getopts 'amprh' OPTION
    do
	case $OPTION in
	        a) all;;
	        m) mininet;;
	        p) postgres;;
	        r) ravel;;
	        h) usage;;
	    esac
    done
    shift $(($OPTIND - 1))
fi
