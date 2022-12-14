import os
import pandas as pd
import numpy as np
import sqlite3 as sql
import billboard_tools as bt
import week_tools as wt
import file_tools as ft
import connect_tools as ct
import connect_tools2 as ct2
import excel_tools as xt
import metadata
import tabular_data as td

REPORT_NAME = 'Radio vs Sales'
RUN_WEEKDAY = 1
RUN_TIME = (5, 0)
MAIN_DIR = r'G:\Reporting\Radio vs Sales New'
CALCS_DIR = ft.join(MAIN_DIR, 'calcs')
DATA_DIR = ft.join(MAIN_DIR, 'data')
METADATA_DIR = r'G:\metadata_sql'
## Chart List
CHARTS = [
    'Adult Contemporary', 
    'Adult R&B Airplay', 
    'Adult Pop Airplay',
    'Alternative Airplay',
    'Christian Airplay',
    'Country Airplay', 
    'Latin Airplay', 
    'Mainstream R&B/Hip-Hop Airplay',
    'Mainstream Rock Airplay', 
    'Pop Airplay', 
    'Rhythmic Airplay', 
    'Smooth Jazz Airplay', 
    'Adult Alternative Airplay',
    'Digital Song Sales',
    'Top 200 Song Consumption (Weekly)',
    'Audio On-Demand Streaming (Weekly)'
]

def format_excel(report_sets, obj_d):
    '''
    Format excel report by taking in the report sets and objs and 
    reading in the different data from paths and the SQL database. 
    In addition, clear the Trend Reports SQL Database for this week 
    and add this week's TR data. 
    '''
    ## Get Data
    tr_df = pd.DataFrame()
    ## Read from xlsx paths
    for _, tr, _ in report_sets['connect']:
        tr_df = pd.concat([tr_df, td.get_df(tr.ptf_xlsx)])
    tr_df = tr_df.iloc[:,~tr_df.columns.duplicated()].copy()
    ## Clean Strings
    tr_df_obj = tr_df.select_dtypes(['object'])
    tr_df[tr_df_obj.columns] = tr_df_obj.apply(lambda x: x.str.strip())
    ## Get Nielsen Maps, Merge with Trend Report data and clean a little
    nielsen_maps = ct.get_nielsen_maps()
    df_csv = tr_df.merge(nielsen_maps, on=['Artist', 'Song'], how='left')
    if sum(df_csv['Nielsen_ID'].isna()) >= 1:
        tr_df['Song'] = tr_df['Song'].apply(lambda x: x.replace('\xa0', ' '))
        df_csv = tr_df.merge(nielsen_maps, on=['Artist', 'Song'], how='left')

    ## Account for any Errors in the merging
    bool_array = df_csv['Nielsen_ID'].isna() # Check for NAs in the Nielsen Ids
    if sum(bool_array) > 0:
        ## Which ids are NA
        bool_array = df_csv['Nielsen_ID'].isna()
        ## Print for Records
        print(df_csv[bool_array][['Artist', 'Song']].drop_duplicates().reset_index())
        ## Drop NA
        df_csv.dropna(subset=['Nielsen_ID'], inplace=True)
    
    ## Merge with trs from Database
    db_df = get_tr(obj_d, df_csv)
    if len(db_df) > 0:
        try:
            merged = pd.concat([df_csv, get_tr(obj_d, df_csv)], ignore_index=True)
        except:
            raise ValueError('Error in concatination')
    else:
        merged = df_csv

    merged.replace(np.nan, 'nan', inplace = True)
    merged['Label Abbreviation'] = merged['Label Abbreviation'].replace('nan', '-')
    ## Send TR to SQL Databse
    append_tr(df_csv)

    ## Get Charts
    df_dict = get_chart_data(weeks = [wt.get_this_wk(), wt.get_this_wk() - 1], id_dict=False)

    # open template
    template_ptf = ft.get_most_recent_ptf(ft.join(MAIN_DIR, 'templates'))
    app, wb = xt.get_wb(template_ptf)
    app.calculation = 'manual'

    # drop in trend report
    xt.arr_to_sht(merged, wb.sheets['Trend Reports'], clear= True)
    # drop in digital songs
    xt.arr_to_sht(df_dict['Digital Songs'].fillna("-"),wb.sheets['Digital Songs'], clear=True)
    # drop in song consumption
    xt.arr_to_sht(df_dict['Song Consumption'].fillna("-"),wb.sheets['Song Consumption'], clear=True)
    # drop in all chart data
    xt.arr_to_sht(df_dict['Airplay Charts'].fillna("-"), wb.sheets['Charts'],clear = True)
    # drop in On-Demand Streaming
    xt.arr_to_sht(df_dict['Audio On-Demand'].fillna("-"), wb.sheets['Audio On-Demand'], clear = True)

    # Set calcs to auto
    app.calculation = 'automatic'

    # Save Calcs
    calc_ptf = get_report_ptf(calcs=True)
    wb.save(calc_ptf)

    ## Copy and Paste Values for each genre sheet
    for i in range(2, 15):
        ws = wb.sheets[i]
        xt.copy_paste_values(ws, (1, 1), (1, 1))
        xt.copy_paste_values(ws, (7, 2), (56, 40))

    ## Delete Data Sheets
    for i in range(1, 7):
        i = 15
        wb.sheets[i].delete()


    # save as and close
    ptf = get_report_ptf()
    wb.save(ptf)
    wb.close()
    app.quit()
    
