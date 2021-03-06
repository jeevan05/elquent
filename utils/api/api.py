#!/usr/bin/env python3.6
# -*- coding: utf8 -*-

'''
ELQuent.api
Eloqua API functions for other modules

Mateusz Dąbrowski
github.com/MateuszDabrowski
linkedin.com/in/mateusz-dabrowski-marketing/
'''

# Python imports
import os
import re
import sys
import json
import time
import base64
import pickle
import getpass
import webbrowser
import pyperclip
import requests
from colorama import Fore, Style, init

# Globals
naming = None
eloqua_key = None
eloqua_bulk = None
eloqua_rest = None
shared_list = None
asset_names = None
source_country = None

# Initialize colorama
init(autoreset=True)

# Predefined messege elements
ERROR = f'{Fore.WHITE}[{Fore.RED}ERROR{Fore.WHITE}] {Fore.YELLOW}'
WARNING = f'{Fore.WHITE}[{Fore.YELLOW}WARNING{Fore.WHITE}] '
SUCCESS = f'{Fore.WHITE}[{Fore.GREEN}SUCCESS{Fore.WHITE}] '
YES = f'{Style.BRIGHT}{Fore.GREEN}y{Fore.WHITE}{Style.NORMAL}'
NO = f'{Style.BRIGHT}{Fore.RED}n{Fore.WHITE}{Style.NORMAL}'

'''
=================================================================================
                                File Path Getter
=================================================================================
'''


def file(file_path):
    '''
    Returns file path to template files
    '''

    def find_data_file(filename):
        '''
        Returns correct file path for both script and frozen app
        '''
        if getattr(sys, 'frozen', False):
            datadir = os.path.dirname(sys.executable)
            return os.path.join(datadir, 'utils', 'api', filename)
        else:
            datadir = os.path.dirname(os.path.dirname(__file__))
            return os.path.join(datadir, 'api', filename)

    file_paths = {
        'click': find_data_file('click.p'),
        'eloqua': find_data_file('eloqua.p'),
        'country': find_data_file('country.p'),
        'naming': find_data_file('naming.json'),
        'image': find_data_file('image.jpg')
    }

    return file_paths.get(file_path)


'''
=================================================================================
                                Main API functions
=================================================================================
'''


def status_code(response, root):
    '''
    Arguments:
        reponse - response from api_request function
        root - root URL of API call
    Returns boolean of API connection.
    '''

    if (response.status_code >= 200) and (response.status_code < 400):
        print(f'{Fore.YELLOW}» {root} '
              f'{Fore.GREEN}({response.status_code})')
        connected = True
    elif response.status_code >= 400:
        print(f'{Fore.YELLOW}» {root} '
              f'{Fore.RED}({response.status_code})')
        connected = False
    else:
        print(f'{Fore.YELLOW}» {root} '
              f'{Fore.BLUE}({response.status_code})')
        connected = False

    return connected


def api_request(root, call='get', api='eloqua', params=None, debug=False, data=None, files=None):
    '''
    Arguments:
        root - root URL of API call
        call - GET/POST/PUT/DELETE
        api - either elouqa or click
        also: params, data, files for calls
    Returns response from API call

    If you want to print API connection status codes, set debug to True
    '''

    # Assings correct authorization method
    if api == 'eloqua':
        headers = {'Authorization': 'Basic ' + eloqua_key}
    elif api == 'click':
        click_api_key = pickle.load(open(file('click'), 'rb'))
        headers = {'X-Api-Key': click_api_key}
    if not files:
        headers['Content-Type'] = 'application/json'

    # Assings correct api call
    if call == 'get':
        response = requests.get(
            root,
            headers=headers,
            params=params)
    elif call == 'post':
        response = requests.post(
            root,
            headers=headers,
            data=data,
            files=files)
    elif call == 'put':
        response = requests.put(
            root,
            headers=headers,
            data=data,
            files=files)
    elif call == 'delete':
        response = requests.delete(root, headers=headers)

    # Prints status code
    if debug:
        status_code(response, root)

    return response


'''
=================================================================================
                                Eloqua Asset Helpers
=================================================================================
'''


def get_asset_id(asset):
    '''
    Returns valid ID of chosen Eloqua asset [integer]
    '''

    while True:
        print(
            f'\n{Fore.WHITE}» [{Fore.YELLOW}{asset.capitalize()}{Fore.WHITE}]',
            f'{Fore.WHITE}Write or copypaste {asset} ID or copy the code and click [Enter]', end='')
        asset_id = input(' ')
        if not asset_id:
            asset_id = pyperclip.paste()
            if len(asset_id) > 10:
                return None

        # Checks if input in numerical value
        try:
            asset_id = int(asset_id)
        except ValueError:
            print(f'{ERROR}It is not valid Eloqua {asset} ID')
            continue

        # Checks if there is asset with that ID
        try:
            asset_exists = eloqua_asset_get(asset_id, asset_type=asset)
        except json.decoder.JSONDecodeError:
            asset_exists = False

        # Gets ID confirmation from user
        if asset_exists:
            choice = ''
            while choice.lower() != 'y' and choice.lower() != 'n':
                print(
                    f'{Fore.WHITE}» Continue with {Fore.YELLOW}{asset_exists[0]}{Fore.WHITE}? {Fore.WHITE}({YES}/{NO}):', end=' ')
                choice = input('')
            if choice.lower() == 'y':
                return asset_id
            elif choice.lower() == 'n':
                continue
        else:
            print(f'{ERROR}Not found Eloqua {asset} with given ID')


def eloqua_asset_exist(name, asset):
    '''
    Returns True if there is already asset in Eloqua instance with that name
    '''
    # Gets required endpoint
    endpoint = asset_names.get(asset)
    endpoint += 's'  # for multiple assets endpoint

    # Gets data of requested asset
    root = f'{eloqua_rest}assets/{endpoint}'
    params = {'search': name}
    response = api_request(root, params=params)
    elq_asset = response.json()

    if elq_asset['total']:
        asset_id = elq_asset['elements'][0]['id']
        print(
            f'\n  {WARNING}{asset} "{name}" already exists! [ID: {asset_id}]')
        while True:
            print(
                f'  {Fore.WHITE}» Click [Enter] to continue with current name or [Q] to quit', end='')
            choice = input(' ')
            if not choice:
                return asset_id
            elif choice.lower() == 'q':
                print(f'\n{Fore.GREEN}Ahoj!')
                raise SystemExit
            else:
                print(
                    f'\n{ERROR}Entered value is not a valid choice!')
    else:
        return False


