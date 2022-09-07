'''
Created on Jan 26, 2021

@author: SedanoD
'''

import os
import requests
import pandas as pd
import gzip
import time
import week_tools as wt
from io import StringIO
from datetime import datetime
# from cpu_vars import nielsen_credentials
    

## API Class
class nielsen_api:

    def __init__(self, umg=False):
        # if umg:
            # nielsen_credentials[0] = ("apiusermc.universalmusic@umusic.com", "zYhyiJq1dkPP")
        self.BASE_URL="http://api.musicconnect.mrc-data.com/"
        self.AUTH_URL=self.BASE_URL+"auth"
        self.API_KEY = os.environ['NIELSEN_API_TOKEN']      # api key i was given: 'YdZUpwFLPeDu590wKigQkaEh24mrO24Jeh6HJ310'
        self.USERNAME = os.environ['USEREMAIL']             # neilson username
        self.PASSWORD = os.environ['USERPASS']              # neilson password
        self.tokens = self.authorize()
        #self.isrc_endpoint = "mc/api/isrc/data/{isrc}"
        #self.upc_endpoint = "mc/api/barcode/data/{barcode}"

    def authorize(self):
        ## URL Headers and Parameters
        headers = {"Content-Type": "application/x-www-form-urlencoded", "x-api-key":self.API_KEY}
        payload = {"username":self.USERNAME, 'password':self.PASSWORD}
        ## Request
        print('Logging in with username:', self.USERNAME)
        r = requests.post(self.AUTH_URL, data=payload, headers=headers)
        if r.status_code == 200:
            tokens = r.json()
            r.close()
        else:
            raise ConnectionError('Error {}: {}'.format(r.status_code, r.reason))
        return tokens

    def run_api_call(self, wk, object_id, artist=False, c='US',metric=None, total=True, retry=5):

        ## Nielsen API Headers and Metrics
        BASE_URL = self.BASE_URL
        tokens = self.tokens
        ## Request Headers
        headers = {
            'Content-Type':'application/json',
            'Authorization': tokens['access_token'],
            'x-api-key': self.API_KEY,
            'Accept':'application/vnd.mrc-data.dashboard.v1+json'
        }
        ## Set Up Parameters
        if wk is None:
            week_id = None
        elif isinstance(wk, str):
            week_id = wk
        else:
            week_id = str(wk)
        #parameters = {'week_id':week_id, 'country':c}
        parameters = {'week_id':week_id, 'country':c, 'metric':metric}
        
        ## ISRC Endpoint URL
        artist_endpoint =  'api/artist/{artist_id}/data'.format(**{'artist_id':object_id})
        isrc_endpoint = "api/isrc/data/{isrc}".format(**{'isrc':object_id})
        upc_endpoint = "api/barcode/data/{isrc}".format(**{'isrc':object_id})

        if artist:
            endpoint = artist_endpoint
        elif len(object_id) == 12:
            if total:
                endpoint = isrc_endpoint+'/song'
            else:
                endpoint = isrc_endpoint
        elif len(object_id) > 12:
            if total:
                endpoint = upc_endpoint+'/album'
            else:
                endpoint = upc_endpoint
        else:
            raise ValueError('Invalid ID!')
        ## Run Request
        r = requests.post(url= BASE_URL + endpoint, json=parameters, headers=headers)
        if r.status_code != 200:
            if r.status_code == 400:
                print(f'Bad Request for ID: {object_id}')
                return r
            for i in range(5):
                print(f'Error: {r.reason}, retrying in {i+1}s...')
                time.sleep(i+1)
                r = requests.post(url= BASE_URL + endpoint, json=parameters, headers=headers)
                if r.status_code == 200:
                    break
        return r

    def download_request_result(self, request_id=str):
        r = self.run_status_request(request_id, endpoint='download')
        response_status = r.status_code
        response_reason = r.reason
        if response_status != 200:
            raise ValueError(f'Response came back with status code {response_status}:{response_reason}')
        ### Process Data 
        response_text = gzip.decompress(r.content)
        response_string = str(response_text, 'utf-8')
        DATA = StringIO(response_string)
        
        return pd.read_csv(DATA, delim_whitespace=True)

    def run_status_request(self, request_id, endpoint=str):
        ## Check Request Status
        status_endpoint = 'api/feed/status/'
        DOWNLOAD_URL = 'https://api.download.musicconnect.mrc-data.com/'
        headers = {
            'Authorization': self.tokens['access_token'],
            'x-api-key': self.API_KEY,
            'Accept':'application/vnd.mrc-data.datafeed.v1+json'
        }
        if endpoint=='status':
            r = requests.get(url=self.BASE_URL+status_endpoint+request_id, headers=headers)
        elif endpoint=='download':
            r = requests.get(url=DOWNLOAD_URL+request_id, headers=headers)
        else:
            raise ValueError("Invalid Endpoint. Please pass either 'status' or 'download'")
        return r

    def get_relationship(self, given_id=str,id_type=str,wanted_type=str):
        ''' 
        Get Relationship between given id and a wanted type
        ids can be of type: barcode (upc), album (nielsen album id),
        isrc, song (nielsen song id) and artist (nielsen artist id)
        '''
        headers = {
            'accept':'application/vnd.mrc-data.search.v1+json',
            'Authorization': self.tokens['access_token'],
            'x-api-key': self.API_KEY
            
        }
        ## Format Endpoint
        relationship_endpoint = 'api/relationship/'
        use_endpoint = relationship_endpoint+f'{id_type}-{wanted_type}/{given_id}'
        r = requests.get(url=self.BASE_URL+use_endpoint, headers=headers)
    
        return r

    def check_request_status(self, request_id=str, wait=True, timeout_limit=30):
        r = self.run_status_request(request_id, endpoint='status')
        if r.status_code != 200:
            raise ValueError('Invalid Request Id!')
        else:
            status = r.json()['status']
        if wait:
            ## Loop Through and Check if Request has finised...
            n=0
            timeout=False
            while (status != 'Complete') and (not timeout):
                print('Current status:',status)
                r = self.run_status_request(request_id, endpoint='status')
                status=r.json()['status']
                if status != 'Complete':
                    n+=1
                    time.sleep(60)
                timeout = n>timeout_limit
            if timeout:
                status = 'Timeout'
        return status 

    def get_bulk_isrcs(self, input_ptf=str, week_id=None, metric=None, country=None, save_to_csv=False):
        ## Get File Name
        input_file_name = os.path.basename(input_ptf)
        ## Headers and Endpoint for API Call
        headers = {
        'Authorization': self.tokens['access_token'],
        'x-api-key': self.API_KEY,
        'Accept':'application/vnd.mrc-data.bulkapi.v1+json'
        }
        ## Endpoint
        bulk_endpoint = 'api/isrc/bulk/data'
        ## Read in Input CSV of Isrcs
        files = {'isrc_file': (input_file_name, open(input_ptf, 'rb'), 'text/csv')}
        ## Headers for API Call
        params = (week_id, country, metric)
        if params == (None, None, None):
            parameters = None
        else:
            parameters = {}
            labels = ('week_id','country','metric')
            for l, p in zip(labels, params):
                if p is not None:
                    parameters[l] = p
        print("Running bulk isrc request...")
        ## Run Request
        if not parameters:
            r = requests.post(url=self.BASE_URL+bulk_endpoint, files=files, headers=headers)
        else:
            print(parameters)
            r = requests.post(url=self.BASE_URL+bulk_endpoint, files=files, data=parameters, headers=headers)
        response_status = r.status_code
        response_reason = r.reason
        if response_status != 200:
            raise ValueError(f'Response came back with status code {response_status}:{response_reason}')
        ### Check Request Status
        print('Checking request status...')
        request_id = r.json()['request_id']
        print(f'Request id: {request_id}')
        status = self.check_request_status(request_id=request_id)
        if status != 'Complete':
            print('Request has not completed after 30 min...')
            try_again = input('Try again? [Y/N]:')
            if try_again == 'Y':
                status = self.check_request_status(request_id=request_id, endpoint='status')
        if status == 'Complete':
            print('Bulk ISRC request completed!')
            df = self.download_request_result(request_id=request_id)
            ## Add Week ID 
            if not week_id:
                week_id = int(str(wt.get_this_wk()))
            if not country:
                c = 'US'
            else:
                c = country
            df['week_id'] = week_id
            df['country'] = c
            if save_to_csv:
                print("Saving to csv...")
                new_file_name = os.path.basename(input_ptf).split('.csv')[0]+'_results_{}'+'.csv'
                df.to_csv(new_file_name.format(str(datetime.now().date())), index=False)
                print('Done!')
        return df