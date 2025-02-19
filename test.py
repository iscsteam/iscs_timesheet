import os 
import pytz
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
import psycopg2
from dotenv import load_dotenv
import uuid
from fastapi import FastAPI, Security, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery, APIKeyCookie
from azure.storage.blob import BlobServiceClient
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

load_dotenv()  
tenant_id=os.getenv('tenant_id_env')
client_id=os.getenv('client_id_env')
client_secret=os.getenv('client_secret_env')
credential = ClientSecretCredential(tenant_id,client_id,client_secret)
key_vault_url = "https://retinopathykeyvault.vault.azure.net/"
storage_account_name="gnayana"
key_vault_client = SecretClient(vault_url=key_vault_url,credential=credential)

def storage_key_vault():
    # Replace this with your secret's name i`n Key Vault
    secret_name = "keydrinf" #
    # Retrieve the secret from Key Vault
    retrieved_secret = key_vault_client.get_secret(secret_name)
    storage_access_key = retrieved_secret.value
    return storage_access_key
storage_access_key=storage_key_vault()
# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={storage_access_key};EndpointSuffix=core.windows.net"
CONTAINER_NAME = "timesheetscontainer"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)
#blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

app = FastAPI()

API_KEY_NAME=os.getenv("API_KEY_NAME")
API_KEY=os.getenv("API_KEY")
# Define API key security dependencies
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Function to verify API key
def get_api_key(
    api_key_header: str = Security(api_key_header),

):
    if api_key_header == API_KEY : 
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )
@app.post("/upload_the_timesheet",dependencies=[Depends(get_api_key)])
async def upload_timesheet(
    file: UploadFile = File(...), 
    month: str = Form(...), 
    year: str = Form(...),
    name:str = Form(...)
):
    """
    Endpoint to upload a timesheet Excel file with month and year metadata.
    Files with the same year and month are stored in the same virtual folder.
    """
    try:
        # Read file content
        content = await file.read()
        sanitized_name = name.replace(" ", "_")
        # Generate filename format: "year_month_name_originalfilename.xlsx"
        filename = f"{year}_{month}_{sanitized_name}_{file.filename}"
        blob_path = f"{year}/{month}/{name}/{filename}"
        blob_client = container_client.get_blob_client(blob_path)
        # Upload the file to blob storage
        blob_client.upload_blob(content)
        return {"message":f"Hey {name} you have successful uploaded  for the month of {month}","path": blob_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files")
async def list_timesheets(month: str, year: str):
    try:
        # Create a prefix to filter blobs (e.g., "2025/January/")
        prefix = f"{year}/{month}/"
        blobs = container_client.list_blobs(name_starts_with=prefix)
        
        # Generate SAS URL for each blob
        file_list = []
        sas_token = os.getenv('sas_token')  # Retrieve SAS token from environment variable
        
        for blob in blobs:
            blob_url_with_sas = f"https://{storage_account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob.name}?{sas_token}"
            file_list.append(blob_url_with_sas)
    
        return {"files": file_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


