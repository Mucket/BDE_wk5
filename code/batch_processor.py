from pyspark.sql import SparkSession, functions
from data_schema import valid_data_schema, session_schema

def extract_columns_for_session_creation(user_row):
    return (user_row.visit_id, {
        'user_id': user_row.user_id,
        'event_time': user_row.event_time,
        'site': user_row.source.site,
        'api_version': user_row.source.api_version,
        'current': user_row.page.current})

def trial_function(list_of_dicts):
    return {'start_time': min(item['event_time'] for item in list_of_dicts),
            'session_duration': max(item['event_time'] for item in list_of_dicts)-min(item['event_time'] for item in list_of_dicts)}




# Initialize spark session
spark = SparkSession.builder\
    .master(master='local[*]')\
    .appName(name='batch_processor')\
    .getOrCreate()

# Path where all batch files are located (in this example only one with 5 rows)
data_path = '/home/cmc/Documents/BecomeDataEngineer/BDE_wk5/data/'

# Read valid_data from file and transform events into sessions
valid_data_input = spark.read\
    .json(path=data_path, schema=valid_data_schema)\
    .rdd.map(f=lambda x: extract_columns_for_session_creation(x))\
    .groupByKey().mapValues(f=lambda x:trial_function(x)).values()



# Check and see what the dataframe looks like
"""valid_data_input.printSchema()
valid_data_input.show()"""

# Check and see what the rdd looks like
print(valid_data_input.collect())