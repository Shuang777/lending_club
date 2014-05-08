#!python
# -*- coding: utf-8 -*-

"""
Stats for Downloader Formatted Data
"""

__author__ = "Marion"
__email__ = "kangarup@gmail.com"
__version__ = "1.0"


import json
import scipy
from prettytable import PrettyTable
from api_converter import Converter
import numpy as np
import mdp
import time
import os

class SimpleStats(object):
	"""Statistical Tools for Downloader Data"""

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
			dataFileToConvert = globals()["DATA_TO_CONVERT"]
		 	classes = globals()["CLASS_NOMINAL_VALUES"]
		 	metrics = globals()["NUMERIC_ATTRIBUTES_NAMES"]
		 	units = globals()["NUMERIC_ATTRIBUTES_METRICS"]
		 	maxNbBuckets = globals()["MAX_NB_BUCKETS"]
			return 	(dataFileToConvert, classes, metrics, units,  int(maxNbBuckets))
		except KeyError, error:
			print "Missing key %s in the configufation file"

	def prepareTimeseries(self, dataset,  classes, metrics):
		"""Prepare timeserie for each metric per class"""

		timeseries = {}
		for status in classes: # each class has a status => N, NB, C, E
			timeseries[status] = {} 

		for status in timeseries:
			for metricName in metrics:
				timeseries[status][metricName] = []

		for datapoint in dataset:
			for status in timeseries:
				if datapoint['noteStatus'] == status:
					for metricName in metrics:
						if str(datapoint[metricName]) != 'null':
							value = float(str(datapoint[metricName]))
							timeseries[status][metricName].append(value)

		return timeseries


	def outputDatasetClassDescription(self, classes):
		"""
		Output class label description for the final dataset
		@param classes The class labels of the dataset
		"""

		print 
		print "==> Class Labels Description (%d classes) :"% len(classes)
		for classLabel in classes:
			if classLabel == 'B':
				print "--> B = Note Bought"
			elif classLabel == 'NB':
				print "--> NB = Note Not Bought"
			elif classLabel == 'NBY':
				print "--> NBY = Note Not Bought Yet"
			elif classLabel == 'C':
				print "--> C = Note Cancelled"




	def outputMainMetricsBuckets(self, dataset,  classes, metrics, maxNbBuckets):
		""" 
		Ouput main metric buckets for each class in the dataset.
		This is a dimensionality reduction step :
		- Main metric buckets are found by runnign 
		  a clustering algorithm on the metric time serie.
		- The cluster centroid is the bucket.
		- The dataset can be discretized by assigning the closest metric 
		  centroid to each metric value.

		@param dataset The dataset to analyze
		@param classes The class labels of the dataset
		@param metrics The metrics names (or attributes, or columns) of the dataset
		@param mainMetricBuckets The max nb of buckets that will be generated for each continuous metric of the dataset (the goal being to discretize them)

		"""

		print 
		print "==> Main metric buckets for each class of the dataset :"

		timeseries = self.prepareTimeseries(dataset, classes, metrics)

		for status in timeseries:
			for metricName in timeseries[status]:
				timeserie = timeseries[status][metricName]
				mainMetricBuckets = self.findMainMetricBuckets(timeserie, maxNbBuckets)
				if len(mainMetricBuckets) > 0:
					print "---> Main '%s' buckets for notes with status %s. Total Population %s" % (metricName, status, len(timeserie))
					for k in mainMetricBuckets:
						bucketPopulation = len(mainMetricBuckets[k])
						if bucketPopulation > 0:
							bucketMean = scipy.mean(mainMetricBuckets[k])
							print " * Bucket ID : %s. Bucket Population : %s. Bucket mean : %s" % (str(k), str(bucketPopulation), str(bucketMean))



	def findMainMetricBuckets(self, timeserie, maxNbBuckets):
		"""
		Find the main metric buckets of a timeserie.
		This is helpful to reduce the dimensionality
		of a dataset and descretize continuous values.
		"""

		
		population = len(timeserie)
		buckets = {}
		if population > maxNbBuckets:
			dim1_matrix = []
			for value in timeserie:
				dim1_matrix.append([value])

			data = np.array(dim1_matrix)
			#import ipdb; ipdb.set_trace();
			
			kmeansNode = mdp.nodes.KMeansClassifier(maxNbBuckets)
			kmeansNode.train(data)
			kmeansNode.stop_training()
			clusters = kmeansNode.label(data)
			nbClusters = len(set(clusters))
			
			for k in xrange(nbClusters):
				buckets[k] = []
				for i in xrange(len(data)):
					if clusters[i] == k:				
						buckets[k].append(data[i][0])		



		return buckets



	def outputStats(self, dataset, classes, metrics, units):
		"""Output mean of each metric per class and some other basic stats"""

		timeseries = self.prepareTimeseries(dataset, classes, metrics)

		print 
		print "==> Simple stats :" 
		print "---> Number of entries in converted dataset : %d" % len(dataset)
		
		for status in timeseries:
			print "---> Note Status : %s " % status
			population = len(timeseries[status][metrics[0]])
			print " * Population : %s" % str(population)
			for metricName in metrics:
				metricMean = scipy.mean(timeseries[status][metricName])
				metricUnit = units[metrics.index(metricName)]
				if metricUnit == 'seconds':
					print " * Average %s : %s hours" % (metricName, str(metricMean / 3600))
				else:
					print " * Average %s : %s %s" % (metricName, str(metricMean), metricUnit)


	def outputSamples(self, dataset):
		""" Print out a nicely formatted table of 50 samples of the datasets. """

		pt = PrettyTable()
		fields = ['id', 'Timestamp', 'Note Price', 'Time On Market (hours)', 'Note Status']
		pt.field_names = (fields)


		sampling_rate = 10
		for i in xrange( int(len(dataset) / sampling_rate)):
			datapoint = dataset[i * sampling_rate]
			pt.add_row([datapoint['id'], datapoint['timestamp'], datapoint['notePrice'], datapoint['timeOnMarket'], datapoint['noteStatus']])

		print 
		print "==> Data Samples :"
		print pt


	def main(self):
		"""Output serie of stats"""

		# read conf file
		(dataFileToConvert,
		 classes,
		 metrics,
		 units,
		 maxNbBuckets) = self.read_conf(self.conf_file_name)

		# convert raw API data file
		converter = Converter()
		rawData = converter.loadDataFromFile(dataFileToConvert)
		convertedData = converter.convertData(rawData)

		# output various stats
		self.outputDatasetClassDescription(classes)
		self.outputStats(convertedData, classes, metrics, units )
		self.outputMainMetricsBuckets(convertedData, classes, metrics, maxNbBuckets)
		self.outputSamples(convertedData)

		
			
if __name__ == '__main__':

	conf_file_name = 'lc_conf'

	start = time.time()	
	stats = SimpleStats(conf_file_name)
	stats.main()
	end = time.time()

	print "==> Run time : %d s" %(end - start)