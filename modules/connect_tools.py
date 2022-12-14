'''
Created on May 17, 2018

@author: cmgreporting.sv
'''

'''
older version of connect downloading, but still widely used throughout reporty
run_ranked_list, run_trend_report are key functions used by reporty
get_song_info, get_album_info, get_artist_info are key functions used by metadata (although metadata now uses these functions in connect_tools2)
'''

import download_tools as dt
import time
import file_tools as ft
import tabular_data as td
import week_tools as wt
import pandas as pd
import sqlite3 as sql
from datetime import datetime
from multiprocessing.dummy import Process, Lock
from queue import Queue, Empty
from cpu_vars import nielsen_credentials as nc
import os

nc = [[os.environ['USEREMAIL'], os.environ['USERPASS']]]

MAIN_DIR = r'G:\metadata_sql'
#url = 'https://mediaview.nielsen.com/mc/'
url = 'https://musicconnect.mrc-data.com'

def go_to_connect(browser, login_boo=True, glob=False):
    browser.get(url)
    if login_boo:
        login(browser)
    #dt.wait_for_item(browser, 'span', [('title', 'Billboard Top 200')], 'Billboard Top 200')
    dt.wait_for_item(browser, 'span', [('title', 'Billboard 200')])
    if glob:
        e = dt.get_es(browser, 'li', [('id', 'country-select-menu')])[0]
        dt.mouseover(browser, e)
        dt.get_es(browser, 'div', [('countrycode', 'G1')])[0].click()

def login(browser):
    ## Get Login Box
    login_box = dt.get_es(browser, 'div', [('class', "auth-content-inner")])[0]

    ## Write in UNM
    dt.wait_for_item(login_box, 'input', [('id', 'okta-signin-username')])
    unm_e = dt.get_es(login_box, 'input', [('id', 'okta-signin-username')])[0]
    dt.input_text(unm_e, nc[0][0], clear=False, enter=False)

    ## Write in Password
    pw_box = dt.get_es(browser, 'input', [('id', 'okta-signin-password')])[0]
    pw_box.send_keys(nc[0][1])

    ## hit enter
    pw_box.send_keys(dt.Keys.RETURN)
    browser.switch_to.default_content()

    # wait for page to appear
    es = dt.get_es(browser, 'input', [('type', 'search'), ('id', 'mc-home-search-textbox')], max_time=60)
    #time.sleep(10)
    if len(es) == 0:
        raise ValueError('Page Failed To Load On Time')
    
def get_contentmanager_df(browser=None, report_name=None, login_boo=True, glob=False, download_dir=dt.default_download_dir):
    def f(browser, login_boo):
        def get_row_es(browser, s=''):
            tbl = eval("dt.get_es{}(browser, 'div', [('class', 'x-panel cmRGrid x-panel-default x-grid')])".format(s))[0]
            return eval("dt.get_es{}(tbl, 'tr', [('class', '  x-grid-row')])".format(s))
        df = None
        st_main = time.time()
        while df is None and time.time() - st_main < 60:
            try:
                go_to_connect(browser, login_boo, glob)
                login_boo = False
                
                # go to content manager
                st = time.time()
                while len(get_row_es(browser, '_basic')) == 0 and time.time() - st < 10:
                    dt.get_es(browser, 'li', [('title', 'Content Manager')])[0].click()
                    try:
                        dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Refresh Inbox')[0].click
                        dt.get_es(browser, 'li', [('title', 'Dashboard')])[0].click
                        dt.get_es(browser, 'li', [('title', 'Content Manager')])[0].click
                        dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Refresh Inbox')[0].click
                    except:
                        pass
                if len(get_row_es(browser, '_basic')) == 0:
                    raise ValueError('Could not click to content manager')
        
                # get df
                st = time.time()
                while df is None and time.time() - st < 30:
                    try:
                        rows = []
                        row_es = get_row_es(browser)
                        today_date = wt.get_today_date().date()
                        submit_date = today_date
                        for row_e in row_es:
                            es = dt.get_es_basic(row_e, 'div', [('class', 'x-grid-cell-inner ')])
                            submit_date = datetime.strptime(es[2].text, '%m/%d/%Y %I:%M %p').date()
                            if submit_date == today_date:
                                row_report_name = es[0].text
                                if row_report_name == report_name[:len('Ariana Grande - Dangerous Woman 101150 201801-2018')]:
                                    status = es[1].text
                                    rows.append([es, row_report_name, status, submit_date])
                        if len(rows) == 0 and submit_date == today_date:
                            dt.get_es(browser, 'span', [('class', 'x-btn-icon-el x-btn-icon-el-default-toolbar-small x-tbar-page-next ')])[0].click()
                            raise ValueError('Could not find streaming on page.')
                        else:
                            df = pd.DataFrame(rows, columns=['es', 'row_report_name', 'status', 'submit_date'])
                    except:
                        pass
            except:
                pass
            
        if df is None:
            raise ValueError('Could not get content manager df.')
                
        return df
    
    if browser is None:
        def b():
            return dt.get_browser(download_dir=download_dir, file_extension='xlsx')
        return dt.try_until_success(f, b, login_boo)
    else:
        return f(browser, login_boo)
    
def get_cm_ptf(nielsen_report_name):
    return ft.join(r'G:\Connect Tools\Content Manager', '{} {}.csv'.format(nielsen_report_name, wt.get_today_str()))
    
def download_contentmanager_report(report_name, d_dir=dt.default_download_dir, f_ptf=None, login_boo=True, glob=False):
    def b():
        return dt.get_browser(download_dir=d_dir, file_extension='xlsx')
    def f(browser, login_boo):
        df = get_contentmanager_df(browser, report_name, login_boo, glob)
        
        # if it's not there, or they're all errors, error_boo = True
        status_l = list(df['status'])
        error_boo = True
        for status_i in status_l:
            if status_i != 'Error':
                error_boo = False
                break
            
        # if they're all 'Complete With No Data', return 'Complete With No Data'
        no_data_status_str = 'Complete With No Data'
        for status_i in status_l:
            if status_i == no_data_status_str:
                return no_data_status_str
                    
        # if not error, find any complete reports and hit export
        if not error_boo:
            df = df[df['status'] == 'Complete']
            if df.shape[0] > 0:
                es = df['es'].iloc[0]
                d_ptf = ft.join(d_dir, report_name[:len('Ariana Grande - Dangerous Woman 101150 201801-2018')] + '.xlsx')
                ft.delete_ptf(d_ptf)
                time.sleep(1)
                dt.get_es_basic(es[6], 'img', [('src', 'images/export3-XLS-16x.png')])[0].click()
                
                # wait for file
                ft.wait_for_file(d_ptf, time_max=30)
            
        if error_boo:
            return 'Error'
        if df.shape[0] == 0:
            return 'Timeout'
        if f_ptf:
            dt.move_downloaded_file(d_ptf, f_ptf)
        return 'Downloaded'
    if ft.file_exists(get_cm_ptf(report_name)):
        return dt.try_until_success(f, b, login_boo)
    else:
        return 'Error'

def export(browser):
    whileboo = True
    while whileboo:
        dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-toolbar-small'), ('data-ref', 'btnInnerEl')], 'Export')[0].click()
        try:
            dt.get_es(browser, 'span', [('class', 'x-menu-item-text x-menu-item-text-default x-menu-item-indent')], 'CSV')[0].click()
            whileboo = False
        except:
            pass
        
