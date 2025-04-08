import gspread
from google.oauth2 import service_account
import streamlit as st
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Load secrets
google_cloud_secrets = st.secrets["google_cloud"]

# Create credentials
creds = service_account.Credentials.from_service_account_info(
    {
        "type": google_cloud_secrets["type"],
        "project_id": google_cloud_secrets["project_id"],
        "private_key_id": google_cloud_secrets["private_key_id"],
        "private_key": google_cloud_secrets["private_key"].replace("\\n", "\n"),
        "client_email": google_cloud_secrets["client_email"],
        "client_id": google_cloud_secrets["client_id"],
        "auth_uri": google_cloud_secrets["auth_uri"],
        "token_uri": google_cloud_secrets["token_uri"],
        "auth_provider_x509_cert_url": google_cloud_secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": google_cloud_secrets["client_x509_cert_url"],
        "universe_domain": google_cloud_secrets["universe_domain"],
    },
    scopes=["https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"],
)

# Constants
SHEET_ID = "10sXzBbFk-WBSpsdtsw42BpTwDp5Xpe8TWxL6SL_xhiY"
DRIVE_FOLDER_ID = '1-RJY0lWMM5SyenDCyEZs1gv_W8N3Un4k'
DRIVERS = [
    "Ade", "Ahmad", "Anta", "Antoni", "Ari", "Atma", "Bari", "Cecep", 
    "Dapit", "Dirman", "Feri", "Friyan", "Gamba", "Glora", "GomGom", 
    "Happy", "Hendi", "Hendra", "Herman", "Marlep", "Nanang K", "Nasrul", 
    "Pendi", "Riyan", "Rudi", "Sitorus", "Solihin", "Sueb", "Sukandar", 
    "Sunggu", "Syamsul", "Yani M", "Yani S", "Yayan"
]

# Initialize services
@st.cache_resource
def get_drive_service():
    return build('drive', 'v3', credentials=creds)

@st.cache_resource
def get_sheets_client():
    return gspread.authorize(creds)

def upload_image_to_drive(image_bytes, image_name):
    """Upload image to Google Drive and return public URL"""
    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype='image/jpeg')
    file_metadata = {
        'name': image_name,
        'parents': [DRIVE_FOLDER_ID]
    }
    
    drive_service = get_drive_service()
    file = drive_service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id'
    ).execute()
    
    # Set public permissions
    drive_service.permissions().create(
        fileId=file['id'],
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()
    
    return f"https://drive.google.com/uc?id={file['id']}"

def input_data(tanggal, supir, surat_jalan_url, foto_segel_url, foto_muat_url):
    """Append data to Google Sheet"""
    client = get_sheets_client()
    sheet = client.open_by_key(SHEET_ID).worksheet("Data")
    data = [tanggal, supir, surat_jalan_url, foto_segel_url, foto_muat_url]
    sheet.append_row(data, value_input_option="USER_ENTERED")

# Streamlit UI
st.title("Testing Upload Surat Jalan")

with st.form("upload_form"):
    supir = st.selectbox(
        "Supir", 
        options=DRIVERS, 
        placeholder="Masukkan Nama Supir", 
        index=None
    )
    
    surat_jalan = st.file_uploader(
        "Upload Surat Jalan", 
        type=["png", "jpg", "jpeg"], 
        key='sj'
    )
    foto_segel = st.file_uploader(
        "Upload Foto Segel", 
        type=["png", "jpg", "jpeg"], 
        key='sg'
    )
    foto_muat = st.file_uploader(
        "Upload Foto Muat", 
        type=["png", "jpg", "jpeg"], 
        key='muat'
    )
    
    submitted = st.form_submit_button("Submit")

if submitted:
    if not supir:
        st.warning("Masukkan Nama Supir!!!")
    elif not all([surat_jalan, foto_segel, foto_muat]):
        st.warning("Harus Upload semua!")
    else:
        with st.spinner("Sedang memproses..."):
            try:
                # Get current date
                tanggal = datetime.now().strftime("%m/%d/%Y")
                
                # Upload files in parallel (conceptually)
                surat_jalan_url = upload_image_to_drive(
                    surat_jalan.getvalue(), 
                    surat_jalan.name
                )
                foto_segel_url = upload_image_to_drive(
                    foto_segel.getvalue(), 
                    foto_segel.name
                )
                foto_muat_url = upload_image_to_drive(
                    foto_muat.getvalue(), 
                    foto_muat.name
                )
                
                # Input data to sheet
                input_data(
                    tanggal, supir, 
                    surat_jalan_url, 
                    foto_segel_url, 
                    foto_muat_url
                )
                
                st.success("Data berhasil diinput!")
            except Exception as e:
                st.error(f"Terjadi kesalahan: {str(e)}")