def eloqua_asset_html_name(name):
    '''
    Returns correct html_name for the asset
    '''
    html_name = ''
    date_element = re.compile(r'\d\d', re.UNICODE)
    local_name = name.split('_')[-2]  # Gets local name from asset name
    for part in local_name.split('-'):
        # Skip if part belongs to PSP
        if part.startswith(tuple(naming[source_country]['psp'])):
            continue
        # Skip if part is a date
        elif date_element.search(part):
            continue
        else:
            html_name += f'{part[:20]}-'
    # Gets asset type last part of html_name
    html_name += name.split('_')[-1]

    return html_name


def eloqua_asset_name():
    '''
    Returns correct name for the asset
    '''
    while True:
        name = input(' ')
        if not name:
            name = pyperclip.paste()
        name_check = name.split('_')
        if len(name_check) != 5:
            print(
                f'{ERROR}Expected 5 name elements, found {len(name_check)}')
        elif '/' in name:
            print(
                f'{ERROR}"/PSP" is expected only in the camapign name')
        elif name_check[0][:2] != 'WK':
            print(
                f'{ERROR}"{name_check[0]}" is not existing country code')
        elif name_check[1] not in naming[source_country]['segment']:
            print(
                f'{ERROR}"{name_check[1]}" is not existing segment name')
        elif name_check[2] not in naming['campaign']:
            print(
                f'{ERROR}"{name_check[2]}" is not existing campaign type')
        else:
            return name
        print(f'{Fore.YELLOW}Please write or copypaste correct name:')


def eloqua_asset_get(asset_id, asset_type, depth=''):
    '''
    Requires asset_id, asset_type and optionally depth
    Returns name and optionally code of Eloqua asset of given ID
    '''

    # Gets required endpoint
    endpoint = asset_names.get(asset_type)

    # Gets data of requested asset
    root = f'{eloqua_rest}assets/{endpoint}/{asset_id}'
    params = {'depth': 'complete'}
    response = api_request(root, params=params)
    asset_response = response.json()

    # Returns full response
    if depth == 'complete':
        return asset_response

    # Gets name and code of the asset
    name = asset_response['name']
    if asset_type in ['landingPage', 'email']:
        code = asset_response['htmlContent']['html']
    elif asset_type == 'form':
        code = asset_response['customCSS'] + asset_response['html']
    elif asset_type == 'sharedContent':
        code = asset_response['contentHtml']

    if asset_type in ['landingPage', 'email', 'form']:
        return (name, code)
    else:
        return name


def eloqua_get_assets(query, asset_type, count='', page='1', depth='complete'):
    '''
    Requires query string, asset_type and optionally count, pagination, depth
    Returns partial list of assets and their full count
    '''
    # Sets output page element count to bigger for smaller response depth
    if not count and depth == 'minimal':
        count = 500
    elif not count:
        count = 20

    # Gets required endpoint
    endpoint = asset_names.get(asset_type) + 's'

    # Builds the API request
    payload = {
        'search': query,  # Filter by query
        'depth': depth,  # Sets required depth of data output
        'orderBy': 'id DESC',  # Sorts from newest to oldest to get most important first
        'count': count,  # Sets count according to depth
        'page': page  # Pagination of outcomes
    }

    # Creating a get call to Eloqua API
    root = f'{eloqua_rest}assets/{endpoint}'
    response = api_request(root, params=payload)
    assets = response.json()
    if assets['total'] > count:
        print(f'{Fore.GREEN}|', end='', flush=True)

    return assets


def eloqua_get_dependencies(asset_id, asset_type, depth='minimal'):
    '''
    Requires asset_id, asset_type and optionally count, pagination, depth
    Returns partial list of dependencies and their full count
    '''

    # Gets required endpoint
    endpoint = asset_names.get(asset_type) + '/' + asset_id + '/dependencies'

    # Builds the API request
    payload = {
        'depth': depth,  # Sets required depth of data output
    }

    # Creating a get call to Eloqua API
    root = f'{eloqua_rest}assets/{endpoint}'
    response = api_request(root, params=payload)
    try:
        dependencies = response.json()
    except json.decoder.JSONDecodeError:
        dependencies = []

    return dependencies


'''
=================================================================================
                                Eloqua Authentication
=================================================================================
'''


def get_eloqua_auth(country):
    '''
    Returns Eloqua Root URL and creates globals with auth and bulk/rest roots
    '''

    # Creates global source_country from main module
    global source_country
    source_country = country

    global asset_names
    asset_names = {
        'landingPage': 'landingPage',
        'form': 'form',
        'email': 'email',
        'campaign': 'campaign',
        'program': 'program',
        'sharedFilter': 'contact/filter',
        'segment': 'contact/segment',
        'image': 'image',
        'file': 'importedFile',
        'sharedContent': 'contentSection',
        'dynamicContent': 'dynamicContent',
        'fieldMerge': 'fieldMerge'
    }

    # Gets data from naming.json
    with open(file('naming'), 'r', encoding='utf-8') as f:
        global naming
        naming = json.load(f)

    def get_eloqua_root():
        '''
        Returns Eloqua base URL for your instance.
        '''
        root = 'https://login.eloqua.com/id'
        response = api_request(root=root)
        login_data = response.json()

        return login_data

    while True:
        # Gets Eloqua user details if they are already stored
        print()
        if not os.path.isfile(file('eloqua')):
            print(f'{Fore.YELLOW}» {Fore.WHITE}Enter Eloqua Company name: ', end='')
            eloqua_domain = input(' ')
            print(f'{Fore.YELLOW}» {Fore.WHITE}Enter Eloqua User name: ', end='')
            eloqua_user = input(' ')
            eloqua_auth = (eloqua_domain, eloqua_user)
            pickle.dump(eloqua_auth, open(file('eloqua'), 'wb'))
        eloqua_domain, eloqua_user = pickle.load(open(file('eloqua'), 'rb'))
        print(f'{Fore.YELLOW}» {Fore.WHITE}Enter Eloqua Password: ', end='')
        eloqua_password = getpass.getpass(' ')

        # Converts domain, user and  to Eloqua Auth Key
        global eloqua_key
        eloqua_key = bytes(eloqua_domain + '\\' +
                           eloqua_user + ':' +
                           eloqua_password, 'utf-8')
        eloqua_key = str(base64.b64encode(eloqua_key), 'utf-8')

        # Gets Eloqua root URL
        try:
            login_data = get_eloqua_root()
            eloqua_root = login_data['urls']['base']
        except TypeError:
            print(f'{ERROR}Login failed!')
            os.remove(file('eloqua'))
            continue
        if eloqua_root:
            break

    # Creates globals related to Eloqua API
    global eloqua_bulk
    eloqua_bulk = eloqua_root + '/api/BULK/2.0/'
    global eloqua_rest
    eloqua_rest = eloqua_root + '/api/REST/2.0/'

    return eloqua_key


