DB_URL = "postgresql://neondb_owner:npg_2AdVgPsO5IUf@ep-sweet-truth-ad559bv7-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

table_name = "variables_del_clima_para_zonas_climaticas_maule"

dir_path = "historical_data_maule/"


"""
schema

id
SERIAL
PRIMARY KEY
date
TIMESTAMP
NOT NULL
lat
DOUBLE PRECISION
NOT NULL
lon
DOUBLE PRECISION
NOT NULL
z
DOUBLE PRECISION
NOT NULL
source
VARCHAR(50)
NOT NULL
granularity
VARCHAR(20)
NOT NULL
tmax
DOUBLE PRECISION
tmin
DOUBLE PRECISION
tdwp
DOUBLE PRECISION
rhmean
DOUBLE PRECISION
rs
DOUBLE PRECISION
wspeed2m
DOUBLE PRECISION
precip_mm
DOUBLE PRECISION
rso
DOUBLE PRECISION
eto
DOUBLE PRECISION
"""

#upload to tablename in db from csv files in dir_path
import os
import pandas as pd
from sqlalchemy import create_engine
import json
from sqlalchemy.exc import SQLAlchemyError
def upload_csv_to_neon(db_url, table_name, dir_path):
    # Create a database engine
    engine = create_engine(db_url)

    # Iterate over CSV files in the directory
    for filename in os.listdir(dir_path):
        if filename.endswith(".csv"):
            file_path = os.path.join(dir_path, filename)
            try:
                # Read the CSV file into a DataFrame
                df = pd.read_csv(file_path)
                
                # Convert column names to lowercase to match PostgreSQL schema
                df.columns = [col.lower() for col in df.columns]

                # Upload the DataFrame to the database
                df.to_sql(table_name, engine, if_exists='append', index=False)
                print(f"Successfully uploaded {filename} to {table_name}.")
            except SQLAlchemyError as e:
                print(f"Error uploading {filename} to {table_name}: {e}")
# Call the function to upload CSV files to Neon database
upload_csv_to_neon(DB_URL, table_name, dir_path)