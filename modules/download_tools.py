'''
Created on Apr 12, 2018

@author: wennekt
'''

'''
basically just a wrapper around the selenium module to make things easier
this is essentially the same as the beautifulsoup package, which I didn't know existed when I wrote this
accessed extensively by connect_tools
'''

turn_on_tus = True
time_out_default = 15

import file_tools as ft
import webbrowser
import time
import traceback
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver
from selenium.webdriver.common.keys import Keys # this is used by other modules
from datetime import datetime
from selenium.webdriver import ActionChains
import urllib
import html
import cpu_vars as cv

default_download_dir = ft.join(cv.default_download_folder)
ff_profile_ptf = ft.join(cv.ff_profile_dir, cv.ff_profile_name)
bypass_profile = cv.bypass_profile

def try_until_success(func, get_browser_func, *args):
    
    if turn_on_tus:
        ran = False
        while not ran:
            ran, val = try_func(func, get_browser_func, *args)
    else:
        ran, val = try_func(func, get_browser_func, *args)
    return val

def try_until_success_n(func, get_browser_func, n, *args):
    for _ in range(n): 
        ran, val = try_func(func, get_browser_func, *args)
        if ran:
            return val
    print('try until success failed after {} attemps.'.format(n))
    return 'failure'
        
def try_func(func, get_browser_func, *args):
    ran = True
    val = None
    browser = None
    try:
        browser = get_browser_func()
        val = func(browser, *args)
    except Exception as e:
        ran = False
        print(traceback.format_exc())
        print(e)
        print('Sleeping for 1 min and trying again...')
        time.sleep(60)
    if browser:
        browser.quit()
    return (ran, val)

def get_es(browser, type1=None, attrs=[], txt=None, max_time=time_out_default):
    whileboo = True
    start_time = time.time()
    while whileboo and time.time() - start_time < max_time:
        es = get_es_basic(browser, type1, attrs, txt)
        whileboo = len(es) == 0
    return es

def wait_for_item(browser, type1, attrs=[], txt=None, appear=True, max_time=time_out_default):
    start_time = time.time()
    whileboo = True
    while whileboo and time.time() - start_time < max_time:
        es = get_es_basic(browser, type1, attrs, txt)
        if appear:
            whileboo = len(es) == 0
        else:
            whileboo = len(es) > 0
    if whileboo:
        raise ValueError('wait for element failed')
    
def get_tag(e):
    return e.tag_name

def get_es_basic(browser, type1=None, attrs=[], txt=None):
    es = []
    if len(attrs) < 1:
        if type1 is None:
            es.extend(browser.find_elements_by_css_selector('*'))
        else:
            es.extend(browser.find_elements_by_tag_name(type1))
    else:
        if type1 is None:
            pos_es = browser.find_elements_by_css_selector('*')
        else:
            attr, s = attrs[0]
            sstr = get_sstr(type1, attr, s)
            pos_es = browser.find_elements_by_css_selector(sstr)
        for e in pos_es:
            n = 1
            whileboo = True
            while whileboo and n < len(attrs):
                attr, s = attrs[n]
                whileboo = get_attribute(e, attr) == s
                n += 1
            if whileboo:
                if txt is not None:
                    if e.text == txt:
                        es.append(e)
                else:
                    es.append(e)
    return es

def get_sstr(type1, type2, s):
    return type1 + '[' + type2 + "='" + s + "']"

def get_attribute(e, attributename):
    try:
        txt = e.get_attribute(attributename)
    except:
        txt = 'no attribute found'
    return txt

def get_parent(e):
    return e.find_element_by_xpath('..')

def get_browser_from_e(e):
    return e.parent

def get_current_url(browser):
    return browser.current_url

def download_url(url, ptf):
    ft.delete_ptf(ptf)
    urllib.request.urlretrieve(url, ptf)
    