'''
=================================================================================
                            Upload Contacts API Flow
=================================================================================
'''


def eloqua_create_sharedlist(export, choice):
    '''
    Creates shared list for contacts
    Requires 'export' dict with webinars and conctacts in format:
    {'listName': ['email', 'email']}
    '''
    outcome = []
    print(f'\n{Fore.BLUE}Saving to shared list:', end='')

    # Unpacks export
    for name, contacts in export.items():
        root = f'{eloqua_rest}assets/contact/list'
        data = {'name': f'{name}',
                'description': 'ELQuent API Upload',
                'folderId': f'{shared_list}'}
        response = api_request(
            root, call='post', data=json.dumps(data))
        sharedlist = response.json()

        print(
            f'\n{Fore.WHITE}» [{Fore.YELLOW}{len(contacts)}{Fore.WHITE}] {name}')
        # Simple shared list creation
        if response.status_code == 201:
            print(f'{Fore.GREEN}  [Created]', end=' ')
            list_id = int(sharedlist['id'])
        # Shared list already exists
        else:
            while True:  # Asks user what to do next
                if not choice:
                    print(f'\n{Fore.YELLOW}Shared list with that name already exist.',
                          f'\n{Fore.WHITE}[{Fore.YELLOW}0{Fore.WHITE}]\tStop importing to Eloqua',
                          f'\n{Fore.WHITE}[{Fore.YELLOW}1{Fore.WHITE}]\tAppend contacts to existing shared list')
                    if len(export) == 1:
                        print(
                            f'{Fore.WHITE}[{Fore.YELLOW}2{Fore.WHITE}]\tChange upload name')
                    print(
                        f'{Fore.WHITE}Enter number associated with your choice:', end='')
                    choice = input(' ')
                if not choice or choice == '0':  # Dropping import
                    return False
                elif choice == '1' or choice == 'append':  # Appending data to existing shared list
                    print(
                        f'{Fore.YELLOW}  [Exists]{Fore.GREEN} » [Append]', end=' ')
                    list_id = sharedlist[0]['requirement']['conflictingId']
                    break
                # Changing name and trying again
                elif choice == '2' and len(export) == 1:
                    name_split = name.split('_')
                    print(
                        f'\n{Fore.WHITE}» Write different name ending for the shared list upload: ', end='')
                    ending = input(' ')
                    new_name = '_'.join(name_split[:4] + [ending])
                    new_export = {new_name: contacts}
                    outcome = eloqua_create_sharedlist(new_export, '')
                    return outcome

        uri = eloqua_import_contact_definition(name, list_id)
        count = eloqua_import_contacts(contacts, uri)
        status = eloqua_post_sync(uri)
        if status == 'success':
            # Sync_id is syncedInstanceUri from sync response
            import_id = (uri.split('/'))[-1]
            root = eloqua_bulk + f'contacts/imports/{import_id}'
            response = api_request(root, call='delete')
        outcome.append((list_id, name, count, status))

    return outcome


def eloqua_import_contact_definition(name, list_id):
    '''
    Request to obtain uri key for data upload
    Requires name of import and ID of shared list
    Returns uri key needed for data upload
    '''
    data = {'name': name,
            'fields': {
                'SourceCountry': '{{Contact.Field(C_Source_Country1)}}',
                'EmailAddress': '{{Contact.Field(C_EmailAddress)}}'},
            'identifierFieldName': 'EmailAddress',
            'isSyncTriggeredOnImport': 'false',
            'syncActions': {
                'action': 'add',
                'destination': '{{ContactList[%s]}}' % list_id}}
    root = eloqua_bulk + 'contacts/imports'
    response = api_request(root, call='post', data=json.dumps(data))
    import_eloqua = response.json()
    uri = import_eloqua['uri'][1:]

    return uri


def eloqua_import_contacts(contacts, uri):
    '''
    Uploads contacts from ClickWebinar to Eloqua
    Requires list of contacts for upload and uri key
    Returns count of uploaded contacts
    '''
    count = 0
    upload = []
    record = {}
    for user in contacts:
        record = {'SourceCountry': source_country,
                  'EmailAddress': user}
        upload.append(record)
        count += 1
    root = eloqua_bulk + uri + '/data'
    api_request(root, call='post', data=json.dumps(upload))

    return count


'''
=================================================================================
                    Upload External Activities API Flow
=================================================================================
'''


def eloqua_create_webinar_activity(attendees, activities):
    '''
    Requires list of attendee e-mails and list of list containg activities in format:
    [E-mail, CampaignId, AssetName, AssetType, AssetDate, ActivityType]
    '''

    # Upload contacts to shared list for correct CLS
    print(f'\n{Fore.YELLOW}» Uploading attendees')
    list_id = naming[source_country]['id']['activity_shared_list']
    contact_uri = eloqua_import_contact_definition(
        'WKPL_ELQuent_Webinar-attendees-upload', list_id)
    eloqua_import_contacts(attendees, contact_uri)
    contact_status = eloqua_post_sync(contact_uri)
    if contact_status == 'success':
        # Sync_id is syncedInstanceUri from sync response
        import_id = (contact_uri.split('/'))[-1]
        root = eloqua_bulk + f'contacts/imports/{import_id}'
        api_request(root, call='delete')

    # Upload external activities
    print(f'\n{Fore.YELLOW}» Uploading activities')
    activity_uri = eloqua_import_webinar_activity_definition()
    eloqua_import_webinar_activity(activities, activity_uri)
    activity_status = eloqua_post_sync(activity_uri)
    if activity_status == 'success':
        # Sync_id is syncedInstanceUri from sync response
        import_id = (activity_uri.split('/'))[-1]
        root = eloqua_bulk + f'contacts/imports/{import_id}'
        api_request(root, call='delete')

    return


def eloqua_import_webinar_activity_definition():
    '''
    Returns uri key of import defininition needed for data upload
    '''
    data = {
        'name': f'WK{source_country}_Webinar_ExternalActivityImport_ELQuent',
        'fields': {
            'C_EmailAddress': '{{Activity.Contact.Field(C_EmailAddress)}}',
            'CampaignID': '{{Activity.Campaign.Id}}',
            'AssetName': '{{Activity.Asset.Name}}',
            'AssetType': '{{Activity.Asset.Type}}',
            'AssetDate': '{{Activity.CreatedAt}}',
            'ActivityType': '{{Activity.Type}}'
        },
        'updateRule': 'always',
        'dataRetentionDuration': 'PT1H',
    }
    root = eloqua_bulk + 'activities/imports'
    response = api_request(root, call='post', data=json.dumps(data))
    import_eloqua = response.json()
    uri = import_eloqua['uri'][1:]

    return uri


