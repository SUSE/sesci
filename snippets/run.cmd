#!/bin/sh
CMDNAME=${1:-"run"}
shift
PIDFILE=~/${CMDNAME}.pid
LOGFILE=~/${CMDNAME}.log
echo Running: $@
$@ </dev/null > $LOGFILE 2>&1 &
PID=$!
echo $PID > $PIDFILE
echo Command PID=$PID saved to $PIDFILE
echo Output is capturing in $LOGFILE file
