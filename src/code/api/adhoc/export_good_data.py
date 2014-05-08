"""
Because of how Python looks for modules, running this batch from the repository
root will fail with import errors.

To get around this, the repo-root directory must be added to the PYTHONPATH:

 PYTHONPATH=`pwd` ipython adhoc/export_good_data.py -i
"""

from data_model import parse_timestamp_from_date
from mongo_manager import MongoManager

start_time = parse_timestamp_from_date('2013-08-13')
end_time = parse_timestamp_from_date('2013-09-10')

mm = MongoManager()

good_data = mm.db.orders.find(
    {'$and': [
        {'first_seen': {'$gte': start_time}},
        {'last_seen': {'$lt': end_time}},
    ]})