def eloqua_import_webinar_activity(activities, uri):
    '''
    Uploads contacts from ClickWebinar to Eloqua
    Requires list of contacts for upload and uri key
    Returns count of uploaded contacts
    '''
    count = 0
    upload = []
    for activity in activities:
        record = {
            'C_EmailAddress': activity[0],
            'CampaignID': activity[1],
            'AssetName': activity[2],
            'AssetType': activity[3],
            'AssetDate': activity[4],
            'ActivityType': activity[5]
        }
        upload.append(record)
        count += 1
    root = eloqua_bulk + uri + '/data'
    api_request(root, call='post', data=json.dumps(upload))

    return count


'''
=================================================================================
                            Contact Segment API
=================================================================================
'''


def eloqua_segment_refresh(segment_id):
    '''
    Returns segment count when segment is refreshed (string)
    '''

    # Post refresh queue
    root = eloqua_rest + 'assets/contact/segment/queue/' + segment_id
    queue = api_request(root, call='post')
    queue_data = queue.json()
    queued_at = queue_data['queuedAt']

    # Check if queue has been resolved and segment is refreshed
    root = eloqua_rest + 'assets/contact/segment/' + segment_id + '/count'
    while True:
        time.sleep(10)
        refresh = api_request(root)
        refresh_data = refresh.json()
        calculated_at = refresh_data.get('lastCalculatedAt', '0')
        if int(calculated_at) > int(queued_at):
            break

    return refresh_data['count']


'''
=================================================================================
                    Export Bouncebacks Activity API Flow
=================================================================================
'''


def eloqua_post_export(data, export_type):
    '''
    Creates definition for activity export
    Requires data and type (for example 'activity')
    Returns uri key needed for data download
    '''
    if export_type == 'activity':
        endpoint = 'activities'

    root = eloqua_bulk + f'{endpoint}/exports'
    response = api_request(root, call='post', data=json.dumps(data))
    export_eloqua = response.json()
    uri = export_eloqua['uri'][1:]

    return uri


'''
=================================================================================
                                Eloqua Sync API
=================================================================================
'''


def eloqua_post_sync(uri, return_uri=False):
    '''
    Requests to sync import
    Checks status of sync
    Requires uri key
    Returns status of sync
    '''

    # Requests sync
    root = eloqua_bulk + 'syncs'
    sync_body = {'syncedInstanceUri': f'/{uri}'}
    response = api_request(root, call='post', data=json.dumps(sync_body))
    sync_eloqua = response.json()

    # Checks stats of sync
    sync_uri = sync_eloqua['uri']
    status = sync_eloqua['status']

    sync_counter = 1
    while True:
        root = eloqua_bulk + sync_uri
        sync_body = {'syncedInstanceUri': f'/{sync_uri}'}
        response = api_request(root)
        sync_status = response.json()
        status = sync_status['status']
        print(f'{Fore.BLUE}{status}/', end='', flush=True)
        if status in ['warning', 'error', 'success']:
            eloqua_log_sync(sync_uri)
            break
        time.sleep(5 * sync_counter)
        sync_counter += 1

    if return_uri:
        return sync_uri

    return status


def eloqua_log_sync(sync_uri):
    '''
    Shows log for problematic sync
    Requires uri key to get id of sync
    Returns logs of sync
    '''
    print(f'{Fore.WHITE}{sync_uri[1:]}')
    sync_id = (sync_uri.split('/'))[-1]
    root = eloqua_bulk + f'syncs/{sync_id}/logs'
    response = api_request(root)
    logs_eloqua = response.json()
    for item in logs_eloqua['items']:
        if item['severity'] == 'warning':
            print(f'\t{Fore.YELLOW}› {item["count"]} {item["message"]}')
        if item['message'] in ['Contacts created.', 'Contacts updated.']:
            print(f'\t{Fore.GREEN}› {item["count"]} {item["message"]}')

    return logs_eloqua


def eloqua_sync_data(sync_uri):
    '''
    Returns json of data from response
    '''
    offset = 0
    response = []
    while True:
        root = eloqua_bulk + f'{sync_uri}/data'
        params = {'limit': '50000',
                  'offset': str(offset)}
        partial_response = api_request(root, params=params)
        partial_response = partial_response.json()
        if partial_response['totalResults'] > 0:
            response.extend(partial_response['items'])
        if not partial_response['hasMore']:
            break
        offset += 50000

    return response


'''
=================================================================================
                                Landing Page API
=================================================================================
'''


def eloqua_create_landingpage(name, code):
    '''
    Requires name and code of the landing page to create LP in Eloqua
    Returns Landing Page ID, eloqua asset url and direct url
    '''
    # Adds source contry to received asset name
    name = f'WK{source_country}_{name}'

    # Checks if there already is LP with that name
    eloqua_asset_exist(name, asset='landingPage')

    # Chosses correct folder ID for upload
    segment = name.split('_')[1]
    folder_id = naming[source_country]['id']['landingpage'].get(segment)

    # Creates correct html_name
    html_name = eloqua_asset_html_name(name)

    # Gets id and url of microsite
    microsite_id = naming[source_country]['id']['microsite'][0]
    microsite_link = naming[source_country]['id']['microsite'][1]

    while True:
        # Creating a post call to Eloqua API
        root = f'{eloqua_rest}assets/landingPage'
        data = {
            'name': name,  # asset name
            'description': 'ELQuent API Upload',
            'folderId': folder_id,
            'micrositeId': microsite_id,  # html name domain
            'relativePath': f'/{html_name}',  # html name path
            'htmlContent': {
                'type': 'RawHtmlContent',
                'html': code
            }
        }
        response = api_request(
            root, call='post', data=json.dumps(data))
        landing_page = response.json()

        # Checks if there is error
        if isinstance(landing_page, list)\
                and len(landing_page) == 1\
                and landing_page[0]['type'] == 'ObjectValidationError'\
                and landing_page[0]['property'] == 'relativePath'\
                and landing_page[0]['requirement']['type'] == 'UniquenessRequirement':

            print(
                f'\n  {ERROR}URL ending "/{html_name}" already exists!',
                f'\n  {Fore.WHITE}» Enter new URL ending:', end='')
            html_name = input(' ')
            if not html_name:
                html_name = pyperclip.paste()
            continue
        elif isinstance(landing_page, list):  # Other errors
            print(f'{Fore.YELLOW}{landing_page}')
        elif landing_page['type'] == 'LandingPage':
            break
        else:  # Weird cases
            print(f'{Fore.YELLOW}{landing_page}')

    # Open in new tab
    lp_id = landing_page['id']
    asset_url = naming['root'] + '#landing_pages&id=' + lp_id
    direct_url = microsite_link + landing_page['relativePath']
    print(f'{Fore.WHITE}» {SUCCESS}Created Eloqua Landing Page ID: {lp_id}')
    webbrowser.open(asset_url, new=2, autoraise=False)

    return (lp_id, asset_url, direct_url)