def download_industry_report(ptf, d_dir=dt.default_download_dir, industry_by='MARKETS'):
    def b():
        return dt.get_browser(d_dir, file_extension='plain')
    def f(browser):
        go_to_connect(browser)
        click_side_bar_item(browser, item_name='Industry Report')
        dt.get_es(browser, 'button', [('class', 'mc-industry-tab-button')], industry_by)[0].click()
        ptfs = ft.walk(d_dir)
        export(browser)
        new_ptf = ft.wait_for_new_file(ptfs, d_dir)
        ft.move(new_ptf, ptf)
    return dt.try_until_success(f, b)

def download_charts(chart_names, download_dir=dt.get_default_download_dir(), suffix=wt.get_this_we_str(), n=3):
    if not isinstance(chart_names, list):
        chart_names = [chart_names]
    if len(chart_names) > 0:
        lock = Lock()
        q = Queue()
        [q.put(chart_name) for chart_name in chart_names]
        def worker(q, lock):
            while True:
                try:
                    chart_name = q.get_nowait()
                except Empty:
                    break
                download_chart(chart_name, download_dir=download_dir, suffix=suffix, lock=lock)
        ps = [Process(target=worker, args=(q, lock)) for _ in range(min(len(chart_names), 3))]
        [p.start() for p in ps]
        [p.join() for p in ps]
        
def get_cleaned_chart_name(chart_name):
    return clean_text(chart_name, chars_to_remove='/', char_replace='')

def download_chart(chart_name, download_dir=dt.get_default_download_dir(), suffix=wt.get_this_we_str(), lock=None):
    chart_dir = r'G:\Connect Tools\Charts'
    cleaned_chart_name = get_cleaned_chart_name(chart_name)
    fname_base = 'Export_US_Chart - ' + cleaned_chart_name
    ptf = ft.join(chart_dir, '{} {}.csv'.format(cleaned_chart_name, wt.get_this_we_str()))
    def b():
        return dt.get_browser(download_dir=chart_dir, file_extension='plain')
    def f(browser, lock):
        go_to_chart(browser, chart_name)
         
        if lock is not None:
            lock.acquire()
         
        # delete possible files
        for d_ptf in ft.walk(chart_dir):
            fname = ft.get_fname(d_ptf)
            if fname[:len(fname_base)] == fname_base:
                ft.delete_ptf(d_ptf)
                 
        # get existing files
        prior_ptfs = ft.walk(chart_dir)
        export(browser)
         
        # pick up and rename file
        whileboo = True
        st = time.time()
        while whileboo and time.time() - st < 20:
            d_ptfs = ft.walk(chart_dir)
            for d_ptf in prior_ptfs:
                try:
                    d_ptfs.remove(d_ptf)
                except:
                    pass
            d_ptfs = [d_ptf for d_ptf in d_ptfs if ft.get_fname(d_ptf)[:len(fname_base)] == fname_base]
            for d_ptf in d_ptfs:
                if ft.file_exists(d_ptf):
                    ft.move(d_ptf, ptf)
                    whileboo = False
                    break
                    
        if lock is not None:
            lock.release()
            
        if whileboo:
            raise ValueError('Could not download {}'.format(chart_name))
    
    f_ptf = ft.join(download_dir, '{} {}.csv'.format(cleaned_chart_name, suffix))
    if not ft.file_exists(f_ptf):
        if not ft.file_exists(ptf):  
            dt.try_until_success(f, b, lock)
        ft.copy(ptf, f_ptf)
        
def go_to_chart(browser, chart_name='Billboard 200', wk=None, first=True, download_dir=None):
    
    default_chart = 'Billboard 200'
    
    if first: 
        # go to connect and login
        go_to_connect(browser)
        
    else: 
        browser.execute_script('window.history.go(-1)')
        time.sleep(1)
        browser.switch_to.default_content()
        
    # go to charts
    ## Bypass because Nielsen is Being whack (11/10/20)
    #es = dt.get_es(browser, 'span', [('title', 'Billboard Top 200')], 'Billboard Top 200')
    #dt.click_until_success(es, repeat=True)
    
    # open Chart
    click_side_bar_item(browser, item_name='Charts')
    
    try:
        # wait
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')], appear=False)
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')])

    except ValueError:
        browser.close()
        browser = dt.get_browser(download_dir=download_dir, bypass_profile=True)
        go_to_connect(browser)
        ## Whack Nielsen (11/10/20)
        #es = dt.get_es(browser, 'span', [('title', 'Billboard Top 200')], 'Billboard Top 200')
        #dt.click_until_success(es, repeat=True)
        # open Chart
        click_side_bar_item(browser, item_name='Charts')
                
        # wait
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')], appear=False)
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')])

    # click dropdown
    if chart_name != default_chart:
        charts_header = dt.get_es(browser, 'div', [('class', 'x-field mc-billboard-chart-combo x-form-item x-form-item-default x-form-type-text x-box-item x-field-default x-hbox-form-item x-form-dirty')])[0]
        
        try:
            dt.get_es(charts_header, 'div', [('class', 'x-form-trigger x-form-trigger-default x-form-arrow-trigger x-form-arrow-trigger-default  ')])[0].click()
        except:
            dt.get_es(charts_header, 'div', [('id', "nielsenCombo-1228-trigger-picker")])[0].click()
        
        # click chart
        dt.get_es(browser, 'li', [('class', 'chart-list-item ')], chart_name)[0].click()
        
        # wait for chart to load
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')], appear=False)
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')])
    
    # go to week
    if wk:
        calendar = get_chart_calendar(browser)
        click_to_calendar_wk(calendar, wk)
    
        # wait for chart to load
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')], appear=False)
        dt.wait_for_item(browser, 'div', [('class', 'bill_board_template_table_anm')])

    return browser

def parse_ids(strings=list):
    ids=[]
    for string in strings: 
        split = string.split(', ')[1:]
        i = 0
        x = split[i]
        flag = True
        while flag:
            try:
                if len(x) < 8:
                    raise ValueError
                else:
                    int(x[3])
                    ids.append(x)
                    flag = False
            except:
                i += 1
                x = split[i]
                flag=True
    return(ids)


def get_chart_d(charts = list, download_dir=None):
    chart_d = {}
    for n, chart in enumerate(charts): 
        if n==0: 
            browser = dt.get_browser(download_dir=download_dir, bypass_profile=True)
            go_to_chart(browser, chart_name=chart, first=True)
        else: 
            browser = go_to_chart(browser, chart, first=False, download_dir=download_dir)

        flag = True
        while flag:
            try:
                table = dt.get_es(browser, 'div', [('id', 'tableview-1240')])[0]
                flag = False
            except: 
                flag = True
                browser.close()
                browser = dt.get_browser()
                go_to_chart(browser, chart_name=chart)

        entries = dt.get_es(table, 'table', [('role', 'presentation')])[0:50]

        strings = []
        for entry in entries:
            strings.append(dt.get_es(entry, 'div', [('class', 'bill_board_template_table_cnm')])[0].find_element_by_css_selector('a').get_attribute('onclick'))

        ids = parse_ids(strings)
        chart_d[chart] = ids

        export(browser)

        if n == len(charts)-1:
            time.sleep(3)

    browser.close()
    return chart_d
    
