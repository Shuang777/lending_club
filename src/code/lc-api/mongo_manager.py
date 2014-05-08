from pymongo import MongoClient

import time
import logging
import pprint

from data_model import consolidate_price_history
from downloader import build_note_info_url

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DBNAME = 'lendingclub'
UPDATE_ERROR_CRITICAL_THRESHOLD = 10  # Threshold for CRITICAL log entry


class NoteConstantFieldsChangedError(ValueError):
    pass


class MongoManager(object):
    def __init__(self, host=MONGO_HOST, port=MONGO_PORT, dbname=MONGO_DBNAME):
        self.client = MongoClient(host, port)
        self.db = self.client[dbname]

    def update_loans(self, all_loans):

        logging.info("Dropping all of the existing loan records")
        self.db.loans.remove({})

        update_time = time.time()

        counter = 0
        for loan_id, loan in all_loans.iteritems():
            loan['last_updated'] = update_time
            self.db.loans.insert(loan)

            counter += 1
            if counter % 5000 == 0:
                logging.debug(".. wrote %s records", counter)

    def update_orders(self, all_orders):

        logging.info("Writing to MongoDB")

        update_time = time.time()

        orders_updated = 0
        error_count = 0
        for order_id, order in all_orders.iteritems():
            try:
                self.update_order_from_dict(order, update_time)
                orders_updated += 1
            except NoteConstantFieldsChangedError as e:
                logging.warning(e.message)
                error_count += 1

            if orders_updated % 5000 == 0:
                logging.debug(".. wrote %s records", orders_updated)

        if error_count > UPDATE_ERROR_CRITICAL_THRESHOLD:
            # Send an email if too many errors occured
            logging.critical(
                "UPDATE_ERROR_CRITICAL_THRESHOLD (%d) exceeded: "
                "There were %d errors updating orders.",
                UPDATE_ERROR_CRITICAL_THRESHOLD, error_count)

    def update_order_from_dict(self, order_data, update_time):

        # Assume these fields do not change over time for (order, note, loan)
        const_fields = ['loanGrade', 'loanRate', 'loanClass']

        existing_order = self.db.orders.find_one({
            'noteId': order_data['noteId'],
            'loanGUID': order_data['loanGUID'],
            'orderId': order_data['orderId'],
            })

        new_order = order_data.copy()

        if existing_order:
            # UPDATE: preserve _id, first_seen, and price_history
            new_order['_id'] = existing_order['_id']
            new_order['first_seen'] = existing_order['first_seen']
            new_order['price_history'] = \
                existing_order.get('price_history', [])

            # Sanity check: constant fields should not change
            if any(existing_order[f] != order_data[f] for f in const_fields):

                # If they have, log a detailed error and skip the write
                error_msg = (
                    'Constant fields on an order have changed!\n' +
                    'Note Info URL:%s\n' % build_note_info_url(
                        order_data['noteId'],
                        order_data['loanGUID'],
                        order_data['orderId']) +
                    'Mismatching records: \n%s\n%s\n' % (
                        pprint.pformat(existing_order),
                        pprint.pformat(order_data)) +
                    'Skipping write.')

                raise NoteConstantFieldsChangedError(error_msg)

        else:
            # CREATE: initialize a new order's first_seen and price_history
            new_order['first_seen'] = update_time
            new_order['price_history'] = []

        # update last_seen and price_history for all orders
        new_order['last_seen'] = update_time
        new_order['price_history'].append(
            [new_order['asking_price'], update_time])

        new_order['price_history'] = \
            consolidate_price_history(new_order['price_history'])

        self.db.orders.save(new_order)

    def get_all_orders(self):
        return list(self.db.orders.find({}))

    def get_market_volumes(self, start_time, end_time, interval_sec=60*60):

        volume_buckets = []

        while start_time + interval_sec <= end_time:
            records_added_in_time_period = self.db.orders.find(
                {'$and': [
                    {'first_seen': {'$gte': start_time}},
                    {'first_seen': {'$lt': start_time + interval_sec}},
                ]}).count()
            records_removed_in_time_period = self.db.orders.find(
                {'$and': [
                    {'last_seen': {'$gte': start_time}},
                    {'last_seen': {'$lt': start_time + interval_sec}},
                ]}).count()
            volume_buckets.append({
                'records_added': records_added_in_time_period,
                'records_removed': records_removed_in_time_period,
                'period_start': start_time,
                'period_end': start_time + interval_sec,
            })

            start_time += interval_sec

        return volume_buckets