def eloqua_put_landingpage(lp_id, data):
    '''
    Requires id and data of the landing page to update LP in Eloqua
    Returns success bool
    '''

    # Creating a put call to Eloqua API
    root = f'{eloqua_rest}assets/landingPage/{lp_id}'
    response = api_request(
        root, call='put', data=json.dumps(data))
    landing_page = response.json()

    # Checks if there is error
    if isinstance(landing_page, list) or landing_page['type'] != 'LandingPage':
        print(f'{Fore.YELLOW}{landing_page}')
        return False

    return True


'''
=================================================================================
                                SharedFilter API
=================================================================================
'''


def eloqua_create_filter(name, data):
    '''
    Requires name and json data of the shared filter to create it in Eloqua
    Returns Filter ID and response of created filter
    '''
    # Checks if there already is Form with that name
    eloqua_asset_exist(name, asset='sharedFilter')

    # Creating a post call to Eloqua API
    root = f'{eloqua_rest}assets/contact/filter'
    response = api_request(
        root, call='post', data=json.dumps(data))
    sharedfilter = response.json()

    # Open in new tab
    sharedfilter_id = sharedfilter['id']
    print(f'{Fore.WHITE}» {SUCCESS}Created Eloqua Filter ID: {sharedfilter_id}')

    return (sharedfilter_id, sharedfilter)


'''
=================================================================================
                                    Form API
=================================================================================
'''


def eloqua_get_form_data(form_id):
    '''
    Returns form data of Form with given ID
    '''
    all_fills = []
    page = 1

    while True:
        # Gets fills of requested form
        root = f'{eloqua_rest}data/form/{form_id}'
        params = {'depth': 'complete',
                  'count': '100',
                  'page': page}
        response = api_request(root, params=params)
        fills = response.json()

        all_fills.extend(fills['elements'])

        # Stops iteration when full list is obtained
        if fills['total'] - page * int(params.get('count')) < 0:
            break

        # Increments page to get next part of outcomes
        page += 1

    return (all_fills, fills['total'])


def eloqua_create_form(name, data):
    '''
    Requires name and json data of the form to create it in Eloqua
    Returns Form ID and response of created form
    '''
    # Checks if there already is Form with that name
    eloqua_asset_exist(name, asset='form')

    # Creating a post call to Eloqua API
    root = f'{eloqua_rest}assets/form'
    response = api_request(
        root, call='post', data=json.dumps(data))
    form = response.json()

    # Open in new tab
    try:
        form_id = form['id']
    except TypeError:
        conflicting_form = form[0]['requirement'].get('conflictingId')
        conflicting_value = form[0].get('value')
        print(
            f'{ERROR}Form ID {conflicting_form} already has the same html name: {conflicting_value}')
        input(' ')
        raise SystemExit
    print(f'{Fore.WHITE}» {SUCCESS}Created Eloqua Form ID: {form_id}')

    return (form_id, form)


def eloqua_update_form(form_id, css='', html='', processing='', open_form=False):
    '''
    Requires id and json data of the form to update it in Eloqua
    Returns Form ID and Form JSON
    '''
    # Gets current data of form to update
    data = eloqua_asset_get(form_id, asset_type='form', depth='complete')
    data['htmlName'] = form_id
    if css:
        data['customCSS'] = css
    if html:
        if 'FORM_ID' in html:
            html.replace('FORM_ID', form_id)
        data['html'] = html
    if processing:
        data['processingSteps'] = processing

    # Creating a post call to Eloqua API and taking care of emoticons encoding
    root = f'{eloqua_rest}assets/form/{form_id}'
    response = api_request(
        root, call='put', data=json.dumps(data))
    form_json = response.json()

    # Open in new tab

    form_id = form_json['id']
    url = naming['root'] + '#forms&id=' + form_id
    print(
        f'{Fore.WHITE}» {SUCCESS}Updated Eloqua Form ID: {form_id}')
    if open_form:
        webbrowser.open(url, new=2, autoraise=False)

    return (form_id, form_json)


'''
=================================================================================
                                    E-mail API
=================================================================================
'''


