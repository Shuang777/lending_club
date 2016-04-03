import json
import random
import time
import logging
import codecs
from sets import Set
from datetime import datetime

from cookielib import CookieJar
from getpass import getpass
from urllib import urlencode
from urllib import urlretrieve
from urllib2 import build_opener
from urllib2 import HTTPCookieProcessor
from urllib2 import HTTPSHandler

from data_model import parse_loan_data_from_file
from lc_parser import LoanHTMLParser, NoteHTMLParser

ACCOUNT_SUMMARY_URL = 'https://www.lendingclub.com/account/summary.action'
NOTES_URL = 'https://www.lendingclub.com/foliofn/browseNotesAj.action'
QUERY_PARAMS_URL = \
    'https://www.lendingclub.com/foliofn/tradingInventory.action'
LOGIN_URL = 'https://www.lendingclub.com/account/login.action'
LOGGED_IN_VALIDATION = 'Welcome'

LOAN_DATA_CSV_URL = 'https://www.lendingclub.com/' + \
    'fileDownload.action?file=LoanStatsNew.csv&type=gen'
LOAN_DATA_CSV_TMPFILE = '/tmp/loan_stats_new.csv'
IN_FUNDING_DATA_CSV = 'https://www.lendingclub.com/' + \
    'fileDownload.action?file=InFunding2StatsNew.csv&type=gen'

NOTE_INFO_BASE_URL = 'https://www.lendingclub.com/foliofn/browseNotesLoanPerf.action'
LOAN_INFO_BASE_URL = 'https://www.lendingclub.com/foliofn/loanDetail.action'

# Yes I am Chrome.
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) ' + \
    'AppleWebKit/537.36 (KHTML, like Gecko) ' + \
    'Chrome/28.0.1500.72 Safari/537.36'

# random sleep between requests (in seconds)
MIN_SLEEP = 0
MAX_SLEEP = 1


def build_note_info_url(note_id, loan_id, order_id):
    return NOTE_INFO_BASE_URL + \
        'loan_id=%s&order_id=%s&note_id=%s' % (loan_id, order_id, note_id)


