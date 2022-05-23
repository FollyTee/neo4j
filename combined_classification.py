# -*- coding: utf-8 -*-
"""Combined classification.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1yoHmhrgKl4dpVoi_TuHbcPKk5mTFelUY
"""

!apt-get install openjdk-8-jdk-headless

!wget https://archive.apache.org/dist/spark/spark-3.2.1/spark-3.2.1-bin-hadoop2.7.tgz

!tar xf /content/spark-3.2.1-bin-hadoop2.7.tgz

!pip install -q findspark

import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"
os.environ["SPARK_HOME"] = "/content/spark-3.2.1-bin-hadoop2.7"

import findspark
findspark.init()
findspark.find()

import pyspark
import numpy as np
import pandas as pd

from pyspark.sql import SparkSession

spark = SparkSession.builder.master('local[*]').appName('Buyers').getOrCreate()

# Read data from CSV file
#you can download it from here: https://raw.githubusercontent.com/besherh/BigDataManagement/main/SparkCSV/flights-larger.csv
customer_df = spark.read.csv('combined-data.csv', sep=',', header=True, inferSchema=True, nullValue='NULL')
#df = pd.read_csv("combined-data.csv")

#View table structure
customer_df.printSchema()

#Total number of records
customer_df.count()

customer_df.show(5)

# Find Count of Null, None, NaN of All DataFrame Columns
from pyspark.sql.functions import col,isnan, when, count

#Check for missing values
#
customer_df.na.drop().count()

customer_df.na.drop(how="any", thresh=2).show()

from pyspark.ml.feature import Imputer

imputer = Imputer(
    inputCols=['count_buyId', 'avg_price'], 
    outputCols=["{}_imputed".format(c) for c in ['count_buyId', 'avg_price']]
    ).setStrategy("mean")

###Add imputation cols to df
customer_df2 = imputer.fit(customer_df).transform(customer_df)

customer_df2.show()

customer_df2.printSchema()

#Create label whether user is a big player or small 

customer_df_players = customer_df2.withColumn('label', (customer_df2.count_gameclicks >=143).cast('integer'))

customer_df_players.show(5)

customer_df_players=customer_df_players.select("userId","userSessionId","teamLevel","platformType","count_hits","count_buyId","avg_price","count_buyId_imputed","avg_price_imputed","label")

customer_df_players.show(5)

#Categorical transformation of PlatformType column to indexed numerical value

from pyspark.ml.feature import StringIndexer

# Create an indexer
indexer = StringIndexer(inputCol='platformType', outputCol='platformType_idx')

# Indexer identifies categories in the data
indexer_model = indexer.fit(customer_df_players)

# Indexer creates a new column with numeric index values
platformType_idx = indexer_model.transform(customer_df_players)

# Repeat the process for the other categorical feature
#platformType_idx = StringIndexer(inputCol='platformType', outputCol='platformType_idx').fit(df_players).transform(df_players)

#Categorical transformation of  teamlevel column to indexed numerical value

from pyspark.ml.feature import StringIndexer

# Create an indexer
indexer = StringIndexer(inputCol='teamLevel', outputCol='teamLevel_idx')

# Indexer identifies categories in the data
indexer_model = indexer.fit(customer_df_players)

teamLevel_idx = indexer_model.transform(customer_df_players)

#Categorical transformation of  teamlevel column to indexed numerical value

from pyspark.ml.feature import StringIndexer

# Create an indexer
indexer = StringIndexer(inputCol='userId', outputCol='userId_idx')

# Indexer identifies categories in the data
indexer_model = indexer.fit(customer_df_players)
userId_idx = indexer_model.transform(customer_df_players)

#Categorical transformation of  teamlevel column to indexed numerical value

from pyspark.ml.feature import StringIndexer

# Create an indexer
indexer = StringIndexer(inputCol='userSessionId', outputCol='userSessionId_idx')

# Indexer identifies categories in the data
indexer_model = indexer.fit(customer_df_players)
userSessionId_idx = indexer_model.transform(customer_df_players)

#Categorical transformation of  teamlevel column to indexed numerical value

from pyspark.ml.feature import StringIndexer

# Create an indexer
indexer = StringIndexer(inputCol='count_buyId_imputed', outputCol='count_buyId_imputed_idx')

# Indexer identifies categories in the data
indexer_model = indexer.fit(customer_df_players)
count_buyId_imputed_idx = indexer_model.transform(customer_df_players)

customer_df_players.columns

#Assembling columns

from pyspark.ml.feature import VectorAssembler

# Create an assembler object
assembler = VectorAssembler(inputCols=[
    'teamLevel', 'count_hits',
    'count_buyId_imputed', 
    'avg_price_imputed'
    
], outputCol='features')

# Consolidate predictor columns
customer_assembled = assembler.transform(customer_df_players)

# Check the resulting column
customer_assembled.select('features', 'label').show(5, truncate=False)

"""'''Decision Tree
Train/test split To objectively assess a Machine Learning model you need to be able to test it on an independent set of data. You can't use the same data that you used to train the model: of course the model will perform (relatively) well on those data!

You will split the data into two components:

training data (used to train the model) and testing data (used to test the model).**bold text**

'''
"""

# Split into training and test sets in a 70:30 ratio
customers_train, customers_test = customer_assembled.randomSplit([0.7, 0.3], seed=17)

# Check that training set has around 70% of records
training_ratio = customers_train.count() / customer_assembled.count()
print(training_ratio)

customers_test.show(2)

"""'''Build a Decision Tree
Now that you've split the flights data into training and testing sets, you can use the training set to fit a Decision Tree model.
'''

"""

from pyspark.ml.classification import DecisionTreeClassifier

# Create a classifier object and fit to the training data
tree = DecisionTreeClassifier()
tree_model = tree.fit(customers_train)

tree_model

# Create predictions for the testing data and take a look at the predictions
prediction = tree_model.transform(customers_test)
prediction.select('label', 'prediction', 'probability').show(5, False)

"""'''Evaluate the Decision Tree
You can assess the quality of your model by evaluating how well it performs on the testing data. Because the model was not trained on these data, this represents an objective assessment of the model.

A confusion matrix gives a useful breakdown of predictions versus known values. It has four cells which represent the counts of:

True Negatives (TN) — model predicts negative outcome & known outcome is negative True Positives (TP) — model predicts positive outcome & known outcome is positive False Negatives (FN) — model predicts negative outcome but known outcome is positive False Positives (FP) — model predicts positive outcome but known outcome is negative.
'''

"""

# Create a confusion matrix
a=prediction.groupBy('label', 'prediction').count().show()



# Calculate the elements of the confusion matrix
TN = prediction.filter('prediction = 0 AND label = prediction').count()
TP = prediction.filter('prediction = 1 AND label = prediction').count()
FN = prediction.filter('prediction = 0 AND label = 1').count()
FP = prediction.filter('prediction = 1 AND label = 0').count()

# Accuracy measures the proportion of correct predictions
accuracy = (TN + TP) / (TN + TP + FN + FP)
print(accuracy)

tree_model.featureImportances