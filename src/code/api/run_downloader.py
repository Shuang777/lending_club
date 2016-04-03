import argparse
import csv
import datetime
import time
import logging

from lc_logging import init_logging
from downloader import Downloader
from mongo_manager import MongoManager

def weka_friendly(record):
    """ Weka is finicky and doesnt like certain characters, so clean them up

    Params: record (dict) - string values won't include weka-breaking chars

    """
    WEKA_CANT_READ_THIS = ["'", '"', '%']
    for k, v in record.iteritems():
        if v is None or v == 'null':
            record[k] = 0
        elif isinstance(v, basestring):
            for c in WEKA_CANT_READ_THIS:
                if c in v:
                    v = v.replace(c, '')
            record[k] = v
    return record


def write_csv(data_dict, filename):
    list_of_records = data_dict.values()
    if not data_dict or len(data_dict) == 0:
        logging.warning('No data to write!')

    with open(filename, 'wb') as f:
        writer = csv.DictWriter(f, list_of_records[0].viewkeys(),
                                quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        for record in list_of_records:
            try:
                writer.writerow(weka_friendly(record))
            except UnicodeEncodeError:
                logging.warning('Skipping a CSV row because unicode is hard')


def parse_commandline_args():
    arg_parser = argparse.ArgumentParser(
        description='Welcome to Lending Club!')
    arg_parser.add_argument(
        '--max-records', metavar='n', type=int, default=1000000)
    arg_parser.add_argument(
        '--page-size', metavar='p', type=int, default=10)
    arg_parser.add_argument(
        '--filename', metavar='o', type=str)
    arg_parser.add_argument(
        '--config', metavar='c', type=str, default='lendingclub.conf')
    arg_parser.add_argument(
        '--username', metavar='u', type=str)
    arg_parser.add_argument(
        '--password', metavar='P', type=str)
    arg_parser.add_argument(
        '--action', metavar='a', type=str, default='update_orders')
    arg_parser.add_argument('--debug', action='store_true')
    arg_parser.add_argument('--skip-db', action='store_true')
    arg_parser.add_argument('--download-details', type=bool, default=False)

    return arg_parser.parse_args()


def run():

    args = parse_commandline_args()
    init_logging(args.config)

    logging.info(' ---------- ')
    logging.info(' started downloader with action: %s', args.action)
    logging.info(' ---------- ')
    
    if args.action == "download_notes":
        mm = MongoManager()
        downloader = Downloader(username=args.username,
                                password=args.password,
                                debug=args.debug)

        downloader.download_data(
            max_records=args.max_records,
            pagesize=args.page_size,
            mongo_manager=mm,
            download_details=args.download_details)

    elif args.action == "download_note_details":
        mm = MongoManager()
        downloader = Downloader(username=args.username,
                                password=args.password,
                                debug=args.debug)

        downloader.download_note_details(mm, pagesize=args.page_size)

    elif args.action == "update_orders":
        downloader = Downloader(username=args.username,
                                password=args.password,
                                debug=args.debug)

        orders = downloader.download_data(
            max_records=args.max_records,
            pagesize=args.page_size)

        logging.info('%s records fetched', len(orders))

        if not args.skip_db:
            mm = MongoManager()
            mm.update_orders(orders)
            logging.info('%s orders updated in mongo', len(orders))
        
        if args.filename:
            write_csv(orders, args.filename)
            logging.info('finished writing to %s', args.filename)

    elif args.action == "update_loans":
        downloader = Downloader()
        loans = downloader.download_historical_loan_data()
    
        if not args.skip_db:
            mm = MongoManager()
            mm.update_loans(loans)
            logging.info('%s loans updated in mongo', len(loans))

    elif args.action == "show_volumes":
        mm = MongoManager()
        start = time.time() - 2*7*24*60*60  # show last two weeks of data
        end = time.time() - 60*60  # omit the last hour
        volumes = mm.get_market_volumes(start, end)
        for v in volumes:
            mytime = datetime.datetime.fromtimestamp(v['period_start']).ctime()

            print '[%s] +%d / -%d' % (
                mytime,
                v['records_added'],
                v['records_removed'])
    else:
        logging.error('unknown action: %s', args.action)

if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        logging.exception(e)