def eloqua_fill_mail_params(name):
    '''
    Returns eloqua_create_email data based on settings of similar mails from the past
    '''

    def json_fill(name, gatherer):
        '''
        Tries to get necessary data for e-mail upload from json file
        '''
        try:
            check_name = '_'.join(name[-2:])
            gatherer[0].append(naming[source_country]
                               ['mail']['by_name'][check_name][gatherer[1]])
            return True
        except KeyError:
            try:
                gatherer[0].append(naming[source_country]
                                   ['mail']['by_type'][(name[-3])][gatherer[1]])
                return True
            except KeyError:
                return False

    def build_gatherers(sender_mail, sender_name, reply_mail, folder_id, footer, header, group_id):
        '''
        Returns updated gatherers list
        '''
        gatherers = [
            (sender_mail, 'senderEmail'),
            (sender_name, 'senderName'),
            (reply_mail, 'replyToEmail'),
            (folder_id, 'folderId'),
            (footer, 'emailFooterId'),
            (header, 'emailHeaderId'),
            (group_id, 'emailGroupId')
        ]

        return gatherers

    def gatherer_fill(gatherer):
        '''
        If succesfully found param value, adds it to data dict
        '''
        if len(gatherer[0]) == 1:
            data[gatherer[1]] = gatherer[0][0]

    def eloqua_search_emails(phrase):
        '''
        Returns information about e-mails with phrase
        '''
        # Gets data of requested e-mail
        root = f'{eloqua_rest}assets/emails'
        params = {'depth': 'complete',
                  'search': f'{phrase}*',
                  'orderBy': 'id DESC',
                  'count': '6'}
        response = api_request(root, params=params)
        email = response.json()

        return email

    '''
    =================================================== Prepares necessary data structures
    '''

    # Builds search name to use for fillers
    name_split = name.split('_')
    local_name = name_split[3].split('-')
    search_full_name = name_split[:-1]
    search_name = name_split[:3]
    search_name.append(local_name[0])

    # Start building data dict
    data = {}
    data['name'] = name
    data['description'] = 'ELQuent API Upload'
    data['bounceBackEmail'] = naming[source_country]['mail']['bounceback']
    data['replyToName'] = naming[source_country]['mail']['reply_name']
    data['isTracked'] = 'true'

    # Builds gatherers for data various sources
    sender_mail = []
    sender_name = []
    reply_mail = []
    folder_id = []
    footer = []
    header = []
    group_id = []

    '''
    =================================================== Step 1: Fill from json
    '''

    # Gatherer list to iterate over each approach to fill
    gatherers = build_gatherers(
        sender_mail, sender_name, reply_mail, folder_id, footer, header, group_id)

    # Fills data from json
    for gatherer in gatherers:
        if json_fill(search_name, gatherer):
            gatherer_fill(gatherer)

    # Updates gatherers to keep only missing ones
    gatherers = [(x, y) for (x, y) in gatherers if len(x) != 1]

    # Returns data if all data elements were filled
    try:
        if data['senderEmail']\
                and data['senderName']\
                and data['replyToEmail']\
                and data['folderId']\
                and data['emailFooterId']\
                and data['emailHeaderId']\
                and data['emailGroupId']:
            print(f'\n{Fore.WHITE}» {SUCCESS}E-mail data ready for upload')
            for value in data.items():
                print(
                    f'   {Fore.YELLOW}› {Fore.GREEN}{value[0]}{Fore.WHITE} {value[1]}')
            return data
    except KeyError:
        pass

    '''
    =================================================== Step 2: Fill from history
    '''

    # If there is still something to fill, tries fill from last 10 similar
    search_full_phrase = '_'.join(search_full_name)
    search_phrase = '_'.join(search_name)

    for search_query in [search_full_phrase, search_phrase]:
        previous_mails = eloqua_search_emails(search_query)

        # Fills gatherers with data
        for mail in previous_mails['elements']:
            for gatherer in gatherers:
                try:
                    gatherer[0].append(mail[gatherer[1]])
                except KeyError:
                    continue

        # Deduplicates to check for pattern
        sender_mail = list(set(sender_mail))
        sender_name = list(set(sender_name))
        reply_mail = list(set(reply_mail))
        folder_id = list(set(folder_id))
        footer = list(set(footer))
        header = list(set(header))
        if not header:
            header = ['9']  # Default empty header
        group_id = list(set(group_id))

        # Rebuilds gatherers list
        gatherers = build_gatherers(
            sender_mail, sender_name, reply_mail, folder_id, footer, header, group_id)

        # Fills data if there is a single pattern
        for gatherer in gatherers:
            gatherer_fill(gatherer)

        # Updates gatherers to keep only missing ones
        gatherers = [(x, y) for (x, y) in gatherers if len(x) != 1]

        # Returns data if all data elements were filled
        try:
            if data['senderEmail']\
                    and data['senderName']\
                    and data['replyToEmail']\
                    and data['folderId']\
                    and data['emailFooterId']\
                    and data['emailHeaderId']\
                    and data['emailGroupId']:
                # If gathering data from broader search, gets confirmation on chosen e-mail sender
                if search_query == search_phrase:
                    print(f'\n{Fore.WHITE}» Continue with {Fore.YELLOW}{data["senderEmail"]}',
                          f'{Fore.WHITE}as sender e-mail? ({YES}/{NO}):', end=' ')
                    sender_acceptance = input('')
                    if sender_acceptance.lower() == 'n':
                        data['senderEmail'] = ''
                        data['replyToEmail'] = ''
                        raise KeyError
                print(f'\n{Fore.WHITE}» {SUCCESS}E-mail data ready for upload:')
                for value in data.items():
                    print(
                        f'   {Fore.YELLOW}› {Fore.GREEN}{value[0]}{Fore.WHITE} {value[1]}')
                return data
        except KeyError:
            pass

    '''
    =================================================== Step 3: Fill from user input
    '''

    # Fill sender/reply e-mail address based on user choice
    if not data.get('senderEmail', False):
        sender_mail = naming[source_country]['mail']['senders']
        print(f'\n{Fore.GREEN}Choose sender and reply e-mail address:')
        for i, sender in enumerate(sender_mail):
            print(
                f'{Fore.WHITE}[{Fore.YELLOW}{i}{Fore.WHITE}]\t» {sender}')
        print(
            f'{Fore.WHITE}[{Fore.YELLOW}S{Fore.WHITE}]\t» Skip choosing sender e-mail')
        while True:
            print(
                f'{Fore.YELLOW}Enter number associated with e-mail address or write it down:', end='')
            choice = input(' ')
            valid_mail = re.compile(
                r'([\w\.\-\+]+?@[\w\.\-\+]+?\.[\w\.\-\+]+?)', re.UNICODE)
            if valid_mail.findall(choice):
                data['senderEmail'] = choice
                data['replyToEmail'] = choice
                break
            if choice.lower() == 's':
                print(
                    f'\n{WARNING}Remember to fill sender and reply e-mail addresses in Eloqua')
                break
            try:
                choice = int(choice)
            except (TypeError, ValueError):
                print(f'{ERROR}Please enter numeric value!')
                choice = ''
                continue
            if 0 <= choice < len(sender_mail):
                data['senderEmail'] = sender_mail[choice]
                data['replyToEmail'] = sender_mail[choice]
                break
            else:
                print(
                    f'{ERROR}Entered value does not belong to any e-mail address!')
                choice = ''

    # If there is no chosen e-mail group
    if not data.get('emailGroupId', False):
        print(f'\n{Fore.GREEN}Choose e-mail group:')
        for group in naming[source_country]['mail']['by_group'].items():
            print(
                f'{Fore.WHITE}[{Fore.YELLOW}{group[0]}{Fore.WHITE}]\t» {group[1]["group_name"]}')
        print(
            f'{Fore.WHITE}[{Fore.YELLOW}S{Fore.WHITE}]\t» Skip choosing e-mail group')
        while True:
            print(
                f'{Fore.YELLOW}Enter number associated with chosen e-mail group:', end='')
            choice = input(' ')
            if choice.lower() == 's':
                print(
                    f'\n{WARNING}Remember to fill e-mail group in Eloqua')
                break
            try:
                naming[source_country]['mail']['by_group'][choice]['group_name']
            except KeyError:
                print(f'{ERROR}Entered value does not belong to any e-mail group!')
            else:
                data['emailGroupId'] = choice
                break

    # If there is chosen e-mail group, but there is no e-mail footer yet in data
    if not data.get('emailFooterId', False) and data.get('emailGroupId', False):
        group_id = data.get('emailGroupId', False)
        if group_id:
            try:
                data['emailFooterId'] = naming[source_country]['mail']['by_group'][group_id]['emailFooterId']
            except KeyError:
                print(
                    f'\n{WARNING}Remember to pick e-mail footer in Eloqua')

    print(f'\n{Fore.WHITE}» {SUCCESS}E-mail data ready for upload:')
    for value in data.items():
        print(
            f'   {Fore.YELLOW}› {Fore.GREEN}{value[0]}{Fore.WHITE} {value[1]}')

    return data


