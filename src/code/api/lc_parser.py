from HTMLParser import HTMLParser

import re

def map_message(data):
    if (re.search(r'no message left|no voicemail', data)):
        return 'no message left'
    elif (re.search(r'message left|left voicemail', data)):
        return 'message left'
    elif (re.search(r'legal action', data)):
        return 'legal action'
    elif (re.search(r'Initial payment reminder|email sent|[Ss]ent email', data)):
        return 'payment reminder'
    elif (re.search(r'[Bb]orrower (contacted|informed) | promised', data)):
        return 'borrower contact'
    else:
        return data

class NoteHTMLParser(HTMLParser):
    def __init__(self, page):
        HTMLParser.__init__(self)
        self.stage = 0
        self.scores = []
        self.dates = []
        self.duedates = []
        self.balances = []
        self.status = []
        self.contact_dates = []
        self.messages = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        if (self.stage == 0 and tag == "table"):
            for attr in attrs:
                if (attr[0] == "id" and attr[1] == "trend-data"):
                    self.stage = 1
        elif (self.stage == 1 and tag == "tbody"):
            self.stage = 11
        elif (self.stage == 11 and tag == "tr"):
            self.stage = 110
        elif (self.stage >= 110 and self.stage <= 112 and tag == "td"):
            self.stage = self.stage + 1

        if (self.stage == 0 and tag == "div"):
            for attr in attrs:
                if (attr[0] == "id" and attr[1] == "lcLoanPerf1"):
                    self.stage = 2
        elif (self.stage == 2 and tag == "tbody"):
            self.stage = 21
        elif (self.stage == 21 and tag == "tr"):
            self.stage = 210
            for attr in attrs:
                if (attr[0] == "style" and attr[1] == "display: none;"):
                    self.stage = 21
        elif (self.stage >= 210 and self.stage <= 228): # assume tag == "td", but may have other info
            self.stage = self.stage + 1

        if (self.stage == 0 and tag == "table"):
            for attr in attrs:
                if (attr[0] == "id" and attr[1] == "lcLoanPerfTable2"):
                    self.stage = 3
        elif (self.stage == 3 and tag == "tbody"):
            self.stage = 31
        elif (self.stage == 31 and tag == "tr"):
            self.stage = 310
        elif (self.stage >= 310 and self.stage <= 313 and tag == "td"):
            self.stage = self.stage + 1

    def handle_data(self, data):
        if (self.stage == 111):
            self.scores.append(data)
        elif (self.stage == 113):
            self.dates.append(data)
        
        elif (self.stage == 211):
            self.duedates.append(data)
        elif (self.stage == 221):
            self.balances.append(data)
        elif (self.stage == 227):
            self.status.append(data.strip())

        elif (self.stage == 311):
            self.contact_dates.append(data.split(' ', 1)[0])
        elif (self.stage == 313):
            self.messages.append(map_message(data))

    def handle_endtag(self, tag):
        if (self.stage >= 111 and self.stage <= 113 and tag == "td"):
            self.stage = self.stage + 1
        elif (self.stage == 114 and tag == "tr"):
            self.stage = 11
        elif (self.stage == 11 and tag == "tbody"):
            self.stage = 0

        elif (self.stage >= 211 and self.stage <= 229 and tag == "td"):
            self.stage = self.stage + 1
        elif (self.stage == 230 and tag == "tr"):
            self.stage = 21
        elif (self.stage == 21 and tag == "tbody"):
            self.stage = 0

        elif (self.stage >= 311 and self.stage <= 313 and tag == "td"):
            self.stage = self.stage + 1
        elif (self.stage == 314 and tag == "tr"):
            self.stage = 31
        elif (self.stage == 31 and tag == "tbody"):
            self.stage = 0

    def get_info(self):
        result = True
        if (len(self.scores) != len(self.dates) or 
            len(self.duedates) != len(self.balances) or
            len(self.duedates) != len(self.status) or 
            len(self.contact_dates) != len(self.messages) or
            len(self.scores) == 0 or
            len(self.duedates) == 0):
            result = False

        credit_history = []
        for score, date in zip(self.scores, self.dates):
            credit_history.append((score, date))
        payment_history = []
        for duedate, balance, status in zip(self.duedates, self.balances, self.status):
            payment_history.append((duedate, balance, status))
        contact_history = []
        for date, message in zip(self.contact_dates, self.messages):
            contact_history.append((date, message))
        
        history = {}
        history['credit_history'] = credit_history
        history['payment_history'] = payment_history
        history['contact_history'] = contact_history
        history['result'] = result
        return history

