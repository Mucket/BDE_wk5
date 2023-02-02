from pyspark.sql.types import StringType,  StructType, StructField, \
    TimestampType, LongType, BooleanType, DoubleType, IntegerType, ArrayType

# Schema of the input gathered from the 'valid' topic
valid_data_schema = StructType(fields=[
    StructField(name='visit_id', dataType=StringType(), nullable=True),
    StructField(name='event_time', dataType=TimestampType(), nullable=False),
    StructField(name='user_id', dataType=LongType(), nullable=False),
    StructField(name='keep_private', dataType=BooleanType(), nullable=True),
    StructField(name='page', dataType=StructType([
        StructField(name='current', dataType=StringType(), nullable=False),
        StructField(name='previous', dataType=StringType(), nullable=True)
    ]), nullable=False),
    StructField(name='source', dataType=StructType([
        StructField(name='site', dataType=StringType(), nullable=False),
        StructField(name='api_version', dataType=StringType(), nullable=False)
    ]), nullable=True),
    StructField(name='user', dataType=StructType([
        StructField(name='ip', dataType=StringType(), nullable=False),
        StructField(name='latitude', dataType=DoubleType(), nullable=False),
        StructField(name='longitude', dataType=DoubleType(), nullable=False)
    ]), nullable=False),
    StructField(name='technical', dataType=StructType([
        StructField(name='browser', dataType=StringType(), nullable=True),
        StructField(name='os', dataType=StringType(), nullable=False),
        StructField(name='lang', dataType=StringType(), nullable=True),
        StructField(name='device', dataType=StructType([
            StructField(name='type', dataType=StringType(), nullable=False),
            StructField(name='version', dataType=StringType(), nullable=False)
        ]), nullable=True),
        StructField(name='network', dataType=StringType(), nullable=True)
    ]), nullable=False)
])

# Schema of the session after combining events to a session
session_schema = StructType(fields=[
    StructField(name='session_id',dataType=StringType(), nullable=False),
    StructField(name='start_time', dataType=TimestampType(), nullable=False),
    StructField(name='duration_seconds', dataType=IntegerType(), nullable=True),
    StructField(name='user_id', dataType=LongType(), nullable=False),
    StructField(name='pages', dataType=ArrayType(
        StructType([
            StructField(name='page', dataType=StructType([
                StructField(name='name', dataType=StringType(), nullable=False),
                StructField(name='event_time', dataType=TimestampType(), nullable=False)
        ]), nullable=True)
    ])), nullable=True),
    StructField(name='source', dataType=StructType([
        StructField(name='site', dataType=StringType(), nullable=False),
        StructField(name='api_version', dataType=StringType(), nullable=False)
    ]), nullable=False)
])