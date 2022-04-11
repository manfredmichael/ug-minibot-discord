import pickle
import os.path, io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient.http import MediaFileUpload, MediaIoBaseDownload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']


def get_service():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    global drive_service
    drive_service = build('drive', 'v3', credentials=creds)
    
def upload_file(filename):
    file_id = search_file(filename)

    try: 
        file_metadata = {'name': filename}
        media = MediaFileUpload(filename,
                                mimetype='application/json')
        file = drive_service.files().update(body=file_metadata,
                                            media_body=media,
                                            fileId=file_id).execute()
    except TypeError:
        print('Failed to upload {}'.format(filename))

def download_file(filename):
    file_id = search_file(filename)

    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    with io.open(filename,'wb') as f:
        fh.seek(0)
        f.write(fh.read())

def search_file(keyword):
    results = drive_service.files().list(pageSize=1,
                                         fields="nextPageToken, files(id, name, kind, mimeType)",
                                         q="name contains '{}'".format(keyword)).execute()
    items = results.get('files', [])
    if not items:
        print('No files found.')
        return None
    else:
        return items[0]['id']

get_service()