def get_browser(download_dir=None, file_extension='csv', eager=False, bypass_profile = bypass_profile):

    if bypass_profile:
        if download_dir is None:
            download_dir = default_download_dir
        #ff_Binary = FirefoxBinary(cv.ff_binary_ptf)
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference('browser.helperApps.alwaysAsk.force', False)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk",'text/plain, text/csv, application/csv, application/download,application/octet-stream,text/comma-separated-values,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        profile.set_preference("browser.download.dir", download_dir)
        browser = webdriver.Firefox(executable_path=cv.geckodriver_ptf, firefox_profile=profile)
        return browser

    else: 
        if download_dir is None:
            download_dir = default_download_dir
        ff_Binary = FirefoxBinary(cv.ff_binary_ptf)
        profile = webdriver.FirefoxProfile(ff_profile_ptf)
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference('browser.helperApps.alwaysAsk.force', False)
        profile.set_preference("browser.download.dir", download_dir)
        if eager:
            caps = DesiredCapabilities().FIREFOX
            caps["marionette"] = True
            caps["pageLoadStrategy"] = 'eager'
        if file_extension == 'csv':
            profile.set_preference('browser.helperApps.neverAsk.saveToDisk', "text/comma-separated-values")
        elif file_extension == 'x-csv':
            profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/x-csv')
        elif file_extension == 'xlsx':
            profile.set_preference('browser.helperApps.neverAsk.saveToDisk', "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif file_extension == 'plain':
            profile.set_preference("browser.helperApps.neverAsk.saveToDisk",'text/plain, text/csv, application/csv, application/download,application/octet-stream, text/comma-separated-values')
        browser = webdriver.Firefox(firefox_binary=ff_Binary, executable_path=cv.geckodriver_ptf, firefox_profile=profile)
        return browser

def change_browser(browser, download_dir=None):
    url = get_current_url(browser) 
    browser.get("about:config")
    es = get_es_basic(browser, 'button', [('label', 'I accept the risk!')])
    if len(es) > 0: 
        es[0].click()
    if download_dir is not None:
        set_string_preference(browser, 'browser.download.dir', download_dir)
    time.sleep(1)
    browser.get(url)
    
def set_string_preference(browser, name, value):
    s = '''
    var prefs = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefBranch);
    prefs.setCharPref(arguments[0], arguments[1]);
    '''
    modified = browser.execute_script(s, name, value)
    if modified in [None, True]:
        accept_alert(browser)

def click_until_success(es, repeat=False, time_out=time_out_default):
    whileboo = True
    n = 0
    if len(es) == 0:
        raise ValueError("No elements in list!")
    else:
        start_time = time.time()
        while whileboo and (n < len(es) or repeat) and (time.time() - start_time < time_out):
            if n == len(es):
                n = 0
            try:
                e = es[n]
                e.click()
                whileboo = False
            except:
                pass
            n += 1
        if whileboo:
            e = None
            raise ValueError("Couldn't click on anything!")
    return e

def mouseover(browser, e):
    ActionChains(browser).move_to_element(e).perform()

def set_attribute(browser, e, attr, val):
    arg_str = "arguments[0].setAttribute('{}', '{}')".format(attr, val)
    browser.execute_script(arg_str, e)
    
def get_inner_html(e):
    return html.unescape(e.get_attribute('innerHTML'))

def get_outer_html(e):
    return html.unescape(e.get_attribute('outerHTML'))

def move_downloaded_file(d_ptf, f_ptf):
    # wait for file
#     print('waiting for', d_ptf)
    ft.wait_for_file(d_ptf)
    
    # rename file
#     print(d_ptf, '-->', f_ptf)
    ft.move(d_ptf, f_ptf)
        
def input_text(e, txt, clear=False, enter=False):
    if clear:
        e.clear()
    e.send_keys(txt)
    if enter:
        time.sleep(0.5)
        e.send_keys(Keys.RETURN)
        
def scroll_e(e):
    browser = get_browser_from_e(e)
    browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', e)
    browser.execute_script('arguments[0].scrollTop = 0', e)
    
def arrow(e, direction):
    e.send_keys(Keys.ARROW_DOWN)
    print('update arrow method to take string')

def save_e_as(browser, e):
    ActionChains(browser).move_to_element(e).context_click(e).send_keys('v').perform()
    
# def save_page(browser, ptf):
#     with codecs.open(ptf, 'w') as f:
#         f.write(browser.page_source)
        
def switch_to_new_window(browser):
    browser.switch_to_window(browser.window_handles[-1])
    
def open_new_window(browser, url):
    browser.execute_script("(window.open('" + url + "'))")
    switch_to_new_window(browser)
    
def close_windows(browser, i=None):
    if i:
        browser.switch_to_window(i)
        browser.close()
        browser.switch_to_window(0)
    else:
        for wh in browser.window_handles:
            browser.switch_to_window(wh)
            browser.close()
        
def get_default_download_dir():
    return default_download_dir

def accept_alert(browser):
    start_time = time.time()
    whileboo = True
    while whileboo and time.time() - start_time < 2:
        try:
            alert = browser.switch_to.alert
            alert.accept()
            whileboo = False
        except:
            pass
    if whileboo:
        pass
#         print('no alert found')

def clear_cookies(browser):
    browser.detele_all_cookies()