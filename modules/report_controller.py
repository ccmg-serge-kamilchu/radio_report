'''
Created on Nov 19, 2018

@author: wennekt
@revised: sedanod
'''

import sys
import datetime
import traceback
import time
import pandas as pd
import file_tools as ft
from thread_tools import Worker, Lock, thread

REPORTS = ['sybersound_tracking']
STATUS_LOG_DIR = r'G:\Reporting\Report Status Logs'
RE_RUN_INTERVAL_MINUTES = 5

def main():
    """
    Main function/ This fucntion will start the threads, initiate the locks, then run each report
    in a seperate thread. This function takes no argument but instead runs as many reports as are
    declared in the REPORTS list.
    """

    bw = Worker(2) # This controls how many firefox windows can be open at one time
    bw.start()
    '''
    read write lock for report status log which prevent
    things that have already run from running again
    '''
    rw_lock = Lock()
    excel_lock = Lock()
    email_lock = Lock()
    l = []
    for report in REPORTS:
        report = import_report(report)
        l.append([report, bw, rw_lock, excel_lock, email_lock])
    thread(run_report, l)
    bw.join()

def import_report(report):
    """
    Import the report module specified in the REPORTS list. First check to make
    sure that the Reporting folder containing the report modules is added to
    the PYTHONPATH. If it is not, then add it to the PYTHONPATH. Then check if
    the report is a valid report. If the report is contained in the report list
    then import the report module, otherwise throw an error.
    """
    # Path to report modules
    report_path = r"G:\Scripts\Reports"
    # Check to see if the Report Path in in the PYTHONPATH
    if report_path not in sys.path:
        sys.path.insert(1, report_path)
    # List of valid report modules
    report_list = [
        'a_r_hotlist',
        'apple_radio',
        'dma',
        'label_focus_tracks',
        'pitch_sheets',
        'radio_vs_sales', 
        'shipment', 
        'streaming',
        'caroline_streaming',
        'sybersound_tracking', 
        'project_tracking',
        'target_tracker',
        'capitol_top_sheet', 
        'a_r_daily', 
        'trackar_update', 
        'artist_one_sheet',
        'bq_focus_tracks', 
        'international_ar'
    ]
    # Is report in the report list, if it is then import it.
    if report in report_list:
        try:
            report = __import__(report)
            print('Imported {}'.format(report))
        # Else raise exception
        except ImportError as e:
            print("Unable to import {}, import returned error: {}".format(report, e))
    # Return imported module
    return report

def bw_func(bw, report, f_str, args=None, default_return=None):
    """
    Browser Worker Function. Execute a method function of the report module
    passed in the argumenets. Arguments are as follows:

    Report: report module, type: Python Module
    f_str : the method to be excecuted, type: str
    args  : The arguments to bbe passed into method function, type: list
    default_return: Object that is returned if the report does not have the
                    method being called.
    """
    # Check if report module has method f_str
    if eval('hasattr(report, f_str)'):
        return bw.func(eval('report.{}'.format(f_str)), args)
    else:
        return default_return

