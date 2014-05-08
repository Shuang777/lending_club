#!python
# -*- coding: utf-8 -*-

"""
Downloader Data Converter
"""

__author__ = "Marion"
__email__ = "kangarup@gmail.com"
__version__ = "1.0"


import json
import os

class Converter(object):
	"""Converter for Downloader Data"""

	def __init__(self,  conf_file_name='lc_conf'):
		self.classes = self.read_conf(conf_file_name)

	def read_conf(self, conf_file_name='lc_conf'):
		""" Retreive parameters from the Stats configuration file """
		script_dir = os.path.dirname(os.path.abspath(__file__))

		try:
			execfile("%s/%s" % (script_dir, conf_file_name), globals())
		except IOError, error:
			print "Configuration file %s not found: %s " % (conf_file_name, repr(error))
			exit(1)
		try:
		 	classNominalValues = globals()["CLASS_NOMINAL_VALUES"]
			return 	classNominalValues
		except KeyError, error:
			print "Missing key %s in the configufation file"

	def loadDataFromFile(self, filePath):
		""" Load Downloader data from file """
		f = open(filePath, 'r')
		return json.load(f)


	def convertData(self, dataToConvert):
		""" 
		Convert Raw Downloader data.

		In the old dataset the key 'price_history' is an array, whereas it'd be more interesting
		to have a seperate entry in the dataset every time this value changes.
		But in the new dataset, every time the price hirtory is chnaging, a new entry is added.

		@param dataToConvert the json data from Downloader API

		@return convertedData json file with converted data
		"""

		convertedData = []

		for datapoint in dataToConvert:

			# the triple (loanGUID, noteId, orderId) is unique for each note
			newId = "%s-%s-%s" %(datapoint['loanGUID'] , datapoint['noteId'], datapoint['orderId'])

			# time one market is the duration between when the note was first and last seen
			timeOnMarket =  float(datapoint['last_seen']) - float(datapoint['first_seen'])

			# 7 days (in s) is the max a note can be on the market
			maxTimeOnMarket = 7 * 24  * 3600 # 168 hours is 7 days


			# convert price history and gnenerate new data points
			notePriceHistory = datapoint['price_history']
			for pricePoint in notePriceHistory:
				newDatapoint = {}

				# numeric attributes
				newDatapoint['id'] = newId
				newDatapoint['timestamp'] = pricePoint[1]
				newDatapoint['notePrice'] = pricePoint[0]
				newDatapoint['timeOnMarket'] = timeOnMarket / 3600
				newDatapoint['loanRate'] = datapoint['loanRate']
				newDatapoint['outstanding_principal'] = datapoint['outstanding_principal']
				newDatapoint['days_since_payment'] = datapoint['days_since_payment']
				newDatapoint['ytm'] = datapoint['ytm']
				newDatapoint['credit_score_trend'] = datapoint['credit_score_trend']
				newDatapoint['markup_discount'] = datapoint['markup_discount']
				newDatapoint['asking_price'] = datapoint['asking_price']
				newDatapoint['accrued_interest'] = datapoint['accrued_interest']
				newDatapoint['remaining_pay'] = datapoint['remaining_pay']
				
				#nominal attribute
				newDatapoint['loanGrade'] = datapoint['loanGrade']


				# 'noteStatus' is the class attribute.
				# - NB : Not Bought
				# - 'NBY' : Not Bought Yet
				# - 'B' : Bought
				# - 'C' : Cancelled
				# The conditions below are a proxy to know whether a note was bought or not.
				pricePointTimestamp = pricePoint[1] 
				dontAppend = False
				if (timeOnMarket < maxTimeOnMarket):
					if pricePointTimestamp == datapoint['last_seen']:
						if timeOnMarket == 0:
							noteStatus = 'C'
						else:
							noteStatus = 'B'
					else:
						noteStatus = 'NBY'
				else:
					noteStatus = 'NB'
					
				if noteStatus in self.classes:
					newDatapoint['noteStatus'] = noteStatus
					convertedData.append(newDatapoint)

		return convertedData


	def convertDataFromFile(self, fileToConvert):
		""" Load file and converter Downloader data """
		dataToConvert = self.loadDataFromFile(fileToConvert)
		return self.convertData(dataToConvert)

	def dumpData(self, data, filePath):
		""" Dumps data to file """

		file = open (filePath, 'w')
		file.write(json.dumps(data))
		file.close()