def get_report_ptf(calcs=False):
    """ Get the file path to the report xlsx file."""
    if calcs:
        return ft.join(CALCS_DIR, '{} {}.xlsx'.format(REPORT_NAME, wt.get_this_wk()))
    else:
        return ft.join(MAIN_DIR, 'reports', '{} {}.xlsx'.format(REPORT_NAME, wt.get_this_wk()))

def run_connect_report(genre, tr, s):
    """
    Run the connect report using the connect tools module and Metadata Song
    objects.
    """
    ct.run_trend_report(template_name=tr.template_name, item_ids=['='+nielsen_id for nielsen_id in tr.nielsen_ids], wk0=tr.wk_0, wkf=tr.wk_f,scrape = True, report_name=tr.tr_name)

def download_connect_data(genre, tr, s):
    """
    Get the download status of the trend reports. If the csv for the report
    exists then return 'Downloaded'. If it doesn't exist then get the content
    manager report. If the content manager report shows that the reports are
    done, then download the df. If not then return the result from the content
    manager report, which will be either Timeout or Error.
    """
    download_status = 'Downloaded'
    if s == '':
        if ft.file_exists(tr.ptf_csv, False):
            return download_status
        if not ft.file_exists(tr.ptf_xlsx):
            download_status = ct.download_contentmanager_report(report_name=tr.tr_name, d_dir=ft.get_parent_dir(tr.ptf_xlsx))
            if download_status == 'Downloaded':
                tr.get_df()
    return download_status
    
def get_report_sets(chart_d):
    """"
    Return the report sets, i.e dict containing data source as key and a list of
    report objects as the value. In this case the values will be a list of trend
    report objects. Create Trend Report Objects for unique Nielsen Ids that were
    scraped from the Nielsen Charts. Also clear the SQL database that contains the
    Niesen Id maps that are used later in the report. 
    """

    ## Dummy Class to be used with the Trend Report Object
    class obj():

        def __init__(self, x):
            self.id = x

        def get_nielsen_id(self):
            return self.id
    ## Constants for Trend Report Objects
    s = ''
    label = 'Weekly'
    wk_f = wt.get_this_wk()
    wk_0 = wk_f - 1
    ## Get All Nielsen Ids
    nielsen_ids = []
    for chart in chart_d:
        if chart not in ['Digital Songs','Top 200 Song Consumption (Weekly)','Audio On-Demand Streaming (Weekly)']:
            nielsen_ids.extend(chart_d[chart])
    ## Get Unique Nielsen Ids
    unique_ids = []
    for i in nielsen_ids:
        if i.strip("''") not in unique_ids:
            unique_ids.append(i.strip("''"))
    ## Initialize objects for each unique Nielsen Id
    unique_objs = [obj(i) for i in unique_ids]
    # Get Trend Report Objects from 'Obj' Objects
    reports = []
    wk_f = wt.get_this_wk()
    wk_0 = wk_f - 1
    for tr in ct2.get_trend_reports(objs=check_nielsen_maps(unique_objs), template_name='Weekly Database', wk_0=wk_0, wk_f=wk_f, tr_name='Weely Database {}'.format(wk_f), n=75, d_dir=ft.join(METADATA_DIR, 'weekly database')):
    #for tr in ct2.get_trend_reports(objs=unique_objs, template_name='Weekly Database', wk_0=wk_0, wk_f=wk_f, tr_name='Weely Database {}'.format(wk_f), n=75, d_dir=ft.join(METADATA_DIR, 'weekly database')): 
        reports.append((label, tr, s))
    ## Return dict  
    return {'connect': reports}

