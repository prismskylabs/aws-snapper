#!/usr/bin/env python
# encoding: utf-8
# A simple init script that run autosnap script hourly
import sys
import os
import subprocess
import shlex
import threading

def hourlyTask():
    p = subprocess.Popen(shlex.split('/opt/aws-autosnap/autosnap.py'))
    returnCode = None
    while(returnCode is None):
    	returnCode = p.poll()
    threading.Timer(60*60, hourlyTask).start()

hourlyTask()

