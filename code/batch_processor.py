from pyspark.sql import SparkSession
from data_schema import valid_data_schema, session_schema
from datetime import datetime
from os import path, makedirs

def extract_columns_for_session_creation(row):
    """
    Extract all the values necessary for creating the session and return a flat structure
    :param row: one row of the rdd data structure
    :return: a nested structure of a dictionary (containing all necessary values for creating a session) enveloped by a
    tuple. The first tuple element holds the value that will be grouped by, while the second one holds the dictionary.
    """
    return (row.visit_id, {
        'visit_id': row.visit_id,
        'user_id': row.user_id,
        'event_time': row.event_time,
        'site': row.source.site,
        'api_version': row.source.api_version,
        'current': row.page.current})

def session_creation(list_of_dicts):
    """
    :param list_of_dicts: the list of dictionaries belonging to the same session
    :return: returns a new dictionary holding all the information of the session. It is structured as:
    {
    'session_id': visit_id,
    'start_time': first event_time,
    'duration_seconds': timedelta min and max event_time,
    'user_id': user_id,
    'pages': [{
        'page': {
            'name': current website,
            'event_time': event_time}}]
    'source': {
        'site': site
        'ape_version': api_version}}
    """
    # Sort all dictionaries belonging to the same session according to its event_time in ascending order
    sorted_list_of_dicts = sorted(list_of_dicts, key=lambda d:d['event_time'])
    # Create a list of dictionaries showing the order and time of visited pages
    pages = [{'page':{'name': item['current'], 'event_time': item['event_time']}} for item in sorted_list_of_dicts]
    # extract the first and final timestamp
    final_time = datetime.timestamp(sorted_list_of_dicts[-1]['event_time'])
    initial_time = datetime.timestamp(sorted_list_of_dicts[0]['event_time'])
    return {'session_id': sorted_list_of_dicts[0]['visit_id'],
            'start_time': sorted_list_of_dicts[0]['event_time'],
            'duration_seconds': int(final_time-initial_time),
            'user_id': sorted_list_of_dicts[0]['user_id'],
            'pages': pages,
            'source': {'site': sorted_list_of_dicts[0]['site'],
                       'api_version': sorted_list_of_dicts[0]['api_version']}}

# Setup environment
# 1: Evaluate the path to the project
common_path = path.dirname(path.split(path.abspath(__file__))[0])
# 2: Create input and output directories
input_data_path = common_path + '/input'
output_data_path = common_path + '/output'
makedirs(name=input_data_path, exist_ok=True)
makedirs(name=output_data_path, exist_ok=True)

# Initialize spark session
spark = SparkSession.builder\
    .master(master='local[*]')\
    .appName(name='batch_processor')\
    .getOrCreate()

""" 
Process the input data:
   - read valid_data from file
   - apply the input schema
   - transform the dataframe to a rdd and map the relevant columns
   - yield a 2-dim tuple whereas the first element holds the grouping key and the second element all the data
   - group by the grouping key
   - map all values of the second tuple element to a new dictionary structure by looping through them per key
   - extract the values of the rdd and transform it back to a dataframe using the output-schema
   - write the dataframe as a json to the file sink
"""
query = spark\
    .read\
    .json(path=input_data_path, schema=valid_data_schema)\
    .rdd\
    .map(f=lambda x: extract_columns_for_session_creation(x))\
    .groupByKey()\
    .mapValues(f=lambda x:session_creation(x))\
    .values()\
    .toDF(schema=session_schema)\
    .write\
    .json(path=output_data_path, mode='append')
