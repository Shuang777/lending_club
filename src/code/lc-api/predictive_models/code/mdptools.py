#!python
# -*- coding: utf-8 -*-

"""
Dimensionnality reduction tools for Downloader Formatted Data
"""

__author__ = "Marion"
__email__ = "kangarup@gmail.com"
__version__ = "1.0"

import mdp
import numpy as np

class MDPTools(object):
	"""MDP tools for data processing"""

	def __init__(self):
		super(MDPTools, self).__init__()
		self.pcanode = None

	def prepareDataForMDP(self, convertedApiData):
		"""
		Prepare converted API data for MDP module filtering.
		The data must be formatted to a numpy.array to be used in the MDP module.

		Data Conversion Methodology :

		* 'convertedApiData' format is :
		    {'timeOnMarket': 3438.052265882492, 'timestamp': 1378792923.871444, 'notePrice': 3.04, 'id': '596513-2703872-11430858', 'noteStatus': 'B'}

		* MDP module uses numpy arrays. So 'convertedApiData' will be converted into 'mdpReadyData' which is a numpy array with this format:
		   numpy.array( [id, notePrice, timeOnMarket, noteStatus],
		   				[id, notePrice, timeOnMarket, noteStatus],
		   				  ...
		   				[id, notePrice, timeOnMarket, noteStatus]) 
		"""

		convertedDataset = []
		for datapoint in convertedApiData:
			#import ipdb; ipdb.set_trace();
			convertedDatapoint = []
			convertedDatapoint.append(datapoint['notePrice'])
			convertedDatapoint.append(datapoint['timeOnMarket'])
			convertedDataset.append(convertedDatapoint)

		
		mdpReadyData = np.array(convertedDataset)
		#mdpReadyData = np.random.random((100, 2))  # 100 observations, 2 variables

		return mdpReadyData


	def trainPCA(self, convertedApiData):
		""" 
	    Train Principal Components Analysis model.
		The base unit in the MDP module is a node. 
		See http://mdp-toolkit.sourceforge.net/tutorial/nodes.html
		"""

		numpyMatrix = self.prepareDataForMDP(convertedApiData)

		self.pcanode = mdp.nodes.PCANode(output_dim=0.8)

		self.pcanode.train(numpyMatrix)

		self.pcanode.stop_training()


	def PCAfilter(self, convertedApiData):
		""" Filter an entire dataset with the previously trained PCA filter"""
		
		numpyMatrix = self.prepareDataForMDP(convertedApiData)
	 	return self.pcanode.execute(numpyMatrix)

