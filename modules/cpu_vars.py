'''
Created on Apr 10, 2019

@author: thomasdre
@revised: sedanod 12/15/20
'''

import platform

## Computer Name
CPU_NAME = platform.node()

## Nielsen Logins (Username, Password)
DANIEL_LOGIN = ('daniel.sedano@umusic.com', '3a$xh6$Bz]@u*BzA')
#DREW_LOGIN = ('drew.thomas@umusic.com', '7AN9b!6iBMf!TtC')
#ZEE_LOGIN = ('zee@umusic.com', 'Capitol1750!!')


DREW_LOGIN = ('daniel.sedano@umusic.com', '3a$xh6$Bz]@u*BzA')
ZEE_LOGIN = ('daniel.sedano@umusic.com', '3a$xh6$Bz]@u*BzA')

CPU_DICT = {
    ## SuperWork
    'USLSAWL00193453':{
        'ff_binary_ptf':r"C:\Program Files\Mozilla Firefox\firefox.exe",
        'ff_profile_dir':r'C:\Users\SedanoD\AppData\Roaming\Mozilla\Firefox\Profiles',
        'ff_profile_name':'8j9umwty.default',
        'geckodriver_ptf':r'C:\geckodriver.exe',
        'default_download_folder':['C:\\', 'Users', 'SedanoD', 'Downloads'],
        'nielsen_credentials':[DANIEL_LOGIN, DREW_LOGIN, ZEE_LOGIN],
        'bypass':False
        },
    ## OldNew
    'USLSAWD00178103':{
        'ff_binary_ptf':r"C:\Program Files (x86)\R2FirefoxESR_60.7.2\firefox.exe",
        'ff_profile_dir':r'C:\Users\cmgreporting.sv\AppData\Roaming\Mozilla\Firefox\Profiles',
        'ff_profile_name':'jefclhkz.default',
        'geckodriver_ptf':r'C:\geckodriver.exe',
        'default_download_folder':['C:\\', 'Users', 'cmgreporting.sv', 'Downloads'], 
        'nielsen_credentials':[DANIEL_LOGIN, DREW_LOGIN, ZEE_LOGIN],
        'bypass':False
        },
    ## Main
    'USLSAWL00193194':{
        'ff_binary_ptf':r'C:\Program Files (x86)\R2FirefoxESR_60.7.2\firefox.exe',
        'ff_profile_dir':r'C:\Users\sedanod\AppData\Roaming\Mozilla\Firefox\Profiles',
        'ff_profile_name':'lpeb8t8a.default-release',
        'geckodriver_ptf':r'C:\Users\sedanod\Documents\geckodriver.exe',
        'default_download_folder':['C:\\', 'Users', 'sedanod', 'Downloads'],
        'nielsen_credentials':[DANIEL_LOGIN, DREW_LOGIN, ZEE_LOGIN],
        'bypass':False
        },
    ## Champ
    'USLSAWD00193134':{
        'ff_binary_ptf':r"C:\Program Files\Mozilla Firefox\firefox.exe",
        'ff_profile_dir':r'C:\Users\sedanod\AppData\Roaming\Mozilla\Firefox\Profiles',
        'ff_profile_name':'nbvh5y9n.default-release',
        'geckodriver_ptf':r'C:\Users\sedanod\Documents\geckodriver.exe',
        'default_download_folder':['C:\\', 'Users', 'sedanod', 'Downloads'],
        'nielsen_credentials':[ZEE_LOGIN, DANIEL_LOGIN, DREW_LOGIN],
        'bypass':True
        },
    ## SuperChamp
    'USLSAWD00193227':{
        'ff_binary_ptf':r"C:\Program Files\Mozilla Firefox\firefox.exe",
        'ff_profile_dir':r'C:\Users\sedanod\AppData\Roaming\Mozilla\Firefox\Profiles',
        'ff_profile_name':'uvxdr5bi.default-release',
        'geckodriver_ptf':r'C:\Users\sedanod\Documents\geckodriver.exe',
        'default_download_folder':['C:\\', 'Users', 'sedanod', 'Downloads'],
        #'nielsen_credentials':[DREW_LOGIN, DANIEL_LOGIN, ZEE_LOGIN],
        'nielsen_credentials':[DANIEL_LOGIN, DREW_LOGIN, ZEE_LOGIN],
        'bypass':True
        }
    }

## FireFox Variables
ff_binary_ptf = CPU_DICT[CPU_NAME]['ff_binary_ptf']
ff_profile_dir = CPU_DICT[CPU_NAME]['ff_profile_dir']
ff_profile_name = CPU_DICT[CPU_NAME]['ff_profile_name']

geckodriver_ptf = CPU_DICT[CPU_NAME]['geckodriver_ptf']
default_download_folder = CPU_DICT[CPU_NAME]['default_download_folder']

nielsen_credentials = CPU_DICT[CPU_NAME]['nielsen_credentials']
bypass_profile=CPU_DICT[CPU_NAME]['bypass']