lc
==

LC project

= Info =
* 'results' folder contains weka dataset and some stats on full data & sampled data
* 'code/resources' contains the Json dump of the Downloader.

= Run =

* Run 'stats.py' to get simple stats on downloader data. 
* Run 'weka_converter.py' to generate weka ARFF file from API downloader data.

= Prerequisites =

Install modules :
* numpy
* scipy
* mdp
* liac-arff
* prettytable

Setup conf file 'lc_conf'

= Configuration = 

The configuration file 'lc_conf' contains the parameters used by 
the modules 'stats.py' and 'weka_converter.py' :

== WEKA-specific parameters ==

Attributes are the are the columns in the dataset to analyze.
You can have NOMINAL or NUMERIC attributes in Weka.

* NOMINAL_ATTRIBUTES_NAMES are the attributes with discreet values. You must list the nominals values. The nominal values can't be modified. See CLASS_NOMINAL_VALUES and LOAN_GRADE_NOMINAL_VALUES below :

** CLASS_NOMINAL_VALUES cannot be changed. This parameter must be set to ['B', 'NB', 'NBY', 'C']. Those are the class labels used in the Weka dataset. Class Labels Description :
*** B = Note Bought
*** NB = Note Not Bought
*** C = Note Cancelled
*** NBY = Note Not Bought Yet

** LOAN_GRADE_NOMINAL_VALUES cannot be changed. This parameter must be set to ['A', 'B', 'C', 'D', 'E', 'F', 'G']

* NUMERIC_ATTRIBUTES_NAMES are the metrics on which you can do continous maths operations like mean, max, min, etc. /!\ make sure that the names correspond to a key in the raw downloader JSON.

* NUMERIC_ATTRIBUTES_METRICS is used to set the unit of each metric of NUMERIC_ATTRIBUTES_NAMES. /!\ list should match with METRICS order.


== Other parameters ==

* INCLUDE_NBY is used to include or not the NBY class in the dataset to analyze.
* MAX_NB_BUCKETS to modify the max nb of buckets that will be generated for each continuous metric of the dataset (the goal being to discretize them).
* WEKA_FILE is the path to file where Weka will save converted downloader data.
* DATA_TO_CONVERT  is used to change path of API downloader data file to analyze.

	



