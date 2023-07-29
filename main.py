# dynamic.py
from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from pydantic import BaseModel
from datetime import date, datetime

import base64
import tensorflow
from tensorflow import keras
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import time

import os
from google.cloud import bigquery, storage
from google.oauth2 import service_account

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

#model = keras.models.load_model("sequential.h5")

# class details(BaseModel):
#     patient_Id : str   
#     patient_Name : str
#     patient_Email : str
#     patient_Dob : str
#     patient_Gender : str
#     dr_Probability : float | None = None
#     image_Path : str | None = None

key_Path = "key.json"
project_id = "cloudkarya-internship"
bigquery_Client = bigquery.Client.from_service_account_json(key_Path)
storage_Client = storage.Client.from_service_account_json(key_Path)
private_Bucket = "dr-raw"
public_Bucket = "dr-processed"

def upload_Data(image : UploadFile, data_Entry : dict):
    folder_Name = "images"
    bucket = storage_Client.get_bucket(private_Bucket)

    # Upload the image into the Cloud Storage
    blob = bucket.blob(f'{image.filename}')
    image.file.seek(0)
    blob.upload_from_file(image.file, content_type = image.content_type)

    # Get the image path from Cloud Storage
    # data_Entry["image_Path"] = f"https://storage.googleapis.com/{bucket_Name}/{blob.name}"
    # data_Entry["dr_Probability"] = str(prediction)

    # Upload the data along with image path into Big Query
    table = 'cloudkarya-internship.patient_data.personal_Data'
    errors = bigquery_Client.insert_rows_json(table, [data_Entry])

    if errors :
        raise Exception(f'Error inserting rows into BigQuery : {errors}')
    return f"https://storage.googleapis.com/{public_Bucket}/images/{blob.name}"


@app.get("/")
async def dynamic_file(request : Request):
    return templates.TemplateResponse("home.html", {"request" : request})

@app.get("/newPatient")
async def dynamic_file(request : Request):
    return templates.TemplateResponse("patientForm.html", {"request" : request})

@app.get("/report")
async def report_fun(request: Request):
    return templates.TemplateResponse("results.html", {"request": request})

@app.post("/dynamic")
async def dynamic(request : Request, image : Annotated[UploadFile, File(...)],
                                    patient_Id : Annotated[str, Form(...)],
                                    patient_fName : Annotated[str, Form(...)],
                                    patient_lName : Annotated[str, Form(...)],
                                    # patient_Aadhar : Annotated[str, Form(...)],
                                    patient_Dob : Annotated[str, Form(...)],
                                    patient_Email : Annotated[str, Form(...)],
                                    patient_Gender : Annotated[str, Form(...)],
                                    patient_Mobile : Annotated[str, Form(...)]):

    test_Date = str(datetime.now().date())
    date_object = datetime.strptime(str(test_Date), "%Y-%m-%d")
    test_Date_Display = date_object.strftime("%B %d, %Y")

    patient_Name = patient_fName + " " + patient_lName

    data_Entry = {"patient_Id": patient_Id, "patient_Name": patient_Name, "patient_Dob": patient_Dob, "patient_Mobile": patient_Mobile, "patient_Email": patient_Email, "patient_Gender": patient_Gender, "test_Date": test_Date}

    image_Path = upload_Data(image, data_Entry)

    time.sleep(13)
    query = f"""
         SELECT dr_Probability, image_Path FROM {project_id}.patient_data.test_Data
         WHERE patient_Id = '{patient_Id}' AND test_Date = '{test_Date}';
    """

    df = bigquery_Client.query(query).to_dataframe()

    return templates.TemplateResponse("results.html", {"request" : request, "probability": round(float(df.iloc[0]['dr_Probability']), 2), "img": image_Path , "patient_Id": patient_Id, "patient_Name": patient_Name,"patient_Dob": patient_Dob,"patient_Email": patient_Email,"patient_Gender": patient_Gender, "test_Date": test_Date_Display})

    
@app.post("/getdata")
async def get_data(request: Request,patient_Id:Annotated[str,Form(...)]):

   query = f"""
         SELECT  * FROM {project_id}.patient_data.personal_Data
         WHERE patient_Id = '{patient_Id}';
   """
   df = bigquery_Client.query(query).to_dataframe()
   print(df.head())
   patient_Id = df.iloc[0]['patient_Id']
   patient_Name = df.iloc[0]['patient_Name']
   patient_Email = df.iloc[0]['patient_Email']
   patient_Dob = df.iloc[0]['patient_Dob']
   patient_Gender = df.iloc[0]['patient_Gender']

   test_Query = f"""
         SELECT * FROM {project_id}.patient_data.test_Data
         WHERE patient_Id = '{patient_Id}';
   """
   test_df = bigquery_Client.query(test_Query).to_dataframe() 
   image_Path = test_df.iloc[0]["image_Path"] 
   prediction = round(float(test_df.iloc[0]['dr_Probability']), 2) 
   test_Date = test_df.iloc[0]['test_Date']
   date_object = datetime.strptime(str(test_Date), "%Y-%m-%d")
   test_Date = date_object.strftime("%B %d, %Y")

   return templates.TemplateResponse("results.html", {"request": request, "probability": prediction, "img": image_Path , "patient_Id": patient_Id, "patient_Name": patient_Name,"patient_Dob": patient_Dob,"patient_Email": patient_Email,"patient_Gender": patient_Gender, "test_Date": test_Date})
   

# # if __name__ == '__dynamic__':
# #    uvicorn.run(app, host='0.0.0.0', port=8000)