def get_chart_calendar(browser):
    calendar_box = dt.get_es(browser, 'span', [('class', 'x-btn-icon-el x-btn-icon-el-default-small fa fa-calendar ')])[0]
    calendar_box.click()
    return dt.get_es(browser, 'div', [('class', 'x-datepicker x-layer x-datepicker-default x-unselectable x-border-box')])[0]
    
def get_current_wk(browser=None):
    date_dir = r'G:\Connect Tools\Connect Date'
    df = pd.read_csv(ft.get_most_recent_ptf(date_dir))
    wk = wt.Week(tup=(df.at[0, 'year'], df.at[0, 'week']))
    if wk == wt.get_this_wk(): 
        return wk
    def func(browser):
        get_page(browser, item_id='6958763', content_type='Album')
        date_str = dt.get_es(browser, 'span', [('class', 'week-selector-date dashboard_perf_date')])[0].text
        d = datetime.strptime(date_str, '%m/%d/%Y')
        return wt.Week(d=d)
    if browser:
        bb_wk = func(browser)
    else:
        bb_wk = dt.try_until_success(func, dt.get_browser)
    df = pd.DataFrame([[bb_wk.year, bb_wk.week]], columns=['year', 'week'])
    df.to_csv(ft.join(date_dir, 'connect_date ' + wt.get_today_str() + '.csv'), index=False)
    return bb_wk
    
def get_current_wk_bb200(browser=None):
    date_dir = r'G:\Connect Tools\Connect Date'
    df = pd.read_csv(ft.get_most_recent_ptf(date_dir))
    wk = wt.Week(tup=(df.at[0, 'year'], df.at[0, 'week']))
    if wk == wt.get_this_wk(): 
        return wk
    def func(browser):
        go_to_chart(browser)
        calendar = get_chart_calendar(browser)
        return get_current_wk_with_calendar(calendar)
    if browser:
        bb_wk = func(browser)
    else:
        bb_wk = dt.try_until_success(func, dt.get_browser)
    df = pd.DataFrame([[bb_wk.year, bb_wk.week]], columns=['year', 'week'])
    df.to_csv(ft.join(date_dir, 'connect_date ' + wt.get_today_str() + '.csv'), index=False)
    return bb_wk
    
def click_template(pop, template_name):
    whileboo = True
    start_time = time.time()
    while whileboo and time.time() - start_time < 4:
        try:
            dt.get_es(pop, 'div', [('class', 'x-grid-cell-inner ')], template_name)[0].click()
            whileboo = False
        except:
            pass
    if whileboo:
        raise ValueError('Could not click template: ' + template_name)
    return not whileboo

def run_ranked_list(browser=None, template_name=None, template_is_shared=False, dynamic_dates=None, wk0=None,wkf=None, report_name=None, release_age=None, market_share_group=None, genres=None, is_core_genre=True, d_dir=None, f_ptf=None, open_ranked_list=True):

    def b():
        return dt.get_browser(download_dir=d_dir, file_extension='xlsx')
    
    def f(browser):
    
        if open_ranked_list:
            
            # go to connect
            go_to_connect(browser)
            
            # open ranked list
            click_side_bar_item(browser, item_name='Ranked List')
            
            # wait to load
            es = dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Refresh')
            dt.click_until_success(es, True)
            
        # load template
        if template_name:
            load_template(browser, template_name, template_is_shared)
            
        # rank by options
        rank_by_e = dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl')], 'Rank By Options')[0] 
        rank_by_e.click()
        e = dt.get_es(browser, 'span', [('class', 'x-form-item-label-inner x-form-item-label-inner-default')], 'Top:')[0]
        e = dt.get_parent(e)
        e = dt.get_parent(e)
        e = dt.get_es(e, 'input')[0]
        rank_count = int(dt.get_attribute(e, 'aria-valuenow'))
        if rank_count < 501:
            dt.input_text(e, '501', clear=True)
            e.send_keys(dt.Keys.RETURN)
        rank_by_e.click()
        
        # choose dates
        if dynamic_dates or (wk0 and wkf):
                     
            # set calendar once, so it doesn't revert to original
            calendar_box = dt.get_es(browser, 'div', [('class', 'mc-field-value')], 'Calendar')[0]
            while dt.get_attribute(calendar_box, 'class') != 'mc-button-wrapper mc-rounded-border':
                calendar_box = dt.get_parent(calendar_box)
            calendar_box.click()
            dt.get_es_basic(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Last Chart Week')[0].click()
            calendar_box.click()
            time.sleep(1)
            calendar_box.click()
            dt.get_es_basic(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Last Chart Week')[0].click()
            calendar_box.click()
                 
            # choose dynamic dates
            if dynamic_dates:
                calendar_box.click()
                dt.get_es_basic(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], dynamic_dates)[0].click()
                calendar_box.click()
                     
            # choose static dates
            elif wk0 and wkf:
                while dt.get_es(calendar_box, 'div', [('data-ref', 'displayValueEl'), ('class', 'mc-display-value')])[0].text != wk0.get_wb_date(True).strftime('%m/%d/%Y') + ' - ' + wkf.we_date.strftime('%m/%d/%Y'):

                    # open calendar
                    calendar_box.click()

                    # get calendars
                    calendars = dt.get_es(browser, 'div', [('class', 'x-datepicker x-box-item x-datepicker-default x-unselectable')])
                    calendars = [(calendars[0], wk0), (calendars[1], wkf)]

                    # for each calendar, click on week
                    for calendar, wk in calendars:
                        for calendar, wk in calendars: 
                            def scroll_and_click_calendar(calendar, wk):
                                n=0
                                while (get_wk_0(calendar) > wk):
                                    #print(n, "Registering:", get_wk_0(calendar), 'Target:', wk , 'id:', calendar.id)
                                    dt.get_es(calendar, 'div', [('title', 'Previous Month (Control+Left)')])[0].click()
                                    time.sleep(0.5)
                                    n+=1
                                # choose week
                                wk_rows = dt.get_es(calendar, 'tr', [('role', 'row')])
                                whileboo = True
                                n = 1
                                while whileboo and n < len(wk_rows):
                                    wk_row = wk_rows[n]
                                    wk_button = get_wk_button(wk_row)
                                    #print(wk_button.text, str(wk.week))
                                    if wk_button.text == str(wk.week):
                                        wk_button.click()
                                        whileboo = False
                                    n += 1
                                if whileboo:
                                    raise ValueError('Week {} not available on calendar'.format(wk.week))
                                return wk_button.text

                            wk_string = ''
                            while wk_string != str(wk.week):
                                wk_string = scroll_and_click_calendar(calendar, wk)

                        # if timespan warning appears, click ok
                        try:
                            dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'OK', max_time=2)[0].click()
                        except:
                            pass
                    calendar_box.click()
                
        # change report name
        if report_name:
            change_report_name(browser, report_name, 'Ranked List')
            use_report_name = report_name
        else:
            get_report_name_e(browser).click()
            e = dt.get_es(browser, 'div', [('class', 'x-field rounded x-form-item x-form-item-default x-form-type-text x-form-dirty x-field-default x-autocontainer-form-item')])[0]
            e = dt.get_es(e, 'input', [('class', 'x-form-field x-form-text x-form-text-default  ')])[0]
            use_report_name = dt.get_attribute(e, 'value')
            
        # change release age
        if release_age:
            release_age_e = dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl')], 'Release Age')[0]
            release_age_parent_e = dt.get_parent(release_age_e)
            max_attempts = 10
            n = 0
            whileboo = True
            while whileboo and n < max_attempts:
                n += 1
                release_age_e.click()
                pop = dt.get_es(browser, 'div', [('class', 'x-grid-view x-fit-item x-grid-view-default x-unselectable x-focus x-grid-view-focus x-grid-view-default-focus')])[0]
                e = dt.get_es(pop, 'div', [('class', 'x-grid-cell-inner ')], release_age)[0]
                e.click()
                click_page_title(browser, 'Ranked List')
                release_age_name_e = dt.get_es(release_age_parent_e, 'div', [('data-ref', 'displayValueEl')])[0]
                whileboo = release_age_name_e.text != release_age
            if whileboo:
                raise ValueError('Could not change release age.')
            
        # change labels
        if market_share_group:
            market_share_e = dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl')], 'Market Share Group')[0]
            market_share_parent_e = dt.get_parent(market_share_e)
            max_attempts = 10
            n = 0
            whileboo = True
            while whileboo and n < max_attempts:
                n += 1
                market_share_e.click()
                top_e = dt.get_es(browser, 'span', [('class', 'x-tree-node-text ')], 'All')[0]
                div_e = dt.get_parent(top_e)
                while dt.get_tag(div_e) != 'div' or dt.get_attribute(div_e, 'class') != 'x-grid-item-container':
                    div_e = dt.get_parent(div_e)
                for e in dt.get_es(div_e, 'span', [('class', 'x-tree-node-text ')]):
                    txt = e.text
                    e.click()
                    if txt == market_share_group:
                        break
                click_page_title(browser, 'Ranked List')
                market_share_name_e = dt.get_es(market_share_parent_e, 'div', [('data-ref', 'displayValueEl')])[0]
                whileboo = market_share_name_e.text != market_share_group
            if whileboo:
                raise ValueError('Could not change market share group.')
            
        # change genre
        if genres:
            box_es = dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl')], 'Genre', max_time=2)
            box_es.extend(dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl')], 'Core Genre', max_time=2))
            dt.click_until_success(box_es, repeat=True)
            dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'Core Genre')[0].click()
            dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'Genre')[0].click()
            if is_core_genre:
                dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'Core Genre')[0].click()
            if type(genres) is list:
                use_genres = genres
            if type(genres) is not list:
                use_genres = [genres]
            pop = dt.get_es(browser, 'div', [('class', 'x-panel mc-filter-popup mc-ranked-list-filter-popup x-grid-header-hidden x-layer x-panel-default x-grid x-border-box')])[0]
            rows = dt.get_es(pop, 'tr', [('role', 'row')])
            num_rows = len(rows)
            dt.get_es(rows[0], 'div', [('class', 'x-grid-row-checker')])[0].click()
            rows = dt.get_es(pop, 'tr', [('role', 'row')])
            for n in range(num_rows):
                rows = dt.get_es(pop, 'tr', [('role', 'row')])
                row_text = dt.get_es(rows[n], 'div', [('class', 'x-grid-cell-inner ')])[1].text
                for genre in use_genres:
                    if genre == row_text:
                        rows = dt.get_es(pop, 'tr', [('role', 'row')])
                        dt.get_es(rows[n], 'div', [('class', 'x-grid-row-checker')])[0].click()
                        break
            dt.click_until_success(box_es, repeat=True)
    
        # run
        dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Run Report')[0].click()
        try:
            dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'Close')[0].click()
        except:
            pass
        
        # pick up
        if d_dir and f_ptf:
            dt.open_new_window(browser, url)
            download_contentmanager_report(browser, use_report_name, d_dir, f_ptf, login_boo=False)
            
        pd.DataFrame([['launched']]).to_csv(get_cm_ptf(use_report_name), index=False)
            
    if browser:
        f(browser)
    else:
        dt.try_until_success(f, b)
    

