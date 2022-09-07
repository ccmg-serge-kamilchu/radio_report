'''
Created on Jun 1, 2018

@author: cmgreporting.sv
'''

'''
this does everything related to weeks
create weeks using
    Week(tup=(2019, 22))
    Week(wk_str='201922')
    Week(d=datetime(2019, 6, 21))
when you use a datetime input, it will return the week that that date is in, even if that's not the actual week-ending date
'''


### Read in Weeks list from CSV and convert columns to Datetime Objects
import pandas as pd
from datetime import timedelta
from datetime import datetime
date_df = pd.read_csv(r'./weeks.csv')
date_df['date'] = pd.to_datetime(date_df['date'])
date_df['we_date'] = pd.to_datetime(date_df['we_date'])
### Groupby Date_Df in order to create a new dataframe containing the Year, Week Number, and Week End Date
cols = ['year', 'week', 'we_date']
df = date_df.groupby(cols, as_index=False).count()[cols]
### Initialize Tuple Maps, Index Maps and Date Map
tup_map = {}
i_map = {}
d_map = {}
### Dynamically Grow the Dictionaries initialized above
for i, row in df.iterrows():
    y = row['year']
    w = row['week']
    we_date = row['we_date']
    if y not in tup_map:
        tup_map[y] = {}
    tup_map[y][w] = {'i': i, 'we_date': we_date}
    i_map[i] = {'year': y, 'week': w, 'we_date': we_date}
### Date Map
for i, row in date_df.iterrows():
    d_map[datetime.strftime(row['date'], format='%Y-%m-%d')
          ] = {'year': row['year'], 'week': row['week']}
### Defines Week class and methods.


class Week:
    '''
    This Week Class Object is used by other modules to gather information on any date. Given a date this class can return the 
    week in the year that the date was in. There are three ways to initiate a Week object. You can either pass in a tuple with 
    the year and week e.g. tuple = (year, week), a string containing the year and week e.g. wk_str = 'yearweek', or a datetime 
    object d = datetime(year, month, day)
    '''

    def __init__(self, tup=None, wk_str=None, d=None):
        ## Parse out year and week depending on what arguments were passed in.
        if tup is not None:
            y, w = tup
        elif wk_str is not None:
            y = int(wk_str[:4])
            w = int(wk_str[-2:])
        else:
            d = datetime(d.year, d.month, d.day)
            v = d_map[datetime.strftime(d, format='%Y-%m-%d')]
            y = v['year']
            w = v['week']
        self.year = y  # Initialize year
        self.week = w  # Initialize week #
        self.tup = (self.year, self.week)  # Initialize tuple
        self.wk_str = str(self.year).zfill(
            4) + str(self.week).zfill(2)  # Initialize week string
        self.we_date = tup_map[y][w]['we_date']  # Week-ending date (DateTime)
        self.we_date_str = datetime.strftime(
            self.we_date, format='%Y-%m-%d')  # Week-ending date (String)

    def __str__(self):
        return self.wk_str  # Return week string

    def __lt__(self, b):
        confirm_type(b)
        # Week Comparison with another Week object Less than Week B (By Week End Date)
        return self.we_date < b.we_date

    def __le__(self, b):
        confirm_type(b)
        # Week comparision with another Week object. Less than/equal to Week B (By Week End Date)
        return self.we_date <= b.we_date

    def __gt__(self, b):
        confirm_type(b)
        # Week comparison with another Week object. Greater than Week B (By Week End Date)
        return self.we_date > b.we_date

    def __ge__(self, b):
        confirm_type(b)
        # Week comparison with another Week object. Greater then/equal to Week B (By Week End Date)
        return self.we_date >= b.we_date

    def __eq__(self, b):
        confirm_type(b)
        # Week comparison with another Week object. Equal to Week B (By Week End Date)
        return self.we_date == b.we_date

    def __add__(self, b):
        # Add Week objects using add_help() function
        return add_helper(self, b, 1)

    def __sub__(self, b):
        # Subtract week objects using add_help() function with mult = -1
        return add_helper(self, b, -1)

    def get_wb_date(self, trend_report=False):
        if trend_report:
            return self.we_date - timedelta(days=6)
        else:
            return (self - 1).we_date + timedelta(days=1)


def get_today_str():
    return datetime.strftime(get_today_date(), format='%Y-%m-%d')


def get_today_date():
    dt = datetime.today()
    return datetime(dt.year, dt.month, dt.day)


def add_helper(a, b, mult):
    if isinstance(b, Week):
        return wk_to_i(a) + mult * wk_to_i(b)
    elif isinstance(b, tuple):
        y = a.year
        w = a.week
        return Week(tup=(y + mult * b[0], 1)) + (w + mult * b[1] - 1)
    else:
        i = wk_to_i(a)
        return i_to_wk(i + mult * b)


def confirm_type(x):
    if not isinstance(x, Week):
        raise ValueError('Invalid type.')


def get_wks_in_yr(y):
    for w in tup_map[y]:
        yield Week(tup=(y, w))


def count_wks_in_yr(y):
    return len(tup_map[y].values())


def get_this_we_str():
    return get_this_wk().we_date_str


def get_this_wk():
    return Week(d=datetime.today()-timedelta(days=10))


def get_we_date(d):
    return Week(d=d).we_date


def get_streaming_week_0():
    return Week(tup=(2014, 48))


def get_wks(wk_0, wk_f):
    if wk_0 > wk_f:
        step = -1
    else:
        step = 1
    return [i_to_wk(i) for i in range(wk_to_i(wk_0), wk_to_i(wk_f) + step, step)]


def wk_to_i(wk):
    return tup_map[wk.year][wk.week]['i']


def i_to_wk(i):
    v = i_map[i]
    return Week(tup=(v['year'], v['week']))