class Downloader(object):

    def __init__(self, username=None, password=None,
                 debug=False, naptime=True,
                 user_agent=DEFAULT_USER_AGENT):
        self.sleep_after_request = naptime
        self.user_agent = user_agent
        self.debug = debug

        # Try setting the username from args
        self.username = username
        self.password = password
        self.logged_in = False

        self.cookie_jar = CookieJar()
        if self.debug:
            # Noisy HTTPS handler for debugging
            self.url_opener = build_opener(
                HTTPCookieProcessor(self.cookie_jar),
                HTTPSHandler(debuglevel=1))
        else:
            self.url_opener = build_opener(
                HTTPCookieProcessor(self.cookie_jar))

        self.url_opener.addheaders = [
            ('User-Agent', self.user_agent)
        ]

        logging.info('Downloader intialized.')

    def open_url(self, url, data=None, method='GET'):
        """
        Consistent place to introduce request throttling
        and other HTTP magic
        """

        if method == 'GET':
            if data:
                url += "?" + urlencode(data, True)
            response = self.url_opener.open(url)

        elif method == 'POST':
            response = self.url_opener.open(url, data=urlencode(data))

        else:
            raise ValueError("%s is not a valid HTTP method" % method)

        if self.sleep_after_request:
            sleep_time = random.randint(MIN_SLEEP, MAX_SLEEP)
            logging.debug('Taking a nap for %s seconds', sleep_time)
            time.sleep(sleep_time)

        return response

    def verify_login(self, resp=None):
        """
        Tries to fetch the Account Summary page,
        returns true if it succeeds

        Args:
            resp (HTTPResponse, optional) -
                 reuse resp instead of re-querying

        Returns: True if the we're actually logged in;
                 also updates self.logged_in
        """

        if not resp:
            resp = self.open_url(ACCOUNT_SUMMARY_URL)

        resp_text = resp.read()

        # Look for a known tag that appears only for logged in users
        if resp_text.find(LOGGED_IN_VALIDATION) >= 0:
            self.logged_in = True
        else:
            self.logged_in = False

        return self.logged_in

    def logout(self):
        try:
            self.cookie_jar.clear('.lendingclub.com')
        except KeyError:
            pass

        logging.debug('Cleared cookies')

    def login(self, invalidate_session=False, retries=5):
        """ Sets an actively logged in session with Lending Club.

        Login Steps:
            1. Get a set of session cookies by visiting ACCOUNT_SUMMARY_URL
            2. Authenticate the session cookies with a username / password

        If self.logged_in is already set, this will verify that we're logged in

        Args:
            invalidate_session (bool): will clear cookies and
                log in with a new session.
            retries (int): number of times to retry on unsuccessful login

        Returns: True if login was successful, also updates self.logged_in

        """

        if self.logged_in and not invalidate_session and self.verify_login():
            # Ensure we're logged in and aren't trying to reset our session
            logging.debug('Ensuring that we already have an active session')
            return self.logged_in

        if not self.logged_in or invalidate_session:
            # Start a new session: clear cookies, and get send a fresh request
            self.logout()

            logging.debug('Starting a fresh Lending Club session..')
            self.open_url(ACCOUNT_SUMMARY_URL)
            logging.debug('session cookies: %s', self.cookie_jar)

        attempt = 1
        while attempt <= retries:

            # Username and password only need to input once
            if not self.username:
                self.username = raw_input('Lending Club username:\n')

            if not self.password:
                self.password = getpass('Password:\n')

            data = {
                'login_url': ACCOUNT_SUMMARY_URL,
                'login_email': self.username,
                'login_password': self.password,
                'login_remember_me': 'off',
            }

            response = self.open_url(LOGIN_URL, data, 'POST')

            # Validate the login attempt
            if self.verify_login(response):
                self.logged_in = True

                # We dont need the LC_FIRSTNAME cookie that was just set
                self.cookie_jar.clear('.lendingclub.com', '/', 'LC_FIRSTNAME')

                logging.info('Successfully logged in as %s', self.username)
                break

            else:
                self.username = None
                self.password = None
                self.logged_in = False
                if attempt < retries:
                    logging.warning(
                        'Login attempt %s of %s failed. Will try again.',
                        attempt, retries)
                else:
                    logging.critical('Last login attempt %s failed.', attempt)

                attempt += 1

        return self.logged_in

    def set_query_params(self):
        """
        Before making requests to NOTES_URL, we need to set the high-level
        search params, like the interest rates and loan status.

        Query params are associated with the session on the server-side.
        """

        request_params = {
            'mode': 'search',
            'search_from_rate': '0.04',
            'search_to_rate': '0.29',
            'fil_search_term':['term_36',
                               'term_60'],
            'search_loan_term':['term_36',
                                'term_60'],
            'opr_min':0.00,
            'opr_max':'Any',
            'loan_status':['loan_status_issued',
                           'loan_status_late_16_30',
                           'loan_status_current',
                           'loan_status_late_31_120',
                           'loan_status_ingrace'],
            'remp_min':1,
            'remp_max':60,
            'askp_min':0.00,
            'askp_max':'Any',
            'credit_score_min':600,
            'credit_score_max':850,
            'ytm_min':0,
            'ytm_max':'Any',
            'credit_score_trend':['UP',
                                  'DOWN',
                                  'FLAT'],
            'markup_dis_min':-100,
            'markup_dis_max':100,
            'ona_min':25,
            'ona_max':'Any'
        }
        logging.debug('Setting up the query params..')

        self.open_url(QUERY_PARAMS_URL, request_params)

    def get_page_of_notes(self, sort='opa', sort_dir='asc',
                          offset=0, limit=15, retries=5):
        """ Given a session cookie, get a page of results in a JSON format """

        request_params = {
            'sortBy': sort,
            'dir': sort_dir,
            'newrdnnum': random.randint(10000000, 90000000),  # What is this?
            'startindex': offset,
            'pagesize': limit,
        }

        QUERY_STATUS_KEY = 'result'

        attempt = 1
        while attempt <= retries:
            try:
                response = self.open_url(NOTES_URL, request_params)
                response_data = response.readline()
                json_data = json.loads(response_data)
                query_status = json_data.get(QUERY_STATUS_KEY)
                if query_status == 'success':
                    return json_data
            except Exception as e:
                log_line = '[%d/%d]: Error parsing response: %s\n RESP: %s' % (
                    attempt, retries, e, response_data)
                logging.warning(log_line)
            else:
                log_line = '[%d/%d] Failed to fetch data. \n RESP: %s' % (
                    attempt, retries, json_data)
                logging.warning(log_line)

            attempt += 1

        # Escalate logging to ERROR if we fail fetching after many retries
        logging.critical('Error fetching page of notes after %d tries.\n > %s',
                         retries, log_line)

        return {}

    def get_note_details(self, record, retries=2):
        request_params = {
            'loan_id': record.get('loanGUID'),
            'order_id': record.get('orderId'),
            'note_id': record.get('noteId'),
            'showfoliofn': 'true'
        }
        QUERY_STATUS_KEY = 'result'
        attempt = 1
        while attempt <= retries:
            try:
                response = self.open_url(NOTE_INFO_BASE_URL, request_params)
                response_page = response.read()
                note_parser = NoteHTMLParser(response_page)
                note_info = note_parser.get_info()
                query_status = note_info.get(QUERY_STATUS_KEY)
                if query_status == True:
                    return note_info
            except Exception as e:
                log_line = 'get_note_details: [%d/%d]: Error parsing response: %s\n RESP: %s' % (
                    attempt, retries, e, response_data)
                logging.warning(log_line)
            else:
                log_line = 'get_note_details: [%d/%d] Failed to fetch data for record %s \n RESP: %s' % (
                    attempt, retries, record, note_info)
                logging.warning(log_line)

            attempt += 1
        # Escalate logging to ERROR if we fail fetching after many retries
        logging.critical('Error fetching page of notes after %d tries.\n > %s',
                         retries, log_line)

        return {}

    def get_loan_details(self, record, retries=2):
        request_params = {
            'loan_id': record.get('loanGUID')
        }
        QUERY_STATUS_KEY = 'result'
        attempt = 1
        while attempt <= retries:
            try:
                response = self.open_url(LOAN_INFO_BASE_URL, request_params)
                response_page = response.read()
                loan_parser = LoanHTMLParser(response_page)
                loan_info = loan_parser.get_info()
                query_status = loan_info.get(QUERY_STATUS_KEY)
                if query_status == True:
                    return loan_info
            except Exception as e:
                log_line = 'get_loan_details: [%d/%d]: Error parsing response: %s\n RESP: %s' % (
                    attempt, retries, e, response_data)
                logging.warning(log_line)
            else:
                log_line = 'get_loan_details: [%d/%d] Failed to fetch data for record %s \n RESP: %s' % (
                    attempt, retries, record, loan_info)
                logging.warning(log_line)

            attempt += 1
        # Escalate logging to ERROR if we fail fetching after many retries
        logging.critical('Error fetching page of notes after %d tries.\n > %s',
                         retries, log_line)

        return {}

    def format_record_detail(self, note_id, note_detail, loan_detail):
        formated = loan_detail
        formated['note_id'] = note_id
        formated.update(note_detail)
        return formated

    def download_note_details(self, mongo_manager, pagesize=250):
        """ download note details from lc using records stored in mongo_manager 
        """
        
        logging.info('Fetching records from mongo_manager')

        all_record_ids = mongo_manager.get_records()

        total_record_count = len(all_record_ids)

        logging.info('Fetched %s record', total_record_count)

        self.login()
        logging.info('Start downloading at %s' % str(datetime.now()))
        
        count = 1
        page_record_details = {}
        start_time = time.time()

        for note_id, record_ids in all_record_ids.iteritems():

            note_detail = self.get_note_details(record_ids)
            loan_detail = self.get_loan_details(record_ids)
            record_detail = self.format_record_detail(note_id, note_detail, loan_detail)
            page_record_details[note_id] = record_detail
        
            if (count % pagesize == 0):
                mongo_manager.add_note_details(page_record_details)
                logging.info('Fetched %s records, %.2f mins elapsed..', count, (time.time() - start_time)/60)
                page_record_details = {}
                time.sleep(1)

            count = count+1
        # end loop of record

        logging.info('Fetched %s records; download complete at %s. %.2f min elapsed.', 
                     count, str(datetime.now()), (time.time() - start_time)/60)

    def download_data(self, max_records=250, pagesize=250, mongo_manager=None, download_details=True):
        """ Paginate through enough pages of results to get the desired
        number of records. Optionally ignore negative YTM to reduce
        the result set.
        """

        RECORD_COUNT_KEY = 'totalRecords'
        RESULT_SET_KEY = 'searchresult'
        LOANS_KEY = 'loans'

        # ensure we're logged in
        self.login()

        # Set the high-level search query params
        self.set_query_params()

        # How many results match the query?
        logging.info('Fetching the total matching record count for the query')

        total_record_count = int(
            self.get_page_of_notes(limit=1).get(RECORD_COUNT_KEY, 0))

        # How many results do we plan to fetch?
        record_limit = min(max_records, total_record_count)
        logging.info('Fetching up to %s of %s matching records',
                     record_limit, total_record_count)

        all_records = {}
        records_set = Set()

        offset = 0

        logging.info('Start downloading at %s' % str(datetime.now()))
        start_time = time.time()

        while offset < record_limit:
            
            logging.debug('Fetched %s; getting %s more records from the site',
                          len(records_set), pagesize)

            # Set the query arguments and fetch the data in a nice dict
            query_args = {'offset': offset, 'limit': pagesize, }

            fetched_data = self.get_page_of_notes(**query_args)

            # Break out early if we're not getting sensible results
            if not fetched_data:
                break

            # Get a list of records from the result
            fetched_records = fetched_data.get(
                RESULT_SET_KEY, {}).get(LOANS_KEY, [])
            
            page_record_details = {}
            page_record_ids = {}

            for record in fetched_records:

                note_id = record.get('noteId')
                if note_id in records_set:
                    logging.warning('Looks like we got a duplicate record: %s', record)

                if mongo_manager :
                    if (download_details):
                        note_detail = self.get_note_details(record)
                        loan_detail = self.get_loan_details(record)
                        record_detail = self.format_record_detail(note_id, note_detail, loan_detail)
                        page_record_details[note_id] = record_detail
                    else:
                        record_ids = {}
                        record_ids['loan_id'] = record.get('loanGUID')
                        record_ids['order_id'] = record.get('orderId')
                        record_ids['note_id'] = record.get('noteId')
                        page_record_ids[note_id] = record_ids
                else:
                    all_records[note_id] = record

                records_set.add(note_id)
            # end loop of record

            if mongo_manager :
                if (download_details):
                    mongo_manager.add_note_detail(page_record_details)
                else:
                    mongo_manager.add_note_ids(page_record_ids)

            offset += pagesize
        # end loop of pages

        logging.info('Fetched %s records; download complete at %s. %.2f min elapsed.', 
                     len(records_set), str(datetime.now()), (time.time() - start_time)/60)

        return all_records

    def download_historical_loan_data(self):
        logging.info('Downloading file from %s..', LOAN_DATA_CSV_URL)
        urlretrieve(LOAN_DATA_CSV_URL, LOAN_DATA_CSV_TMPFILE)
        logging.info('Done writing to %s', LOAN_DATA_CSV_TMPFILE)
        return parse_loan_data_from_file(LOAN_DATA_CSV_TMPFILE)