def run_trend_report(template_name=None, template_is_shared=False, trends_by=None, item_ids=None, dynamic_dates=None, wk0=None, wkf=None, report_name=None, d_ptf=None, f_ptf=None, d_dir=dt.default_download_dir, open_trend_reports=True, glob = False, return_df=False, scrape = False, report=None):

    def b():
        if d_ptf:
            use_d_dir = ft.get_parent_dir(d_ptf)
        else:
            use_d_dir = d_dir
        return dt.get_browser(download_dir=use_d_dir, file_extension='xlsx')

    def f(browser):

        if open_trend_reports:
           
            # go to connect
            go_to_connect(browser, glob=glob)
            
            # open trend streaming
            click_side_bar_item(browser, 'Trend Report')
                    
            # wait to load
            es = dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Refresh')
            dt.click_until_success(es, True)
                
        # load template
        if template_name:
            load_template(browser, template_name, template_is_shared)
                
        # choose ids
        if item_ids:
            use_item_ids = clean_text(item_ids)
            use_item_ids = set(item_ids)
            es = dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl')], 'Trends By')
            dt.click_until_success(es, repeat=True)
            if template_name: 
                dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-toolbar-small')], 'Options')[0].click()
                dt.get_es(browser, 'span', [('class', 'x-menu-item-text x-menu-item-text-default x-menu-item-indent')], 'Clear All')[0].click()
            if trends_by:
                es = dt.get_es(browser, 'input', [('class', 'x-form-field x-form-text x-form-text-default  '), ('role', 'combobox')])
                whileboo = True
                n = 0
                while whileboo and n < len(es):
                    combo_box = es[n]
                    n += 1
                    try:
                        combo_box.clear()
                        whileboo = False
                    except:
                        pass
                if whileboo:
                    raise ValueError('Could not get trends by combo box.')
                dt.input_text(combo_box, trends_by)
            es = dt.get_es(browser, 'input', [('class', 'x-form-field x-form-text x-form-text-default  '), ('role', 'textbox')])
            whileboo = True
            n = 0
            while whileboo and n < len(es):
                search_bar = es[n]
                n += 1
                try:
                    search_bar.clear()
                    whileboo = False
                except:
                    pass
            if whileboo:
                raise ValueError('Could not get search bar.')

        # Fill out report..
        md = []
        bad_ids = []
        counter_e = dt.get_es(browser, 'label', [('class', 'x-component x-box-item x-toolbar-item x-component-default')], 'Selected Items (0)')[0]
        last_item_text = ('str', 'str', 'str')
        ## Functions for Scraping
        def get_pos_items(browser):
            pos_items_box = dt.get_es(browser, 'div', [('class', 'x-container x-box-item x-container-default x-border-layout-ct')])[0]
            return dt.get_es_basic(pos_items_box, 'tr', [('class', '  x-grid-row'), ('role', 'row')])
        def scrape_tr_new(browser):
            track = dt.get_es(browser, 'div', [('class', 'x-grid-item-container'), ('role', 'presentation'), ('style', 'width: 756px; transform: translate3d(0px, 0px, 0px);')])[0].text
            if track == '':
                return track
            else: 
                try:
                    return track.split('\n')[1], track.split('\n')[2]
                except:
                    return track.split('\n')[1]
        '''        
        def get_item_text(e):
            grid_cells = dt.get_es(e, 'td', [('role', 'gridcell')])
            if len(grid_cells) > 3: 
                return (grid_cells[2].text, grid_cells[3].text, grid_cells[4].text)
            else: 
                return (grid_cells[0].text, grid_cells[1].text, grid_cells[2].text)
        '''
        def get_item_text(e):
            grid_cells = dt.get_es(e, 'td', [('role', 'gridcell')])
            if len(grid_cells) > 3: 
                if len(grid_cells) == 4:
                    return (grid_cells[1].text, grid_cells[2].text, grid_cells[3].text)
                else:
                    return (grid_cells[2].text, grid_cells[3].text, grid_cells[4].text)
            else: 
                return (grid_cells[0].text, grid_cells[1].text, grid_cells[2].text)

        ## Fill Out Report        
        for n, item_id in enumerate(use_item_ids):
            # Clear Search Bar
            search_bar.clear()
            dt.input_text(search_bar, item_id)
            st = time.time()
            whileboo = True
            while whileboo and time.time() - st < 15:
                try:
                    item_e = get_pos_items(browser)[0]
                    whileboo = last_item_text == get_item_text(item_e)
                    last_item_text = get_item_text(item_e)
                    duplicate_flag = False
                except:
                    duplicate_flag = True
                    pass
            # Get Info
            track_info = scrape_tr_new(browser)
            skip_flag = track_info == '' or duplicate_flag
            if not skip_flag:
                md.append((item_id[1:], track_info))
                dt.get_es(item_e, 'div', [('class', 'x-grid-row-checker')])[0].click()
                dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-toolbar-small')], 'Add to Selected')[0].click()
                st = time.time()
                whileboo = True
                while whileboo and time.time() - st > 15:
                    whileboo = counter_e.text != 'Selected Items ({})'.format(len(md)) 
            else:
                print('Could not select id: {}, moving on to next id...'.format(item_id[1:]))
                bad_ids.append(item_id[1:])
                pass
        if scrape: 
            ## Send ids to SQL Database
            if len(md) > 0:
                #print(pd.DataFrame(md, columns = ['Nielsen_ID', 'Song_Info']))
                append_data(pd.DataFrame(md, columns = ['Nielsen_ID', 'Song_Info']), report=report)
                print("Nielsen Maps Updated! {} entries added.".format(len(md)))
                
        ## Send Bad Ids to Database? 
        if (len(bad_ids) > 0):
            print('Sending bad ids to database...')
            ids_df = pd.DataFrame(bad_ids, columns =['Bad_Ids'])
            ids_df['Report'] = report
            ids_df['Week'] = str(wt.get_this_wk())
            conn = sql.connect('G:\\metadata_sql\\nielsen_maps_fixed.db')
            ids_df.to_sql('bad_nielsen_ids', conn, if_exists = 'append', index=False)
            print('Bad ids sent to database!')
            conn.close()
            
        ## Apply Changes to Trend Report
        dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-toolbar-small')], 'Apply')[0].click()
                
        # choose dates
        if dynamic_dates or (wk0 and wkf):
                     
            # set calendar once, so it doesn't revert to original
            calendar_box = dt.get_es(browser, 'div', [('class', 'mc-field-value')], 'Calendar')[0]
            while dt.get_attribute(calendar_box, 'class') != 'mc-button-wrapper mc-rounded-border':
                calendar_box = dt.get_parent(calendar_box)
            calendar_box.click()
            dt.get_es_basic(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Last Chart Week')[0].click()
            calendar_box.click()
            time.sleep(1)
            calendar_box.click()
            dt.get_es_basic(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Last Chart Week')[0].click()
            calendar_box.click()
                 
            # choose dynamic dates
            if dynamic_dates:
                calendar_box.click()
                dt.get_es_basic(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], dynamic_dates)[0].click()
                calendar_box.click()
                     
            # choose static dates
            elif wk0 and wkf:
                
                while dt.get_es(calendar_box, 'div', [('data-ref', 'displayValueEl'), ('class', 'mc-display-value')])[0].text != wk0.get_wb_date(True).strftime('%m/%d/%Y') + ' - ' + wkf.we_date.strftime('%m/%d/%Y'):
                
                    # open calendar
                    calendar_box.click()
                             
                    # get calendars
                    calendars = dt.get_es(browser, 'div', [('class', 'x-datepicker x-box-item x-datepicker-default x-unselectable')])
                    calendars = [(calendars[0], wk0), (calendars[1], wkf)]
                             
                    # for each calendar, click on week
                    for calendar, wk in calendars:
                        click_to_calendar_wk(calendar, wk)
                                 
                        # if timespan warning appears, click ok
                        try:
                            dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'OK', max_time=2)[0].click()
                        except:
                            pass
                    calendar_box.click()
                
        # change report name
        if report_name:
            use_report_name = report_name
            change_report_name(browser, use_report_name, 'Trend Report')
        else:
            get_report_name_e(browser).click()
            e = dt.get_es(browser, 'div', [('class', 'x-field rounded x-form-item x-form-item-default x-form-type-text x-form-dirty x-field-default x-autocontainer-form-item')])[0]
            e = dt.get_es(e, 'input', [('class', 'x-form-field x-form-text x-form-text-default  ')])[0]
            use_report_name = dt.get_attribute(e, 'value')
            click_page_title(browser, 'Trend Report')
                
        # run
        run_button = dt.get_es(browser, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Run Report')[0]
        while dt.get_attribute(run_button, 'role') != 'button': 
            run_button = dt.get_parent(run_button)
        dt.mouseover(browser, run_button)
        run_button.click()
        time.sleep(2)
        try:
            dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'OK')[0].click()
        except:
            pass
        time.sleep(2)
        try:
            dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'Close')[0].click()
        except:
            pass
        
        # wait for chart to appear in content manager
        while True:
            df = get_contentmanager_df(report_name=use_report_name, glob=glob)
            if df.shape[0] > 0:
                break
            else:
                raise ValueError('{} never appeared'.format(use_report_name))
                      
        # download from content manager
        if f_ptf:
            dt.open_new_window(browser, url)
            whileboo = True
            while whileboo:
                if d_ptf:
                    use_d_dir = ft.get_parent_dir(d_ptf)
                else:
                    use_d_dir = d_dir
                dcmr = download_contentmanager_report(use_report_name, use_d_dir, f_ptf)
                if dcmr == 'Error':
                    raise ValueError('Report error.')
                elif dcmr == 'Downloaded':
                    whileboo = False
            if return_df:
                return td.get_df(f_ptf)
            
        pd.DataFrame([['launched']]).to_csv(get_cm_ptf(use_report_name), index=False)
            
    return dt.try_until_success(f, b)