class LoanHTMLParser(HTMLParser):
    def __init__(self, page):
        HTMLParser.__init__(self)
        self.stage = 0
        self.loan_details = {}
        self.profile = {}
        self.credit = {}
        self.feed(page)
    def handle_starttag(self, tag, attrs):
        if (self.stage == 0 and tag == "table"):
            for attr in attrs:
                if (attr[0] == "class" and attr[1] == "loan-details"):
                    self.stage = 1
        elif (self.stage == 3 and tag == "h3"):
            for attr in attrs:
                if (attr[0] == "class" and attr[1] == "profile_title master_pngfix"):
                    self.stage = 4
                if (attr[0] == "class" and attr[1] == "credit_history_title master_pngfix"):
                    self.stage = 5
        elif (self.stage == 1 and tag == "tr"):
            self.stage = 11
        elif (self.stage == 11 and tag == "div"):
            for attr in attrs:
                assert(attr[0] == "class" and attr[1] == "amountRequested")
            self.stage = 111
        elif (self.stage == 111 and tag == "div"):
            self.stage = 1111
        elif (self.stage >= 12 and self.stage <= 21 and tag == "tr"):
            self.stage = self.stage * 10 + 1
        elif ((self.stage == 121 or self.stage/10 >= 14 and self.stage/10 <= 21) and tag == "td"):
            self.stage = self.stage * 10 + 1
        elif (self.stage == 131 and tag == "span"):
            self.stage = 1311
            
        elif (self.stage >=41 and self.stage <= 46 and tag == "tr"):        # tr under profile
            self.stage = self.stage * 10 + 1
        elif (self.stage/10 >= 41 and self.stage/10 <= 46 and tag == "td"):     # td under profile tr
            self.stage = self.stage * 10 + 1
            
        elif (self.stage == 5 and tag == "table"):
            self.stage = 51
        elif (self.stage >= 51 and self.stage <= 65 and tag == "tr"):
            self.stage = self.stage * 10 + 1
        elif (self.stage/10 >= 51 and self.stage/10 <= 65 and tag == "td"):
            self.stage = self.stage * 10 + 1
    def handle_data(self, data):
        if (self.stage == 1111):
            self.loan_details['amount_request'] = data.strip()
        elif (self.stage == 1211):
            self.loan_details['purpose'] = data.strip()
        elif (self.stage == 1311):
            self.loan_details['grade'] = data.strip()
        elif (self.stage == 1411):
            self.loan_details['interest_rate'] = data.strip()
        elif (self.stage == 1511):
            self.loan_details['length'] = data.strip()
        elif (self.stage == 1611):
            self.loan_details['payment'] = data.strip()
        elif (self.stage == 1711):
            self.loan_details['received'] = data.strip()
        elif (self.stage == 1811):
            self.loan_details['investors'] = data.strip()
        elif (self.stage == 1911):
            self.loan_details['issue_time'] = data.strip()
        elif (self.stage == 2011):
            self.loan_details['status'] = data.strip()
        elif (self.stage == 2111):
            self.loan_details['submitted_time'] = data.strip()
        if (self.stage/100 >= 11 and self.stage/100 <= 21):
            self.stage = self.stage / 100 + 1
        if (self.stage == 4):
            self.profile['member_id'] = data.strip()
            self.stage = 41
        elif (self.stage == 4111):
            self.profile['home_ownership'] = data.strip()
        elif (self.stage == 4211):
            self.profile['job'] = data.strip()
        elif (self.stage == 4311):
            self.profile['length_of_employment'] = data.strip()
        elif (self.stage == 4411):
            self.profile['gross_income'] = data.strip()
        elif (self.stage == 4511):
            self.profile['debt_to_income'] = data.strip()
        elif (self.stage == 4611):
            self.profile['location'] = data.strip()
        if (self.stage/100 >= 41 and self.stage/100 <= 46):
            self.stage = self.stage / 100 + 1
            
        if (self.stage == 5111):
            self.credit['score_range'] = data.strip()
        elif (self.stage == 5211):
            self.credit['earliest_credit_line'] = data.strip()
        elif (self.stage == 5311):
            self.credit['open_credit_line'] = data.strip()
        elif (self.stage == 5411):
            self.credit['total_credit_line'] = data.strip()
        elif (self.stage == 5511):
            self.credit['revolving_balance'] = data.strip()
        elif (self.stage == 5611):
            self.credit['revolving_utilization'] = data.strip()
        elif (self.stage == 5711):
            self.credit['inquiries_last_6month'] = data.strip()
        elif (self.stage == 5811):
            self.credit['accounts_delinquent'] = data.strip()
        elif (self.stage == 5911):
            self.credit['delinquent_amount'] = data.strip()
        elif (self.stage == 6011):
            self.credit['delinquencies_last_2year'] = data.strip()
        elif (self.stage == 6111):
            self.credit['months_last_delinquency'] = data.strip()
        elif (self.stage == 6211):
            self.credit['public_records'] = data.strip()
        elif (self.stage == 6311):
            self.credit['months_last_record'] = data.strip()
        elif (self.stage == 6411):
            self.credit['months_last_derogatory'] = data.strip()
        elif (self.stage == 6511):
            self.credit['collections_excluding_medical'] = data.strip()
        if (self.stage/100 >= 51 and self.stage/100 <= 65):
            self.stage = self.stage / 100 + 1
            
    def handle_endtag(self, tag):
        if ((self.stage == 22 or self.stage == 47 or self.stage == 66) and tag == "table"):
            self.stage = 3

    def get_info(self):
        result = True
        if (not self.loan_details or
            not self.profile or
            not self.credit):
            result = False

        info = {}
        info['loan_details'] = self.loan_details
        info['profile'] = self.profile
        info['credit'] = self.credit
        info['result'] = result
        return info

if __name__ == '__main__':
    import urllib
    loan_page = urllib.urlopen("loan.html").read()
    loan_parser = LoanHTMLParser(loan_page)
    loan_info = loan_parser.get_info()
    print loan_info
    print loan_info.get('result')

    note_page = urllib.urlopen("note.html").read()
    note_parser = NoteHTMLParser(note_page)
    note_info = note_parser.get_info()
    print note_info
    print note_info.get('result')
