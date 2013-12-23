#!python
# -*- coding: utf-8 -*-

"""
Downloader Data Converter
"""

__author__ = "Marion"
__email__ = "kangarup@gmail.com"
__version__ = "1.0"


import json

class Converter(object):
	"""Converter for Downloader Data"""


	def __init__(self):
		super(Converter, self).__init__()

	def loadDataFromFile(self, filePath):
		""" Load Downloader data from file """
		f = open(filePath, 'r')
		return json.load(f)


	def convertData(self, dataToConvert, includeNBY):
		""" 
		Convert Raw Downloader data.

		In the old dataset the key 'price_history' is an array, whereas it'd be more interesting
		to have a seperate entry in the dataset every time this value changes.
		But in the new dataset, every time the price hirtory is chnaging, a new entry is added.

		@param dataToConvert the json data from Downloader API
		@param includeNBY Boolean to include NBY notes or not. Set 'includeNBY' to False to leave out notes that are Not Bought Yet (NBY)

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
							newDatapoint['noteStatus'] = 'C'
						else:
							newDatapoint['noteStatus'] = 'B'
					else:
						dontAppend = not includeNBY
						newDatapoint['noteStatus'] = 'NBY'
				else:					
					newDatapoint['noteStatus'] = 'NB'
					
				if not dontAppend:
					convertedData.append(newDatapoint)

		return convertedData

	def convertDataFromFile(self, fileToConvert, includeNBY):
		""" Load file and converter Downloader data """
		dataToConvert = self.loadDataFromFile(fileToConvert)
		return self.convertData(dataToConvert, includeNBY)

	def dumpData(self, data, filePath):
		""" Dumps data to file """

		file = open (filePath, 'w')
		file.write(json.dumps(data))
		file.close()