def append_data(data, report):
    if report == 'Zee':
        table = 'isrcs'
    else:
        table ='data'
    ## SQL Connection
    flag = True
    while flag:
        try:
            conn = sql.connect(ft.join(MAIN_DIR, 'nielsen_maps_fixed.db'))
            flag = False
        except: 
            time.sleep(1)
            flag = True
    ## Get SQL Dataframe
    sql_df = pd.read_sql("SELECT * FROM {}".format(table), conn)
    ## Data Types and Index 
    data['Nielsen_ID'] = data['Nielsen_ID'].astype(str)
    data['Song_Info'] = data['Song_Info'].astype(str)
    index = data['Nielsen_ID'].apply(lambda x: x not in list(sql_df['Nielsen_ID']))
    if len(index) > 0:
        data[index].copy().reset_index(drop=True).to_sql(table, conn, if_exists='append')
        conn.commit()
    conn.close()

'''
## Old Function
def get_nielsen_maps():
    conn = sql.connect(r"G:\metadata_sql\nielsen_maps_fixed.db")
    nielsen_maps = pd.read_sql("SELECT * FROM data;", conn)
    conn.close()

    nielsen_maps['Song_Info'] = nielsen_maps['Song_Info'].map(eval)
    nielsen_maps['Song'] = nielsen_maps['Song_Info'].apply(lambda x: x[0])
    nielsen_maps['Artist'] = nielsen_maps['Song_Info'].apply(lambda x: x[1])
    
    return nielsen_maps.drop(columns=['Song_Info', 'index'])
'''

