'''
Created on Mar 28, 2018

@author: wennekt
'''

import shutil
import os
import datetime
import time
import week_tools as wt

bad_endings = ['crdownload', 'part', 'tmp']
bad_beginnings = ['~$']
time_out_default = 600

def join(*arg):
    p = ''
    for a in arg:
        if isinstance(a, str):
            p = os.path.join(p, a)
        else:
            for s in a:
                p = os.path.join(p, s)
    return p

def walk(maindir):
    ptfs = []
    for root, _, files in os.walk(maindir):
        for file in files:
            ptf = os.path.join(root, file)
            ptfs.append(ptf)
    return ptfs

def get_next_ptf(ptf, max_file_count=100, skip_first=False):
    fname = get_fname(ptf)
    fname_extent = get_extension(ptf)
    fname_base = fname[:-len(fname_extent)]
    parent_dir = get_parent_dir(ptf)
    num_digits = len(str(max_file_count - 1))
    if skip_first:
        n = 1
        ptf = join(parent_dir, fname_base + ' 01' + fname_extent)
    else:
        n = 0
        ptf = join(parent_dir, fname_base + fname_extent)
    while os.path.isfile(ptf) and n < max_file_count:
        ptf = join(parent_dir, fname_base + ' ' + str(n + 1).zfill(num_digits) + fname_extent)
        n += 1
    if n >= max_file_count:
        raise ValueError(max_file_count + ' reached at ' + ptf)
    return ptf

def make_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_parent_dir(ptf):
    return os.path.abspath(os.path.join(ptf, os.pardir))

def get_today_string():
    return wt.get_today_str()

def get_fname(ptf):
    return os.path.split(ptf)[1]

def get_extension(ptf):
    fname = get_fname(ptf)
    return '.' + fname.split('.')[-1]

def get_path(ptf):
    return os.path.split(ptf)[0]

def get_size(ptf):
    return os.path.getsize(ptf)

def file_exists(ptf, downloading=True):
    if downloading:
        start_time = time.time()
        fe_boo = True
        while fe_boo and time.time() - start_time < 2:
            fe_boo = os.path.isfile(ptf)
            if fe_boo:
                fe_boo = file_is_ok(ptf)
        return fe_boo
    else:
        return os.path.isfile(ptf)

def move(sptf, dptf):
    shutil.move(sptf, dptf)
    
def copy(s_ptf, d_ptf):
    shutil.copyfile(s_ptf, d_ptf)
    
def delete_ptf(ptf):
    while os.path.isfile(ptf):
        try:
            os.remove(ptf)
        except:
            pass
    
def get_date_modified(ptf):
    return os.path.getmtime(ptf)

def get_most_recent_ptf(directory):
    
    ptfs = walk(directory)
    mr_ptf = None
    mtime = None
    for ptf in ptfs:
        if file_is_ok(ptf):
            n_mtime = get_date_modified(ptf)
            if mtime is None or n_mtime > mtime:
                mr_ptf = ptf
                mtime = n_mtime

    return mr_ptf

def wait_for_file(ptf, time_max=time_out_default):
    whileboo = True
    start_time = time.time()
    while whileboo and (time.time() - start_time < (time_max / 2)):
        time.sleep(2)
        whileboo = not file_exists(ptf)
    if not whileboo:
        whileboo = True
        time.sleep(2)
        start_time = time.time()
        while whileboo and (time.time() - start_time < (time_max / 2)):
            whileboo = not file_exists(ptf)
    if whileboo:
        raise ValueError(ptf + ' not found')

def file_is_ok(ptf):
    fname = get_fname(ptf)
    file_ok = True
    for bad_ending in bad_endings:
            if ptf[-len(bad_ending):] == bad_ending:
                file_ok = False
    for bad_beginning in bad_beginnings:
        if fname[:len(bad_beginning)] == bad_beginning:
            file_ok = False
    if file_ok:
        try:
            file_ok = get_f_size(ptf) != 0
        except:
            file_ok = False
    return file_ok

def get_f_size(ptf):
    return os.path.getsize(ptf)

def wait_for_new_file(ptfs, search_dir):
    whileboo = True
    while whileboo:
        for ptf in walk(search_dir):
            if file_is_ok(ptf) and ptf not in ptfs:
                time.sleep(2)
                for ptf in walk(search_dir):
                    if file_is_ok(ptf) and ptf not in ptfs:
                        new_ptf = ptf
                        whileboo = False
    return new_ptf