from __future__ import print_function

# Adapted from https://developers.google.com/gmail/api/quickstart/python
import os
import base64
import httplib2
import time
import subprocess

from apiclient import discovery
from googleapiclient import errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'MailPrint Client'
UNREAD_LABEL = 'UNREAD'
PRINT_LABEL = 'Label_5'
USERID = 'me'
MAILPRINT_FOLDER = '/tmp/mailprint'
PRINTER_NAME = 'Brother_DCP-7065DN'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'mailprint.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_messages(service):
    results = service.users().messages().list(
        userId=USERID,
        labelIds=[UNREAD_LABEL, PRINT_LABEL]
    ).execute()
    return results.get('messages', [])


def get_message(service, message_id):
    return service.users().messages().get(
        userId=USERID,
        id=message_id
    ).execute()


def get_attachment(service, message_id, attachment_id):
    return service.users().messages().attachments().get(
        id=attachment_id,
        messageId=message_id,
        userId=USERID
    ).execute()


def remove_label(service, message_id):
    service.users().messages().modify(
        userId=USERID,
        id=message_id,
        body={'removeLabelIds': [PRINT_LABEL]}
    ).execute()


def main():
    """Shows basic usage of the Gmail API.

    Creates a Gmail API service object and outputs a list of label names
    of the user's Gmail account.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    messages = get_messages(service)

    if not messages:
        return 'No messages found.'

    if not os.path.exists(MAILPRINT_FOLDER):
        os.makedirs(MAILPRINT_FOLDER)

    for msg in messages:
        try:
            message = get_message(service, msg['id'])

            for part in message['payload']['parts']:
                attachment_id = None
                if part['filename']:
                    attachment_id = part['body']['attachmentId']

                if attachment_id is None:
                    continue

                attachment = get_attachment(
                    service,
                    msg['id'],
                    part['body']['attachmentId']
                )

                file_data = base64.urlsafe_b64decode(attachment['data']
                                                     .encode('UTF-8'))

                path = os.path.join('/', MAILPRINT_FOLDER, part['filename'])
                with open(path, 'wb+') as fsock:
                    fsock.write(file_data)

                cmd = ['lp', '-d {}'.format(PRINTER_NAME), path]
                subprocess.call(cmd, stderr=subprocess.STDOUT)

                time.sleep(5)

        except errors.HttpError as error:
            return 'An error occurred: %s' % error

        remove_label(service, msg['id'])


if __name__ == '__main__':
    main()
