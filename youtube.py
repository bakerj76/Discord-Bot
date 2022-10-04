# -*- coding: utf-8 -*-

# Sample Python code for youtube.playlists.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/guides/code_samples#python


from googleapiclient.discovery import build	
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import googleapiclient.discovery
import pickle
import os

SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
PICKLE_FILE = 'secrets/token.pickle'

def get_client():
	credentials = None
	if os.path.exists(PICKLE_FILE):
		with open(PICKLE_FILE, 'rb') as token:
			credentials = pickle.load(token)
			
	# If there are no (valid) credentials available, let the user log in.
	if not credentials or not credentials.valid:
		if credentials and credentials.expired and credentials.refresh_token:
			try:
				credentials.refresh(Request())
			except RefreshError:
				flow = InstalledAppFlow.from_client_secrets_file(
					CLIENT_SECRETS_FILE, 
					SCOPES
				)
				credentials = flow.run_local_server(port=0)
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				CLIENT_SECRETS_FILE, 
				SCOPES
			)
			credentials = flow.run_local_server(port=0)

		# Save the credentials for the next run
		with open(PICKLE_FILE, 'wb') as token:
			pickle.dump(credentials, token)

	# Get credentials and create an API client
	client = googleapiclient.discovery.build(
		API_SERVICE_NAME, 
		API_VERSION, 
		credentials=credentials
	)

	return client
