import gspread
from google.oauth2 import service_account
import streamlit as st
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Constants
MAIN_DRIVE_FOLDER_ID = '1-RJY0lWMM5SyenDCyEZs1gv_W8N3Un4k'
SHEET_ID = "10sXzBbFk-WBSpsdtsw42BpTwDp5Xpe8TWxL6SL_xhiY"
DRIVERS = ["Ade", "Ahmad", "Anta", "Antoni", "Ari", "Atma", "Bari", "Cecep", 
           "Dapit", "Dirman", "Feri", "Friyan", "Gamba", "Glora", "GomGom", 
           "Happy", "Hendi", "Hendra", "Herman", "Marlep", "Nanang K", "Nasrul", 
           "Pendi", "Riyan", "Rudi", "Sitorus", "Solihin", "Sueb", "Sukandar", 
           "Sunggu", "Syamsul", "Yani M", "Yani S", "Yayan"]

# Initialize Google Services
@st.cache_resource
def get_drive_service():
    return build('drive', 'v3', credentials=creds)

@st.cache_resource
def get_sheets_client():
    return gspread.authorize(creds)

# Authentication
creds = service_account.Credentials.from_service_account_info(
    st.secrets["google_cloud"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"],
)

def create_folder(folder_name, parent_folder_id):
    """Create a new folder in Google Drive and return its ID and URL"""
    drive_service = get_drive_service()
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    
    # Make folder publicly accessible
    drive_service.permissions().create(
        fileId=folder['id'],
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()
    
    folder_url = f"https://drive.google.com/drive/folders/{folder['id']}"
    return folder['id'], folder_url

def upload_image_to_folder(image_file, folder_id):
    """Upload a single image to a folder and return its direct image URL"""
    drive_service = get_drive_service()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{image_file.name}"
    
    media = MediaIoBaseUpload(io.BytesIO(image_file.getvalue()), mimetype='image/jpeg')
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    drive_service.permissions().create(
        fileId=file['id'],
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()
    
    return f"https://drive.google.com/uc?id={file['id']}"

def upload_images_to_folder(image_files, folder_id):
    """Upload multiple images to a folder and return list of direct image URLs"""
    drive_service = get_drive_service()
    urls = []
    
    for img in image_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{img.name}"
        
        media = MediaIoBaseUpload(io.BytesIO(img.getvalue()), mimetype='image/jpeg')
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        drive_service.permissions().create(
            fileId=file['id'],
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        urls.append(f"https://drive.google.com/uc?id={file['id']}")
    
    return urls

def create_folder_structure(supir):
    """Create complete folder structure and return all important URLs"""
    # Main parent folder
    main_folder_name = f"{supir}_{datetime.now().strftime('%Y-%m-%d_%H%M')}"
    main_folder_id, main_folder_url = create_folder(main_folder_name, MAIN_DRIVE_FOLDER_ID)
    
    # Create subfolders
    surat_jalan_id, surat_jalan_url = create_folder("Surat Jalan", main_folder_id)
    
    return {
        'main_folder_url': main_folder_url,
        'main_folder_id': main_folder_id,
        'surat_jalan': {'id': surat_jalan_id, 'url': surat_jalan_url}
    }

# Streamlit UI
st.title("📦 Sistem Upload Dokumen Pengiriman")

with st.form("upload_form"):
    supir = st.selectbox("Nama Supir*", options=DRIVERS, index=None)
    
    st.subheader("Foto Segel*")
    segel_file = st.file_uploader(
        "Upload foto segel (single photo)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=False,
        key="segel"
    )

    st.subheader("Foto Muat*")
    muat_file = st.file_uploader(
        "Upload foto muat (single photo)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=False,
        key="muat"
    )
    
    st.subheader("Foto Surat Jalan*")
    surat_jalan_files = st.file_uploader(
        "Upload foto surat jalan (bisa multiple)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="sj"
    )

    submitted = st.form_submit_button("💾 Simpan Data")

if submitted:
    if not supir:
        st.warning("⚠️ Harap pilih nama supir!")
    elif not surat_jalan_files or not segel_file or not muat_file:
        st.warning("⚠️ Harap upload file untuk semua kategori!")
    else:
        with st.spinner("⏳ Membuat struktur folder dan mengupload file..."):
            try:
                # 1. Create folder structure
                folders = create_folder_structure(supir)
                
                # 2. Upload files
                # Single photos (segel and muat) go directly to main folder
                segel_url = upload_image_to_folder(segel_file, folders['main_folder_id'])
                muat_url = upload_image_to_folder(muat_file, folders['main_folder_id'])
                
                # Multiple surat jalan photos go to subfolder
                surat_jalan_urls = upload_images_to_folder(surat_jalan_files, folders['surat_jalan']['id'])
                
                # 3. Save to Google Sheets
                client = get_sheets_client()
                sheet = client.open_by_key(SHEET_ID).worksheet("Data")
                
                # Prepare the row data with surat jalan URLs in separate columns
                row_data = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    supir,
                    segel_url,
                    muat_url,
                    folders['main_folder_url']
                ]
                
                # Add each surat jalan URL as a separate column
                row_data.extend(surat_jalan_urls)
                
                # Append the row to the sheet
                sheet.append_row(row_data, value_input_option="USER_ENTERED")
                
                st.success("✅ Data berhasil disimpan!")
                st.markdown(f"""
                **Links:**
                - [Folder Utama]({folders['main_folder_url']})
                - [Foto Segel]({segel_url})
                - [Foto Muat]({muat_url})
                - [Foto Surat Jalan]({folders['surat_jalan']['url']}) ({len(surat_jalan_files)} file)
                """)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.error("Silakan coba lagi atau hubungi administrator.")