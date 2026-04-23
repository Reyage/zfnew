# -*- coding: utf-8 -*-
"""
config.py - Global configuration for the zfnew educational system API.

This module stores shared constants used across the package:
  - Default student credentials template (STUDENT_INF)
  - The base URL for the educational management system (BASE_URL)
  - A mapping of named URL paths (URL_PATH_LIST)
  - The timetable mapping class period numbers to start/end times (CLASS_LIST)
"""

# Template for student login credentials.
# Fill in 'student ID' and 'password' before using the Login class.
STUDENT_INF = {
    'student ID': '',
    'password': ''
}

# Base URL of the educational management system.
# Change this to your school's system URL (e.g. 'http://jwc.yourschool.edu.cn/').
BASE_URL = 'http://jwc.xhu.edu.cn/'

# Named URL paths derived from BASE_URL.
# Extend this dict with additional route keys as new API endpoints are added.
URL_PATH_LIST = {
    'LOGIN_URL': BASE_URL,
    '': ''
}


# Class timetable (课程时间表)
# Each entry is [start_time, end_time] for a single 45-minute class period.
# Periods 1-2  : morning first block  (08:00-09:40)
# Periods 3-4  : morning second block (10:00-11:40)
# Periods 5-6  : afternoon first block (14:00-15:40)
# Periods 7-8  : afternoon second block (16:00-17:40)
# Periods 9-11 : evening block         (19:00-21:45)
CLASS_LIST = [
    ["8:00", "8:45"],    # Period 1
    ["8:55", "9:40"],    # Period 2
    ["10:00", "10:45"],  # Period 3
    ["10:55", "11:40"],  # Period 4
    ["14:00", "14:45"],  # Period 5
    ["14:55", "15:40"],  # Period 6
    ["16:00", "16:45"],  # Period 7
    ["16:55", "17:40"],  # Period 8
    ["19:00", "19:45"],  # Period 9
    ["19:55", "20:40"],  # Period 10
    ["21:00", "21:45"]   # Period 11
]