def run_report(report, bw, rw_lock, excel_lock, email_lock):
    """
    Run the report(s) specified in the REPORTS list. First check if the report
    already ran. If it hasnt then check to see if the data for the report is
    available. Finally, get the metadata song objects, report sets,download the
    data, format the excel files, then log and sleep. This function is passed
    to the threading funciton for every report that is called.
    """
    while True:
        # Set Default report status
        report_status = 'ran'

        # wait for start time
        """
        checks report staus log to see if report ran today if it has run
        then skips otherwise it will runn based on time set in report
        """
        nrt = get_next_run_time(report, rw_lock)
        time_delta = nrt - datetime.datetime.now()
        st = time_delta.total_seconds() #sleep time
        if st > 0:
            #print(report.REPORT_NAME, 'sleeping until', nrt, '-', time_delta)
            #time.sleep(st)
            print(report.REPORT_NAME, 'already ran. See logs.')
            break

            #time.sleep(st)
        print(report.REPORT_NAME, 'running', datetime.datetime.now())

        # try / except in order to release locks on fail
        try:

            # wait for latest data to arrive
            print(report.REPORT_NAME, 'checking data status')
            while not bw_func(bw, report, 'check_data_status', default_return=True):
                print(report.REPORT_NAME, 'data not ready yet')
            print(report.REPORT_NAME, 'data ready')

            # get objs
            print(report.REPORT_NAME, 'getting objs')
            objs = bw_func(bw, report, 'get_objs', default_return='no objs')

            # download data
            def download_data_switcher(bw, source_name, report_args):
                """
                Downloads data based on data source name given by the report
                sets dict. For Nielsen Connect Data first check that the reports
                have ran (connect_status). If they havent, then download the
                data. For other sources such as BigQuery ('bq') or Industry (DMA)
                download the data by calling the download_{source}_data method
                from the report module.
                """
                if source_name == 'connect':
                    while True:
                        connect_status = bw_func(bw, report, 'download_connect_data', args=report_args)
                        if connect_status == 'Error':
                            bw_func(bw, report, 'run_connect_report', args=report_args)
                        elif connect_status == 'Downloaded':
                            break
                        time.sleep(60 * 5)
                elif source_name in ['bq']:
                    exec('report.download_{}_data(*report_args)'.format(source_name))
                else:
                    bw_func(bw, report, 'download_{}_data'.format(source_name), args=report_args)
            print(report.REPORT_NAME, 'getting report sets')
            report_sets = report.get_report_sets(objs)
            print(report.REPORT_NAME, 'got report sets')
            thread_arg = []
            for source_name, report_set in report_sets.items():
                [thread_arg.append((bw, source_name, report_args)) for report_args in report_set]
            print(report.REPORT_NAME, 'downloading data')
            thread(download_data_switcher, thread_arg)

            # format excel
            print(report.REPORT_NAME, 'waiting for excel lock')
            excel_lock.acquire()
            print(report.REPORT_NAME, 'formatting excel')
            report.format_excel(report_sets, objs)
            print(report.REPORT_NAME, 'formatted excel')
            excel_lock.release()

    #         # send email
    #         print(report.REPORT_NAME, 'waiting for email lock')
    #         email_lock.acquire()
    #         print(report.REPORT_NAME, 'sending email')
    #         report.send_email()
    #         print(report.REPORT_NAME, 'sent email')
    #         email_lock.release()

        except Exception as e:
            print(traceback.format_exc())
            print(e)
            # On errors acquire and realease each lock
            for lock in [rw_lock, excel_lock, email_lock]:
                lock.acquire()
                lock.release()
            report_status = 'fail'
            time.sleep(120)
        # Log results of each run
        write_to_report_status_log(report, report_status, rw_lock)
        if report_status != 'ran':
            # On fail print out failure notice to the console and run again
            print(report.REPORT_NAME, 'failed. sleeping', RE_RUN_INTERVAL_MINUTES, 'minutes before trying again.')
            time.sleep(RE_RUN_INTERVAL_MINUTES* 60)
            run_report(report, bw, rw_lock, excel_lock, email_lock)
        # If successful print out a confirmation that the report ran
        print(report.REPORT_NAME, 'ran', datetime.datetime.now())

def get_next_run_time(report, lock):
    """
    Function used to get the next run time of the report based on the last
    time the report ran.
    """
    run_weekday = report.RUN_WEEKDAY
    run_time_tup = report.RUN_TIME
    run_time = datetime.time(run_time_tup[0], run_time_tup[1], 0, 0)
    now_dt = datetime.datetime.now()
    now_date = now_dt.date()
    now_weekday = now_date.weekday()
    days_add = run_weekday - now_weekday
    if days_add <= 0:
        days_add += 7
    target_date = now_date + datetime.timedelta(days=days_add)

    def get_last_run_date():
        """Get the most recent run time out of the log"""
        df = get_report_status_df(lock)
        df = df[df['report_name'] == report.REPORT_NAME]
        df = df[df['status'] == 'ran']
        i = df['datetime'].idxmax()
        df['datetime'] = df['datetime'].dt.date
        return df.at[i, 'datetime']

    if run_weekday == now_weekday:
        if get_last_run_date() != now_date:
            target_date = now_date
    return datetime.datetime.combine(target_date, run_time)

def write_to_report_status_log(report, report_status, lock):
    """ Writes report status to runtime log"""
    lock.acquire()
    df = get_report_status_df()
    new_df = pd.DataFrame([[datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), report.REPORT_NAME, report_status]], columns=['datetime', 'report_name', 'status'])
    df = pd.concat([df, new_df])
    ptf = ft.join(STATUS_LOG_DIR, 'report_status_log ' + ft.get_today_string() + '.txt')
    df.to_csv(ptf, index=False)
    lock.release()

def get_report_status_df(lock=None):
    """ Finds the most recent status of the report based on the logs"""
    if lock:
        lock.acquire()
    ptf = ft.get_most_recent_ptf(STATUS_LOG_DIR)
    df = pd.read_csv(ptf)
    df['datetime'] = pd.to_datetime(df['datetime'])
    if lock:
        lock.release()
    return df

if __name__ == '__main__':
    main()