#!python
# -*- coding: utf-8 -*-

"""
Convert formatted API data to Weka dataset
"""

__author__ = "Marion"
__email__ = "kangarup@gmail.com"
__version__ = "1.0"

import arff
from api_converter import Converter
import os

class WekaConverter(object):
	"""Dimensionnality reduction with Principal Components Analysis"""

	def __init__(self,  conf_file_name='lc_conf'):
		self.conf_file_name = conf_file_name

	def read_conf(self, conf_file_name='lc_conf'):
		""" Retreive parameters from the Stats configuration file """
		script_dir = os.path.dirname(os.path.abspath(__file__))

		try:
			execfile("%s/%s" % (script_dir, conf_file_name), globals())
		except IOError, error:
			print "Configuration file %s not found: %s " % (conf_file_name, repr(error))
			exit(1)
		try:
			fileToConvert = globals()["DATA_TO_CONVERT"]
		 	classNominalValues = globals()["CLASS_NOMINAL_VALUES"]
		 	loanGradeNominalValues = globals()["LOAN_GRADE_NOMINAL_VALUES"]
		 	numericAttributesNames = globals()["NUMERIC_ATTRIBUTES_NAMES"]
		 	nominalAttributesNames = globals()["NOMINAL_ATTRIBUTES_NAMES"]
		 	wekaFile = globals()["WEKA_FILE"]
			return 	(fileToConvert, classNominalValues, loanGradeNominalValues, numericAttributesNames, nominalAttributesNames, wekaFile)
		except KeyError, error:
			print "Missing key %s in the configufation file"


	def createSampleArff(self):
		"""Sample Weka ARFF file generation"""

		data = {
				'attributes': [
					('outlook', ['sunny', 'overcast', 'rainy']),
					('temperature', 'REAL'),
					('humidity', 'REAL'),
					('windy', ['TRUE', 'FALSE']),
					('play', ['yes', 'no'])],
				'data': [
					['sunny', 85.0, 85.0, None, 'no'],
					['sunny', 80.0, 90.0, 'TRUE', 'no'],
					['overcast', 83.0, 86.0, 'FALSE', 'yes'],
					['rainy', 70.0, 96.0, 'FALSE', 'yes'],
					['rainy', 68.0, 80.0, 'FALSE', 'yes'],
					['rainy', 65.0, 70.0, 'TRUE', 'no'],
					['overcast', 64.0, 65.0, 'TRUE', 'yes'],
					['sunny', 72.0, 95.0, 'FALSE', 'no'],
					['sunny', 69.0, 70.0, 'FALSE', 'yes'],
					['rainy', 75.0, 80.0, 'FALSE', 'yes'],
					['sunny', 75.0, 70.0, 'TRUE', 'yes'],
					['overcast', 72.0, 90.0, 'TRUE', 'yes'],
					['overcast', 81.0, 75.0, 'FALSE', 'yes'],
					['rainy', 71.0, 91.0, 'TRUE', 'no']],
				'description': u'',
				'relation': 'weather'
				}


		wekaFile = "../data/test.arff"
		arff.dump(open(wekaFile, 'w'), data)


	def prepareWekaData(self, apiDataConverted, numericAttributesNames, nominalAttributesNames ):
		"""
		Prepare timeserie for Weka ARFF file generation

		Note => Format of apiDataConverted :
			 	{'timeOnMarket': 3438.052265882492, 'timestamp': 1378792923.871444, 'notePrice': 3.04, 'id': '596513-2703872-11430858', 'noteStatus': 'B'}
		"""

		wekaData = []
		for datapoint in apiDataConverted:
			wekaDatapoint = []
			for attributesName in numericAttributesNames:
				for key in datapoint.keys():
					if key == attributesName:
						if datapoint[key] == 'null':
							wekaDatapoint.append(None)
						else:
							wekaDatapoint.append(float(datapoint[key]))
			for attributesName in nominalAttributesNames:
				for key in datapoint.keys():
					if key == attributesName:
						if datapoint[key] == 'null':
							wekaDatapoint.append(None)
						else:
							wekaDatapoint.append(str(datapoint[key]))

			wekaData.append(wekaDatapoint)

		return wekaData

	def convertToWeka(self, fileToConvert, classNominalValues, loanGradeNominalValues, numericAttributesNames, nominalAttributesNames, wekaFile):
		""" Generate Weka ARFF file from API downloader data"""

		converter = Converter()
		apiDataConverted = converter.convertDataFromFile(fileToConvert)

		data = self.prepareWekaData(apiDataConverted, numericAttributesNames, nominalAttributesNames)

		dataset = {}

		dataset['attributes'] = []
		
		for name in numericAttributesNames:
			attribute = (name, 'REAL')
			dataset['attributes'].append(attribute)


		loanGradeAttribute = ('loanGrade', loanGradeNominalValues)
		dataset['attributes'].append(loanGradeAttribute)

		classAttribute = ('noteStatus', classNominalValues)
		dataset['attributes'].append(classAttribute)
		
		
		dataset['data'] = data
		dataset['description'] =  u''
		dataset['relation'] = 'downloader data'

		arff.dump(open(wekaFile, 'w'), dataset)

	def main(self):
		"""Main method for Weka dataset generation"""

		# read conf file
		(fileToConvert,
		 classNominalValues,
		 loanGradeNominalValues, 
		 numericAttributesNames,
		 nominalAttributesNames,
		 wekaFile) = self.read_conf(self.conf_file_name)

		#wekaFile = "../data/train_data.arff"

		self.convertToWeka(fileToConvert, classNominalValues, loanGradeNominalValues, numericAttributesNames, nominalAttributesNames, wekaFile)


if __name__ == '__main__':

	conf_file_name = 'lc_conf'

	wc = WekaConverter(conf_file_name)
	#wc.createSampleArff()
	wc.main()


