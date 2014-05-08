import re
import csv
import logging

from datetime import datetime


def consolidate_price_history(history):

    new_history = []

    for i in range(len(history)):
        if i == 0 or i == len(history) - 1:
            new_history.append(history[i])
        else:
            prev_price, prev_time = history[i-1]
            price, time = history[i]
            next_price, next_time = history[i+1]

            if prev_price != price or next_price != price:
                new_history.append(history[i])

    return new_history

"""

    Parsers for the LoanStatsData.csv from lendingclub site

"""


def parse_timestamp_from_date(yyyy_mm_dd):
    yyyy_mm_dd = yyyy_mm_dd.split(' ')[0]
    return int(datetime.strptime(yyyy_mm_dd, '%Y-%m-%d').strftime('%s'))


def parse_payment_plan(pymnt_plan):
    return pymnt_plan == 'y'


def parse_verified_income(is_inc_v):
    return is_inc_v == 'TRUE'


def parse_term(term):
    """ ' 36 months' -> 36 """
    return int(term.strip().split(' ')[0])


def parse_percentge(percentage):
    """ '49.01%' -> 49.01 """
    return float(percentage.strip()[:-1])


def parse_loan_status(loan_status):

    # Some entries are prefixed with a warning like this:
    credit_policy_re = re.compile(
        'does not meet the (current )?credit policy.( )+status:', re.I)

    if loan_status and loan_status != '':
        if credit_policy_re.search(loan_status):
            # We dont really care about the credit policy, so we strip it
            loan_status = credit_policy_re.sub('', loan_status)

        loan_status = loan_status.lower()
        if loan_status in KNOWN_STATUSES:
            return loan_status
        else:
            logging.warning("unknown loan_status: %s", loan_status)
            return "unknown status"
    return None


def parse_loan_data_dict(loan_data):
    try:
        loan_data['loanGUID'] = int(loan_data['id'])
    except Exception:
        logging.warning("error setting loanGUID, skipping: %s", loan_data)
        return

    # Convert string fields into better types
    type_converters = [
        (LOAN_STATS_INT_FIELDS, int),
        (LOAN_STATS_FLOAT_FIELDS, float),
        (LOAN_STATS_PERCENT_FIELDS, parse_percentge),
        (LOAN_STATS_STR_FIELDS, str),
        (LOAN_STATS_DATE_FIELDS, parse_timestamp_from_date),
    ]

    for type_fields, converter_fn in type_converters:

        for field in type_fields:
            if (loan_data.get(field) and
                    loan_data[field] != '' and
                    loan_data[field] != 'null'):
                try:
                    loan_data[field] = converter_fn(loan_data[field])
                except ValueError:
                    logging.warning("Error converting field %s (%s)",
                                    field, loan_data[field])
                    loan_data[field] = None
            else:
                loan_data[field] = None

    # Parse custom fields
    loan_data['pymnt_plan'] = parse_payment_plan(loan_data.get('pymnt_plan'))
    loan_data['is_inc_v'] = parse_verified_income(loan_data.get('is_inc_v'))
    loan_data['loan_status'] = parse_loan_status(loan_data.get('loan_status'))
    loan_data['term'] = parse_term(loan_data.get('term'))

    return loan_data


def parse_loan_data_from_file(csv_file):

    id_to_loan_data = {}

    logging.info("Parsing %s", csv_file)
    with open(csv_file, 'r') as csv_data:

        # skip the useless line about the prospectus
        csv_data.readline()

        reader = csv.DictReader(csv_data)

        for row in reader:
            try:
                loan_id = int(row['id'])
            except ValueError:
                logging.info(
                    "skipping row with non-numeric id: %s", row['id'])
            else:
                id_to_loan_data[loan_id] = parse_loan_data_dict(row)

            if len(id_to_loan_data) % 10000 == 0:
                logging.info("parsed %s records", len(id_to_loan_data))

        logging.info("fetched historical data for %s loans",
                     len(id_to_loan_data))

    return id_to_loan_data

KNOWN_STATUSES = [
    'issued',
    'current',
    'in grace period',
    'late (16-30 days)',
    'late (31-120 days)',
    'fully paid',
    'default',
    'charged off',
]

LOAN_STATS_INT_FIELDS = [
    "id",
    "member_id",

    "acc_now_delinq",
    "acc_open_past_24mths",
    "delinq_2yrs",
    "inq_last_6mths",
    "fico_range_low",
    "fico_range_high",
    "last_fico_range_high",
    "last_fico_range_low",
    "mths_since_last_delinq",
    "mths_since_last_record",
    "mths_since_recent_inq",
    "mths_since_recent_loan_delinq",
    "mths_since_recent_revol_delinq",
    "mths_since_recent_bc",
    "mort_acc",
    "open_acc",
    "pub_rec_gt_100",
    "pub_rec",
    "tax_liens",
    "mths_since_oldest_il_open",
    "num_rev_accts",
    "mths_since_recent_bc_dlq",
    "pub_rec_bankruptcies",
    "num_accts_ever_120_pd",
    "chargeoff_within_12_mths",
    "collections_12_mths_ex_med",
    "mths_since_last_major_derog",
    "num_sats",
    "num_tl_op_past_12m",
    "mo_sin_rcnt_tl",
    "num_bc_tl",
    "num_actv_bc_tl",
    "num_bc_sats",
    "num_tl_90g_dpd_24m",
    "num_tl_30dpd",
    "num_tl_120dpd_2m",
    "num_il_tl",
    "mo_sin_old_il_acct",
    "num_actv_rev_tl",
    "mo_sin_old_rev_tl_op",
    "mo_sin_rcnt_rev_tl_op",
    "num_rev_tl_bal_gt_0",
    "num_op_rev_tl",
]

LOAN_STATS_PERCENT_FIELDS = [
    "revol_util",
    "apr",
    "int_rate",
]

LOAN_STATS_FLOAT_FIELDS = [
    "loan_amnt",
    "funded_amnt",
    "funded_amnt_inv",
    "installment",
    "annual_inc",
    "bc_util",
    "dti",
    "bc_open_to_buy",
    "percent_bc_gt_75",  # percent of credit cards > 75% utilization
    "total_bal_ex_mort",
    "revol_bal",
    "total_bc_limit",

    "out_prncp",
    "out_prncp_inv",  # what is inv?
    "total_pymnt",
    "total_pymnt_inv",  # what is inv?

    "total_acc",
    "total_rec_prncp",
    "total_rec_int",
    "total_rec_late_fee",
    "last_pymnt_amnt",
    "total_il_high_credit_limit",
    "tot_hi_cred_lim",
    "tot_cur_bal",
    "avg_cur_bal",
    "pct_tl_nvr_dlq",
    "total_rev_hi_lim",
    "tot_coll_amt",
]

LOAN_STATS_STR_FIELDS = [
    "grade",  # should this be enum?
    "sub_grade",
    "emp_name",
    "emp_length",
    "home_ownership",
    "url",  # useless?
    "desc",  # useless?
    "purpose",  # standardized
    "title",
    "addr_city",
    "addr_state",
]

LOAN_STATS_DATE_FIELDS = [
    "accept_d",
    "exp_d",
    "list_d",
    "issue_d",
    "earliest_cr_line",
    "next_pymnt_d",
    "last_credit_pull_d",
    "last_pymnt_d",
]


LOAN_STATS_CUSTOM_FIELDS = [
    "is_inc_v",  # TRUE / FALSE
    "pymnt_plan",  # n / y
    "loan_status",  # FULLY PAID / other
    "initial_list_status",  # f / w ?
]