## New Function
def get_nielsen_maps(artist=False, report='default'):
    if report == 'Zee':
        table = 'isrcs'
    else:
        table ='data'
    ## Get data from database
    with sql.connect(r"G:\metadata_sql\nielsen_maps_fixed.db") as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM {};'.format(table)
        cursor.execute(query)
        scraped_entries = cursor.fetchall()

    ## Results to Df
    results_df = pd.DataFrame.from_records(scraped_entries, columns = ['index', 'Nielsen_ID', 'Song_Info'])
    try:
        results_df['Nielsen_ID'] =  results_df['Nielsen_ID'].map(float).map(int).map(str)
        results_df.drop_duplicates(inplace=True)
    except:
        pass
    if len(results_df) == 0:

        return results_df.drop(columns=['Song_Info', 'index'])  
    
    def tryeval(x):
        try:
            eval(x)
        except:
            return False
        return True
    artist_index = results_df['Song_Info'].apply(lambda x: tryeval(x))
    if artist:
        nielsen_maps = results_df[~artist_index].copy()
        nielsen_maps['Artist'] = results_df['Song_Info']
    else:
        nielsen_maps = results_df[artist_index].copy()
        nielsen_maps['Song_Info'] = nielsen_maps['Song_Info'].map(eval)
        class_index = nielsen_maps['Song_Info'].apply(lambda x: isinstance(x, tuple))
        nielsen_maps = nielsen_maps[class_index].reset_index(drop=True)
        nielsen_maps['Song'] = nielsen_maps['Song_Info'].apply(lambda x: x[0])
        nielsen_maps['Artist'] = nielsen_maps['Song_Info'].apply(lambda x: x[1]) 

    return nielsen_maps.drop(columns=['Song_Info', 'index'])

def clear_db(db, table):
    
    conn = sql.connect(ft.join(MAIN_DIR, '{}.db'.format(db)))
    clear = "DELETE FROM {};".format(table)
    cursor = conn.cursor()
    cursor.execute(clear)
    conn.commit()
    conn.close()

    print('Database Cleared!')

def chunker(l, n):
    return [('{}-{}'.format(i+1,min(i+n,len(l))), l[i:i+n]) for i in range(0, len(l), n)]

def click_side_bar_item(browser, item_name):
    e = dt.get_es(browser, 'div', [('id', 'leftNavGroupsContainer')])[0]
    dt.mouseover(browser, e)
    dt.get_es(browser, 'div', [('class', 'navItems-text')], item_name)[0].click()
        
def load_template(browser, template_name, template_is_shared):
    
    es = dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'Template')
    dt.click_until_success(es, repeat=True)
    dt.get_es(browser, 'span', [('data-ref', 'textEl')], 'Load Template')[0].click()
    pop = dt.get_es(browser, 'div', [('class', 'x-window trendTemplatePopup x-layer x-window-default x-closable x-window-closable x-window-default-closable x-border-box x-resizable x-window-resizable x-window-default-resizable')])[0]
    if template_is_shared:
        shared_start_time = time.time()
        shared_whileboo = True
        while shared_whileboo and time.time() - shared_start_time < 25:
            dt.get_es(pop, 'span', [('class', 'x-btn-inner x-btn-inner-default-small')], 'Shared')[0].click()
            try:
                shared_whileboo = not click_template(pop, template_name)
            except:
                pass
        if shared_whileboo:
            raise ValueError('Could not toggle to shared reports')
    else:
        click_template(pop, template_name)
    dt.get_es(browser, 'span', [('data-ref', 'btnInnerEl')], 'Apply')[0].click()
    
    # wait until loaded
    dt.get_es(browser, 'div', [('class', 'mc-field-value')], 'Report Name/Schedule')
    dt.click_until_success(es, repeat=True)
    dt.click_until_success(es, repeat=True)
    

def get_report_name_e(browser):
    report_box = dt.get_es(browser, 'div', [('class', 'mc-field-value')], 'Report Name/Schedule')[0]
    report_box = dt.get_parent(report_box)
    return dt.get_es(report_box, 'div', [('data-ref', 'displayValueEl')])[0]
        
def change_report_name_old(browser, report_name, report_type):
    
    name_e = get_report_name_e(browser)
    box_es = dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl'), ('class', 'mc-field-value')], 'Report Name/Schedule')
    dt.click_until_success(box_es, repeat=True)
    report_name_line = dt.get_es(browser, 'div', [('class', 'x-field rounded x-form-item x-form-item-default x-form-type-text x-form-dirty x-field-default x-autocontainer-form-item')])[0]
    es = dt.get_es(report_name_line, 'input', [('data-ref', 'inputEl')])
    for e in es:
        try:
            e.clear()
            break
        except:
            pass
    dt.click_until_success(box_es, repeat=True)
    whileboo = True
    start_time = time.time()
    while whileboo and time.time() - start_time < 15:
        dt.click_until_success(box_es, repeat=True)
        e.clear()
        e.send_keys(report_name)
        time.sleep(1)
        click_page_title(browser, report_type)
        num_chars = len('Total Under Review DanceEl')
        whileboo = name_e.text[:num_chars] != report_name[:num_chars]
    if whileboo:
        raise ValueError('Could not change streaming name.')
    
def change_report_name(browser, report_name, report_type):
    name_e = get_report_name_e(browser)
    current_name = name_e.text
    num_chars = len('Total Under Review DanceEl')
    if current_name[:num_chars] != report_name[:num_chars]:
        box_e = dt.get_es(browser, 'div', [('data-ref', 'fieldValueEl'), ('class', 'mc-field-value')], 'Report Name/Schedule')[0]
        while dt.get_attribute(box_e, 'data-ref') != 'btnWrap':
            box_e = dt.get_parent(box_e)
        box_e.click()
        #print(f'Current Report Name: {current_name}')
        input_e = dt.get_es(browser, 'input', [('value', current_name)])[0]
        dt.input_text(input_e, txt=report_name, clear=True, enter=True)
        click_page_title(browser, report_type)
        change_report_name(browser, report_name, report_type)
    