def eloqua_create_email(name, code):
    '''
    Requires name and code of the email to create it in Eloqua
    Returns E-mail ID
    '''

    # Checks if there already is E-mail with that name
    eloqua_asset_exist(name, asset='email')

    # Cleans technical comments
    code = code.replace('<!--pre-start-->', '').replace('<!--pre-end-->', '')
    code = code.replace('<br>', '<br/>')

    # Gets required data for the API call
    data = eloqua_fill_mail_params(name)
    data['isTracked'] = 'true'
    data['htmlContent'] = {
        'type': 'RawHtmlContent',
        'html': code
    }

    # Gets subject line for the e-mail
    while True:
        print(f'\n{Fore.YELLOW}»{Fore.WHITE} Write or copypaste',
              f'{Fore.YELLOW}e-mail subject{Fore.WHITE} and click [Enter] or [S]kip')
        subject = input(' ')
        if not subject:
            subject = pyperclip.paste()
            if not subject:
                print(f'\n{ERROR}Subject can not be blank')
                continue
        elif len(subject) > 100:
            print(f'\n{ERROR}Subject is over 100 characters long')
            continue
        else:
            break
    if subject.lower() != 's':
        data['subject'] = subject

    # Creating a post call to Eloqua API
    root = f'{eloqua_rest}assets/email'
    response = api_request(
        root, call='post', data=json.dumps(data, ensure_ascii=False).encode('utf-8'))
    email = response.json()

    # Open in new tab
    email_id = email['id']
    url = naming['root'] + '#emails&id=' + email_id
    print(
        f'\n{Fore.WHITE}» {SUCCESS}Created Eloqua E-mail ID: {email_id}')
    webbrowser.open(url, new=2, autoraise=False)

    return email_id


def eloqua_update_email(email_id, code):
    '''
    Requires id and code of the email to update it in Eloqua
    Returns E-mail ID
    '''
    # Gets current data of e-mail to update
    old_data = eloqua_asset_get(email_id, asset_type='email', depth='complete')
    code = code.replace('"', '\"').replace('<br>', '<br/>')

    data = {
        'type': 'Email',
        'isTracked': 'true',
        'htmlContent': {
            'type': 'RawHtmlContent',
            'html': code
        }
    }

    # Takes care of case where there is lack of element in source mail
    for element in ['currentStatus', 'id', 'createdAt', 'createdBy',
                    'folderId', 'name', 'updatedAt', 'updatedBy', 'bounceBackEmail',
                    'emailFooterId', 'emailGroupId', 'emailHeaderId', 'replyToEmail',
                    'replyToName', 'senderEmail', 'senderName', 'subject']:
        try:
            data[element] = old_data[element]
        except KeyError:
            continue

    # Creating a post call to Eloqua API and taking care of emoticons encoding
    root = f'{eloqua_rest}assets/email/{email_id}'
    response = api_request(
        root, call='put', data=json.dumps(data, ensure_ascii=False).encode('utf-8'))
    email = response.json()

    # Open in new tab
    email_id = email['id']
    url = naming['root'] + '#emails&id=' + email_id
    print(
        f'\n{Fore.WHITE}[{Fore.YELLOW}UPDATED{Fore.WHITE}] Eloqua E-mail ID: {email_id}')
    webbrowser.open(url, new=2, autoraise=False)

    return email_id


'''
=================================================================================
                                Campaign API
=================================================================================
'''


def eloqua_create_campaign(name, data):
    '''
    Requires name and json data of the campaign canvas to create it in Eloqua
    Returns ID and reponse of created campaign canvas
    '''
    # Checks if there already is Campaign with that name
    eloqua_asset_exist(name, asset='campaign')

    # Creating a post call to Eloqua API
    root = f'{eloqua_rest}assets/campaign'
    response = api_request(
        root, call='post', data=json.dumps(data))
    campaign = response.json()

    # Open in new tab
    campaign_id = campaign['id']
    url = naming['root'] + '#campaigns&id=' + campaign_id
    print(f'{Fore.WHITE}» {SUCCESS}Created Eloqua Campaign ID: {campaign_id}')
    webbrowser.open(url, new=2, autoraise=True)

    return (campaign_id, campaign)


'''
=================================================================================
                                Program API
=================================================================================
'''


def eloqua_create_program(name, data):
    '''
    Requires name and json data of the program canvas to create it in Eloqua
    Returns ID and reponse of created program canvas
    '''
    # Checks if there already is Campaign with that name
    eloqua_asset_exist(name, asset='program')

    # Creating a post call to Eloqua API
    root = f'{eloqua_rest}assets/program'
    response = api_request(
        root, call='post', data=json.dumps(data))
    program = response.json()

    # Open in new tab
    program_id = program['id']
    url = naming['root'] + '#programs&id=' + program_id
    print(f'{Fore.WHITE}» {SUCCESS}Created Eloqua Program ID: {program_id}')
    webbrowser.open(url, new=2, autoraise=True)

    return (program_id, program)


'''
=================================================================================
                                User API
=================================================================================
'''


def eloqua_get_user(user_id):
    '''
    Required user id
    Returns user data
    '''
    # Creating a get call to Eloqua API
    root = f'{eloqua_rest}system/user/{user_id}'
    response = api_request(root)
    user = response.json()

    return user


'''
=================================================================================
                                Data API
=================================================================================
'''


def eloqua_get_step_contacts(step_id, count=400, page=1):
    '''
    Requires step_id, and optionally count, pagination
    Returns contacts staying on chosen step
    '''

    # Getting a correct view_id
    view_id = naming[source_country]['id']['view_id']

    # Builds the API request
    payload = {
        'count': count,  # Sets count of outcomes
        'page': page  # Pagination of outcomes
    }

    # Creating a get call to Eloqua API
    root = f'{eloqua_rest}data/contact/view/{view_id}/contacts/campaign/element/{step_id}'
    response = api_request(root, params=payload)
    contacts = response.json()
    if contacts['total'] > count:
        print(f'{Fore.GREEN}|', end='', flush=True)

    return contacts


'''
=================================================================================
                                Image Storage API
=================================================================================
'''