def get_objs():
    """
    Get a dict object with the top n tracks for each chart in the CHARTS 
    list. First check if the charts have already been scraped by queryiing
    the charts out of the SQL Database. If nothing comes back from the 
    initial pull then Scrape Nielsen Charts using the Billboard Tools module.  
    """
    ## Scrape this weeks charts and store then in SQL Database
    weeks = [wt.get_this_wk()]
    ## Initialize dict to hold Nielsen Ids
    chart_d = get_chart_data(weeks, n=100)
    ## if Charts come back empty Scape them
    if len(chart_d) == 0:
        for chart in CHARTS: 
            try:
                bt.scrape_billboard(weeks=weeks, chart_name=chart)
            except: 
                print("Trying again...")
                bt.scrape_billboard(weeks=weeks, chart_name=chart)
        chart_d = get_chart_data(weeks, n=100)
    ## Return Id Dict
    return chart_d
    
def check_data_status():
    """
    Check the data status by checkning if the current week is the current
    Nielsen Week.
    """
    return ct2.get_current_wk() == wt.get_this_wk()
    
def get_chart_data(weeks=list, id_dict=True, n = 50):
    '''
    Take in a list of weeks and return a dict with the Nielsen Chart names as keys and 
    either the Nielsen Ids for the songs in those weeks' charts in a list or the entire chart
    itself in a DataFrame as the values. 
    '''
    # Query out the charts from the SQL Database
    max_wk_str = max(weeks).wk_str
    weeks = [w.wk_str for w in weeks]
    conn = sql.connect(r'G:\metadata_sql\billboard_charts.db')
    chart = pd.read_sql("SELECT * FROM radio_charts WHERE TW_Rank < {} AND WK IN ({});".format(n+1,','.join(weeks)), conn)
    digital_songs =  pd.read_sql("SELECT * FROM digital_songs WHERE WK IN ({});".format(max_wk_str), conn)
    song_consumption =  pd.read_sql("SELECT * FROM top_200 WHERE WK IN ({});".format(max_wk_str), conn)
    audio_od = pd.read_sql("SELECT * FROM audio_od_streaming WHERE WK IN ({});".format(max_wk_str), conn)
    conn.close()
    # Initialize the dict obj that will contain the charts
    chart_d = {}
    # Build dict of Nielsen Ids
    if id_dict:
        for chart_name in chart['Chart'].unique():
            chart_d[chart_name] = list(chart['Nielsen_ID'][chart['Chart'] == chart_name])
        '''
        chart_d['Digital Songs'] = list(digital_songs['Nielsen_ID'])[:n]
        chart_d['Top 200 Song Consumption (Weekly)'] = list(song_consumption['Nielsen_ID'])[:n]
        '''
    # Build dict of DataFrames
    else: 
        chart_d['Airplay Charts'] = chart
        chart_d['Digital Songs'] = digital_songs
        chart_d['Song Consumption'] = song_consumption
        chart_d['Audio On-Demand'] = audio_od
    # Return dict 
    return chart_d

def check_nielsen_maps(objs):
    needed = []
    nielsen_maps = list(ct.get_nielsen_maps()['Nielsen_ID'])
    for song in objs:
        if (song.get_nielsen_id() not in nielsen_maps) & (song not in needed):
            needed.append(song)
    return needed

def get_tr(chart_d, df):

    ## Get All Nielsen Ids
    nielsen_ids = []
    for chart in chart_d:
        if chart not in ['Digital Songs','Top 200 Song Consumption (Weekly)','Audio On-Demand Streaming (Weekly)']:
            nielsen_ids.extend(chart_d[chart])
    ## Get Unique Nielsen Ids
    unique_ids = []
    for i in nielsen_ids:
        if i.strip("''") not in unique_ids:
            unique_ids.append(i.strip("''"))
    ## Get needed ids
    needed_ids = []
    for n in unique_ids:
        if n not in list(df['Nielsen_ID'].unique()):
            needed_ids.append(n)
    ## Get Data from Database
    conn = sql.connect(ft.join(METADATA_DIR, 'nielsen_maps_fixed.db'))
    query = 'SELECT * FROM trend_reports WHERE Nielsen_ID in ({ids});'.format(**{'ids':','.join(needed_ids)})
    df = pd.read_sql(query, conn)
    conn.close() 
    
    return df

def append_tr(data):
    ## Clean Data
    columns = data.columns
    data.columns = [c.replace(' ', '_') for c in columns]
    data['Nielsen_ID'] = data['Nielsen_ID'].map(int)
    
    ## Send Data to SQL Database
    conn = sql.connect(r"G:\metadata_sql\nielsen_maps_fixed.db")
    data.to_sql('trend_reports', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()
    
    print('Trend Reports sent to SQL Database!')
    return None