def click_page_title(browser, report_type):
    dt.get_es(browser, 'label', [('class', 'x-component ranked-list-title x-box-item x-component-default')], report_type)[0].click()
    
def click_to_calendar_wk(calendar, wk):
    
    # if week is past latest available, change to latest available
    wk = min(get_current_wk(), wk)
    
    # click left until first week is less than week we want
    while get_wk_0(calendar) > wk:
        dt.get_es(calendar, 'div', [('title', 'Previous Month (Control+Left)')])[0].click()    
        time.sleep(.6)
        
    # choose week
    wk_rows = dt.get_es(calendar, 'tr', [('role', 'row')])
    whileboo = True
    n = 1
    while whileboo and n < len(wk_rows):
        wk_row = wk_rows[n]
        wk_button = get_wk_button(wk_row)
        if wk_button.text == str(wk.week):
            wk_button.click()
            whileboo = False
        n += 1
    if whileboo:
        raise ValueError('Week {} not available on calendar'.format(wk.week))
        
def get_current_wk_with_calendar(calendar):
    wk_rows = dt.get_es(calendar, 'tr', [('role', 'row')])
    whileboo = True
    n = 1
    last_week = 0
    while whileboo and n < len(wk_rows):
        wk_row = wk_rows[n]
        n += 1
        week = int(get_wk_button(wk_row).text)
        if week < last_week:
            whileboo = False
        else:
            last_week = week
        days = dt.get_es(wk_row, 'td', [('role', 'gridcell')])
        m = 0
        while whileboo and m < len(days):
            day = days[m]
            m += 1
            whileboo = dt.get_attribute(day, 'data-qtip') != 'This date is after the maximum date'
            if not whileboo:
                last_week -= 1
    return wt.Week(tup=(get_year(calendar), last_week))

def get_wk_button(wk_row):
    return dt.get_es(wk_row, 'div', [('class', 'x-datepicker-column-header-inner'), ('role', 'presentation')])[0]
        
def get_wk_0(calendar):
    wk_rows = dt.get_es(calendar, 'tr', [('role', 'row')])
    week_0 = int(get_wk_button(wk_rows[1]).text)
    year = get_year(calendar)
    if week_0 > 50:
        year -= 1
    return wt.Week(tup=(year, week_0))

def get_year(calendar):
    es = dt.get_es(calendar, 'span', [('data-ref', 'btnInnerEl')])
    n = 0
    whileboo = True
    while whileboo and n < len(es):
        e = es[n]
        txt = e.text
        if len(txt) > 0:
            yr = int(txt[-4:])
            whileboo = False
        n += 1
    return yr
    