def eloqua_get_images(image_name):
    '''
    Returns url of uploaded image
    '''

    # Gets data of requested image name
    root = f'{eloqua_rest}assets/images'
    params = {'depth': 'complete',
              'orderBy': 'createdAt Desc',
              'search': image_name}
    response = api_request(root, params=params)
    image_info = response.json()

    # Builds image_link
    image_link = image_info['elements'][0]['fullImageUrl']
    image_link = (image_link.split('/'))[-1]
    image_link = naming['image'] + image_link

    # Warns if there are multiple images found by query
    if int(image_info['total']) > 1:
        print(
            f'\n{WARNING}More then one image found - adding newest ', end='')

    return image_link


def eloqua_post_image(image):
    '''
    Returns url of uploaded image
    '''

    def eloqua_move_image(image_id):
        '''
        Moves image to ELQuent image uploads folder
        '''

        # Gets image data to prepare PUT body
        image_data = eloqua_asset_get(
            image_id, asset_type='image', depth='complete')

        # Gets and swaps folder_id to correct one for ELQuent image uploads
        folder_id = naming[source_country]['id']['image']
        image_data['folderId'] = folder_id

        # Updates image folder_id
        root = f'{eloqua_rest}assets/image/{image_id}'
        api_request(root, call='put', data=json.dumps(image_data))

        return

    # Posts image to Eloqua
    root = f'{eloqua_rest}assets/image/content'
    response = api_request(root, call='post', files=image)
    image_info = response.json()

    # Builds image_link
    image_url = image_info['fullImageUrl']
    image_link = naming['image'] + image_url

    # Moves file to correct image folder
    image_id = image_info['id']
    eloqua_move_image(image_id)

    print(f'{Fore.GREEN} › {Fore.WHITE}ELQ', end='', flush=True)

    return image_link


'''
=================================================================================
                                File Storage API
=================================================================================
'''


def eloqua_get_files(file_name):
    '''
    Returns url of uploaded file
    '''

    # Gets data of requested image name
    root = f'{eloqua_rest}assets/importedFiles'
    params = {'depth': 'complete',
              'orderBy': 'createdAt Desc',
              'search': file_name}
    response = api_request(root, params=params)
    file_info = response.json()

    # Gets file_link
    file_link = file_info['elements'][0]['trackedLink']

    # Warns if there are multiple images found by query
    if int(file_info['total']) > 1:
        print(
            f'\n{WARNING}More then one file found - adding newest ', end='')

    return file_link


def eloqua_post_file(imported_file):
    '''
    Returns url of uploaded file
    '''

    def eloqua_move_file(file_id):
        '''
        Moves file to ELQuent file storage uploads folder
        '''

        # Gets image data to prepare PUT body
        file_data = eloqua_asset_get(
            file_id, asset_type='file', depth='complete')

        # Gets and swaps folder_id to correct one for ELQuent image uploads
        folder_id = naming[source_country]['id']['certificate']
        file_data['folderId'] = folder_id

        # Updates image folder_id
        root = f'{eloqua_rest}assets/importedFile/{file_id}'
        api_request(root, call='put', data=json.dumps(file_data))

        return

    # Posts image to Eloqua
    root = f'{eloqua_rest}assets/importedFile/content'
    response = api_request(root, call='post', files=imported_file)
    file_info = response.json()

    # Builds image_link
    file_link = file_info['trackedLink']

    # Shortens the link to Unique elements
    file_lid_regex = re.compile(r'(?<=lid=).*?(?=&elq)')
    file_lids = file_lid_regex.findall(file_link)
    file_lid = file_lids[0]

    # Moves file to correct image folder
    file_id = file_info['id']
    eloqua_move_file(file_id)

    print(f'{Fore.GREEN} › {Fore.WHITE}ELQ', end='', flush=True)

    return file_lid


'''
=================================================================================
                                Shared Content API
=================================================================================
'''


def eloqua_put_sharedcontent(sc_id, data):
    '''
    Requires id and data of the shared content to update SC in Eloqua
    Returns success bool
    '''

    # Creating a put call to Eloqua API
    root = f'{eloqua_rest}assets/contentSection/{sc_id}'
    response = api_request(
        root, call='put', data=json.dumps(data))
    shared_content = response.json()

    # Checks if there is error
    if isinstance(shared_content, list) or shared_content['type'] != 'ContentSection':
        print(f'{Fore.YELLOW}{shared_content}')
        return False

    return True


'''
=================================================================================
                                Field Merge API
=================================================================================
'''


def eloqua_create_fieldmerge(name, data):
    '''
    Requires name and json data of the field merge to create it in Eloqua
    Returns fieldmerge htmlName ('syntax')
    '''
    # Checks if there already is Form with that name
    eloqua_asset_exist(name, asset='fieldMerge')

    # Creating a post call to Eloqua API
    root = f'{eloqua_rest}assets/fieldMerge'
    response = api_request(
        root, call='post', data=json.dumps(data))
    fieldmerge = response.json()

    # Open in new tab
    fieldmerge_htmlname = fieldmerge['syntax']
    print(f'\n{Fore.WHITE}» {SUCCESS}Created Field Merge: {fieldmerge_htmlname}')

    return fieldmerge_htmlname


'''
=================================================================================
                                Data Model API
=================================================================================
'''


def eloqua_get_fields():
    '''
    Returns data model fields {'id':'name'}
    '''
    # Creating a get call to Eloqua API
    root = f'{eloqua_rest}assets/contact/fields'
    response = api_request(root, data=json.dumps(
        {'depth': 'minimal', 'count': 1000}))
    datamodel_json = response.json()

    datamodel = {}
    for field in datamodel_json['elements']:
        datamodel[field['id']] = field['name']

    return datamodel


'''
=================================================================================
                                E-mail Groups API
=================================================================================
'''


def eloqua_get_emailgroups():
    '''
    Returns e-mail groups {'id':'name'}
    '''
    # Creating a get call to Eloqua API
    root = f'{eloqua_rest}assets/email/groups'
    response = api_request(root, data=json.dumps(
        {'depth': 'minimal', 'count': 1000}))
    emailgroups_json = response.json()

    emailgroups = {}
    for field in emailgroups_json['elements']:
        emailgroups[field['id']] = field['name']

    return emailgroups


'''
=================================================================================
                                Contact Upload API
=================================================================================
'''


def upload_contacts(contacts, list_type, choice=''):
    '''
    Contacts argument should be dict with list: {'listName': ['mail', 'mail']}
    Uploads mail list to Eloqua as shared list listName (appends if it already exists)
    '''

    # Creates global shared_list information from json
    global shared_list
    shared_list = naming[source_country]['id']['sharedlist'][list_type]

    # Uploads database to eloqua shared list
    eloqua_create_sharedlist(contacts, choice)

    return
