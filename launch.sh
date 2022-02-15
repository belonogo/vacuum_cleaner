#!/bin/bash

sudo su
sudo python3 /home/pi/vacuum_cleaner/main.py > /home/pi/vacuum_cleaner/logs/output 2> /home/pi/vacuum_cleaner/logs/err
exit