chars_to_remove_default = ['`', '~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '-', '+', '[', '{', ']', '}', '\\', '|', ';', ':', '"', ',', '<', '.', '>', '/', '?']
words_to_remove_default = ['the', 'and', 'The', 'And', 'THE', 'AND', 'Deluxe', 'Remixes', 'Special', 'Edition', 'Version', 'Remastered', 'Edited', 'Clean', 'Explicit', 'Ed', 'Ex']
char_replace_default = ' '
def clean_text(txt, chars_to_remove=chars_to_remove_default, words_to_remove=words_to_remove_default, char_replace=char_replace_default):
    if type(txt) == list:
        result = [clean_text_helper(txt_item, chars_to_remove, words_to_remove, char_replace) for txt_item in txt]
    else:
        result = clean_text_helper(txt, chars_to_remove, words_to_remove, char_replace)
    return result
    
def clean_text_helper(txt, chars_to_remove, words_to_remove, char_replace):
    ccs = txt.split(' ')
    result = ''
    for cc in ccs:
        for c in chars_to_remove:
            cc = cc.replace(c, char_replace)
        cc = cc.strip()
        remove_word = False
        for w in words_to_remove:
            if cc == w:
                remove_word = True
        if not remove_word and len(cc) > 0:
            result += cc + ' '
    return result[:-1]

def str_to_int(s):
    return int(s.replace(',', ''))

def get_str_n(s, n):
    
    # go to first character after "("
    c = s.find('(')
    
    # move to nth comma, but ignore anything between quotes
    def is_quote(s, c):
        return s[c] == "'" and s[c-1] != '\\'
    def find_next_comma(s, c):
        while s[c] not in [',', ')']:
            if is_quote(s, c):
                c += 1
                while not is_quote(s, c):
                    c += 1
            c += 1
        return c
    c_0 = c
    for _ in range(n):
        c_0 = find_next_comma(s, c_0 + 1)
        while s[c_0 + 1] == ' ':
            c_0 += 1
    c_f = find_next_comma(s, c_0 + 1)
    return s[ c_0 + 2 : c_f - 1].replace('\\', '')

def onclick_to_song_info(s):
    song_name = get_str_n(s, 0)
    song_id = get_str_n(s, 1) + '-' + get_str_n(s, 2)
    artist_name = get_str_n(s, 3)
    return (song_id, artist_name, song_name)

def onclick_to_album_info(s):
    album_name = get_str_n(s, 0)
    album_id = get_str_n(s, 1)
    artist_id = get_str_n(s, 2)
    artist_name = get_str_n(s, 3)
    return (album_id, artist_id, artist_name, album_name)

def onclick_to_artist_info(s):
    artist_name = get_str_n(s, 0)
    artist_id = get_str_n(s, 1)
    return (artist_id, artist_name)

def full_id_to_n(full_id, n):
    pos_f = 0
    for _ in range(n + 1):
        pos_0 = pos_f
        pos_f = full_id.find('-')
    return full_id[pos_0 : pos_f]

def full_id_to_str(full_id):
    return '=' + full_id_to_n(full_id, 0)

def get_album_info(nielsen_id=None, primary_upc=None):
    def func(browser):
        whileboo = True
        login_boo = True
        n = 0
        while whileboo and n < 3:
            try:
                if nielsen_id:
                    error_id = nielsen_id
                    get_page(browser, nielsen_id, 'Album', login_boo=login_boo)
                else:
                    error_id = primary_upc
                    get_page(browser, primary_upc, 'upc', login_boo=login_boo)
                whileboo = False
            except:
                n += 1
                login_boo = False
        if whileboo:
            return ('not found', 'not found', 'not found', 'not found', ['not found'])
        artist_es = dt.get_es(browser, 'a', [('class', 'entity_parameter_cls')])
        if len(artist_es) > 0:
            s = dt.get_attribute(artist_es[0], 'onclick')
            artist_id, _ = onclick_to_artist_info(s)
            artist_name = artist_es[0].text
        else:
            e = dt.get_es(browser, 'div', [('class', 'artist_name_head_sub')])[0]
            for group_name in ['Various', 'Soundtrack', ' ']:
                if group_name in e.text:
                    artist_id, artist_name = (group_name, group_name)
                    break
            else:
                raise ValueError('Could not find artist for album id:{}, html name:{}.'.format(error_id, e.text))
        album_e = dt.get_es(browser, 'div', [('class', 'artist_dtls_name-cell')])[0]
        album_sub_es = dt.get_es_basic(album_e, 'a', [('class', 'mc-view-entityname')])
        if len(album_sub_es) > 0:
            album_name = dt.get_inner_html(dt.get_es(album_sub_es[0], 'div', [])[0])
        else:
            album_name = album_e.text.strip()
        album_e = dt.get_es(album_e, 'a', [('href', 'javascript:void(0);')])[0]
        s = dt.get_attribute(album_e, 'onclick')
        album_id = get_str_n(s, 3)
        if album_id == '181128932739111':
            album_id = 'not found'
        upcs = []
        try:
            table_e = dt.get_es(browser, 'td', [('data-qtip', 'Album Total')])[0]
            while dt.get_attribute(table_e, 'class') != 'x-grid-item-container':
                table_e = dt.get_parent(table_e)
            upc_es = dt.get_es(table_e, 'span', [('class', 'x-tree-node-text ')])
            for upc_e in upc_es[1:]:
                txt = upc_e.text
                pos = txt.find('-')
                if pos == -1:
                    pos = len(txt)
                upc = int(txt[:pos])
                upcs.append(upc)
        except:
            if len(upcs) == 0:
                upcs.append('not found')
        if '' in [album_id, artist_id, artist_name, album_name]:
            raise ValueError('Incomplete Nielsen metadata: "{}", "{}", "{}", "{}", {}'.format(album_id, artist_id, artist_name, album_name, upcs))
        return (album_id, artist_id, artist_name, album_name, upcs)
    return dt.try_until_success(func, dt.get_browser)

def get_artist_info(nielsen_id=None, upc=None, isrc=None):
    def func(browser):
        get_nielsen_id = True
        try:
            if nielsen_id is not None:
                get_nielsen_id = False
                artist_id = nielsen_id
        except:
            pass
        if get_nielsen_id:
            if upc:
                _, artist_id, _, _, _ = get_album_info(primary_upc=upc)
            else:
                _, artist_id, _, _, _ = get_song_info(isrc=isrc)
        n = 0
        whileboo = True
        login_boo = True
        while whileboo and n < 3:
            try:
                get_page(browser, artist_id, content_type='Artist', login_boo=login_boo)
                whileboo = False
            except:
                n += 1
                login_boo = False
        if whileboo:
            return ('not found', 'not found', ['not found'])
        artist_e = dt.get_es(browser, 'div', [('class', 'artist_dtls_name-cell')])[0]
        artist_sub_es = dt.get_es_basic(artist_e, 'a', [('class', 'mc-view-entityname')])
        if len(artist_sub_es) > 0:
            artist_name = dt.get_inner_html(dt.get_es(artist_sub_es[0], 'div', [])[0])
        else:
            artist_name = artist_e.text.strip()
        top_albums_table = dt.get_es(browser, 'div', [('class', 'summary-chart-header')], 'Top Albums')[0]
        while dt.get_tag(top_albums_table) != 'tbody':
            top_albums_table = dt.get_parent(top_albums_table)
        album_es = dt.get_es(top_albums_table, 'a', [('href', 'javascript:void(0);')])
        top_album_ids = [] 
        for album_e in album_es:
            album_id, _, _, _ = onclick_to_album_info(dt.get_attribute(album_e, 'onclick'))
            top_album_ids.append(album_id)
        if '' in [artist_name, artist_id]:
            raise ValueError('Incomplete Nielsen metadata: "{}", "{}"'.format(artist_name, artist_id))
        return artist_id, artist_name, top_album_ids
    return dt.try_until_success(func, dt.get_browser)

def get_song_info(nielsen_id=None, isrc=None):
    def func(browser):
        whileboo = True
        login_boo = True
        n = 0
        while whileboo and n < 3:
            try:
                if nielsen_id is None:
                    try:
                        get_page(browser, isrc, content_type='isrc', login_boo=login_boo)
                    except:
                        time.sleep(60)
                else:
                    try:
                        get_page(browser, nielsen_id, content_type='Song', login_boo=login_boo)
                    except:
                        time.sleep(60)
                whileboo = False
            except:
                n += 1
                login_boo = False
        if whileboo:
            return 'not found', 'not found', 'not found', 'not found', ['not found']
        artist_outer_e = dt.get_es(browser, 'div', [('class', 'artist_name_head_sub')])[0]
        artist_e = dt.get_es(artist_outer_e, 'a', [('href', 'javascript:void(0);')])[0]
        onclick = dt.get_attribute(artist_e, 'onclick')
        artist_id, _ = onclick_to_artist_info(onclick)
        artist_name = dt.get_attribute(artist_e, 'title')
        if artist_name == '':
            artist_name = artist_e.text
        song_e = dt.get_es(browser, 'div', [('class', 'artist_dtls_name-cell')])[0]
        song_sub_es = dt.get_es_basic(song_e, 'a', [('class', 'mc-view-entityname')])
        if len(song_sub_es) > 0:
            song_name = dt.get_inner_html(dt.get_es(song_sub_es[0], 'div', [])[0])
        else:
            song_name = song_e.text.strip()
        star_e = dt.get_es(song_e, 'a', [('href', 'javascript:void(0);')])[0]
        onclick = dt.get_attribute(star_e, 'onclick')
        song_id = get_str_n(onclick, 3)
        isrc_table = dt.get_es(browser, 'span', [('class', 'x-tree-node-text ')], 'Song Total')[0]
        while dt.get_tag(isrc_table) != 'div' or dt.get_attribute(isrc_table, 'class') != 'x-grid-item-container':
            isrc_table = dt.get_parent(isrc_table)
        isrc_es = dt.get_es(isrc_table, 'span', [('class', 'x-tree-node-text ')])
        isrcs = []
        for isrc_e in isrc_es[1:]:
            isrcs.append(isrc_e.text.split(' ')[-1])
        if '' in [artist_name, song_name, song_id] == 0:
            raise ValueError('Incomplete Nielsen metadata: "{}", "{}", "{}", "{}", "{}"'.format(artist_id, artist_name, song_name, song_id, isrcs))
        return song_id, artist_id, artist_name, song_name, isrcs
    return dt.try_until_success(func, dt.get_browser)

def get_page(browser, item_id, content_type='Album', login_boo=True):
    if item_id == '':
        raise ValueError('No item id provided.')
    if content_type == 'upc':
        content_type = ''
        item_id = str(item_id).zfill(len('0602557935059'))
    if content_type == 'isrc':
        content_type = ''
    go_to_connect(browser, login_boo=login_boo)
    search_bar = dt.get_es(browser, 'input', [('id', 'mc-home-search-textbox')])[0]
    dt.input_text(search_bar, '=' + str(item_id))
    time.sleep(1)
    click_e = None
    start_time = time.time()
    while click_e is None and time.time() - start_time < 10:
        try:
            e = dt.get_es(browser, 'table', [('class', 'mc-search-panel-table')])[0]
            es = dt.get_es(e, 'tr')
            for e in es:
                time.sleep(1)
                try:
                    type_e = dt.get_es_basic(e, 'div', [('class', 'mc-search-panel-type')])[0]
                    if type_e.text == content_type:
                        click_e = dt.get_es(e, 'div', [('class', 'mc-search-panel-name')])[0]
                        break
                except:
                    pass
        except:
            pass
    if click_e:
        click_e.click()
        dt.wait_for_item(browser, 'span', [('class', 'x-btn-icon-el x-btn-icon-el-default-small fa fa-calendar ')], appear=True)
    else:
        raise ValueError('Could not click ' + str(item_id) + ' ' + content_type)
        
def get_url():
    return url