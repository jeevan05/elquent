#!/usr/bin/env python3.6
# -*- coding: utf8 -*-

'''
ELQuent.admin
ELQuent helpers for central team

Mateusz Dąbrowski
github.com/MateuszDabrowski
linkedin.com/in/mateusz-dabrowski-marketing/
'''

# Python imports
import os
import sys
import csv
import json
from collections import defaultdict
import pyperclip
from colorama import Fore, Style, init

# ELQuent imports
import utils.helper as helper
import utils.modifier as modifier
import utils.api.api as api

# Initialize colorama
init(autoreset=True)

# Globals
naming = None
source_country = None

# Predefined messege elements
ERROR = f'{Fore.WHITE}[{Fore.RED}ERROR{Fore.WHITE}] {Fore.YELLOW}'
SUCCESS = f'{Fore.WHITE}[{Fore.GREEN}SUCCESS{Fore.WHITE}] '
YES = f'{Style.BRIGHT}{Fore.GREEN}y{Fore.WHITE}{Style.NORMAL}'
NO = f'{Style.BRIGHT}{Fore.RED}n{Fore.WHITE}{Style.NORMAL}'


def country_naming_setter(country):
    '''
    Sets source_country for all functions
    Loads json file with naming convention
    '''
    global source_country
    source_country = country

    # Loads json file with naming convention
    with open(file('naming'), 'r', encoding='utf-8') as f:
        global naming
        naming = json.load(f)


'''
=================================================================================
                            File Path Getter
=================================================================================
'''


def file(file_path, name=''):
    '''
    Returns file path to template files
    '''

    def find_data_file(filename, directory='templates'):
        '''
        Returns correct file path for both script and frozen app
        '''
        if directory == 'templates':  # For reading template files
            if getattr(sys, 'frozen', False):
                datadir = os.path.dirname(sys.executable)
            else:
                datadir = os.path.dirname(os.path.dirname(__file__))
            return os.path.join(datadir, 'utils', directory, filename)
        elif directory == 'api':  # For reading api files
            if getattr(sys, 'frozen', False):
                datadir = os.path.dirname(sys.executable)
            else:
                datadir = os.path.dirname(os.path.dirname(__file__))
            return os.path.join(datadir, 'utils', directory, filename)
        elif directory == 'outcomes':  # For writing outcome files
            if getattr(sys, 'frozen', False):
                datadir = os.path.dirname(sys.executable)
            else:
                datadir = os.path.dirname(os.path.dirname(__file__))
            return os.path.join(datadir, directory, filename)

    file_paths = {
        'naming': find_data_file('naming.json', directory='api'),
        'form': find_data_file(f'WKCORP_form-email-group.json'),
        'filter': find_data_file(f'WKCORP_filter-email-group.json'),
        'program-canvas': find_data_file(f'WKCORP_program-canvas.txt'),
        'program-steps': find_data_file(f'WKCORP_program-steps.txt'),
        'program-last-step': find_data_file(f'WKCORP_program-last-step.txt'),
        'email-groups': find_data_file(f'WKCORP_email-groups.json'),
        'outcome-json': find_data_file(f'WK{source_country}_{name}.json', directory='outcomes'),
        'outcome-csv': find_data_file(f'WK{source_country}_{name}.csv', directory='outcomes')
    }

    return file_paths.get(file_path)


'''
=================================================================================
                            Email Groups Program Creator
=================================================================================
'''


def email_groups():
    '''
    Creates shared lists and forms for email group corp program
    '''

    def form_builder(countries, groups):
        '''
        Creates form for each given e-mail group
        '''
        # Prepares informations necessary for proper data in API call
        form_folder_id = countries['FolderID']['Form']

        # Gets form source json
        with open(file('form'), 'r', encoding='utf-8') as f:
            source_form_json = json.load(f)

        # Iterates for each e-mail group to create form for each
        for email_group in groups:
            print(
                f'\n{Fore.WHITE}[{Fore.YELLOW}CREATING{Fore.WHITE}] {email_group[0]} Form:')

            form_name = f'{email_group[0]}-{email_group[1]}_FORM'
            form_html_name = f'{email_group[0]}'

            # Change form json to string for easy replacing
            form_string = json.dumps(source_form_json)
            form_string = form_string\
                .replace('HTML_NAME', form_html_name)\
                .replace('FORM_NAME', form_name)\
                .replace('EMAIL_GROUP', email_group[0])\
                .replace('GROUP_ID', email_group[1])\
                .replace('FOLDER_ID', form_folder_id)

            # Change back to json for API call
            form_json = json.loads(form_string)

            # Creates form with given data
            form_id = api.eloqua_create_form(form_name, form_json)[0]

            # Save to outcome json file
            assets_created[email_group[0]].append([form_name, form_id])

    def sharedfilter_builder(countries, groups):
        '''
        Creates pair of shared filters (sub/unsub) for each given e-mail group
        '''
        # Prepares informations necessary for proper data in API call
        filter_folder_id = countries['FolderID']['SharedFilter']

        # Gets form source json
        with open(file('filter'), 'r', encoding='utf-8') as f:
            source_filter_json = json.load(f)

        # Change form json to string for easy replacing
        filter_string = json.dumps(source_filter_json)

        # Iterates for each e-mail group to create form for each
        for email_group in groups:
            print(
                f'\n{Fore.WHITE}[{Fore.YELLOW}CREATING{Fore.WHITE}] {email_group[0]} Shared Filters (SUB/UNSUB):')

            # ---------------------------------- Creating Subscription Shared Filter
            filter_sub_name = f'WK{source_country}_{email_group[0]}-{email_group[1]}_SUB-FILTER'

            # Swapping shared filter elements
            filter_sub_string = filter_string\
                .replace('FILTER_NAME', filter_sub_name)\
                .replace('GROUP_ID', email_group[1])\
                .replace('FOLDER_ID', filter_folder_id)\
                .replace('SUB_CRITERION', 'SubscriptionCriterion')

            # Change back to json for API call
            filter_sub_json = json.loads(filter_sub_string)

            # Creates form with given data
            filter_id = api.eloqua_create_filter(
                filter_sub_name, filter_sub_json)[0]

            # Save to outcome json file
            assets_created[email_group[0]].append([filter_sub_name, filter_id])

            # ---------------------------------- Creating Unsubscription Shared Filter
            filter_unsub_name = f'WK{source_country}_{email_group[0]}-{email_group[1]}_UNSUB-FILTER'

            # Swapping shared filter elements
            filter_unsub_string = filter_string\
                .replace('FILTER_NAME', filter_unsub_name)\
                .replace('GROUP_ID', email_group[1])\
                .replace('FOLDER_ID', filter_folder_id)\
                .replace('SUB_CRITERION', 'UnsubscriptionCriterion')

            # Change back to json for API call
            filter_unsub_json = json.loads(filter_unsub_string)

            # Creates form with given data
            filter_id = api.eloqua_create_filter(
                filter_unsub_name, filter_unsub_json)[0]

            # Save to outcome json file
            assets_created[email_group[0]].append(
                [filter_unsub_name, filter_id])

    def program_builder(assets_created):
        '''
        Creates program canvas with built assets
        '''
        print(
            f'\n{Fore.WHITE}[{Fore.YELLOW}CREATING{Fore.WHITE}] Program Canvas:')

        # Gets program canvas json
        with open(file('program-canvas'), 'r', encoding='utf-8') as f:
            program_canvas = f.read()
        country = list(assets_created.keys())[0].split('_')
        country = country[0]
        program_name = f'WKCORP_GDPR-Subscription-{country}_PROG'
        program_canvas = program_canvas.replace('PROGRAM_NAME', program_name)

        # Gets program steps json
        with open(file('program-steps'), 'r', encoding='utf-8') as f:
            program_steps = f.read()

        counter = 1
        for group, assets in assets_created.items():
            sub_id = assets[1][1]
            unsub_id = assets[2][1]

            # Check if this is last email group to add
            if counter == len(assets_created.keys()):
                with open(file('program-last-step'), 'r', encoding='utf-8') as f:
                    program_steps = f.read()

            filled_program_steps = program_steps\
                .replace('EMAIL_GROUP', group)\
                .replace('COUNTER_PLUS', str(counter * 150 + 100))\
                .replace('COUNTER', str(counter * 150))\
                .replace('FILTER_SUB_ID', sub_id)\
                .replace('FILTER_UNSUB_ID', unsub_id)

            program_canvas = program_canvas.replace(
                'INSERT_STEPS', filled_program_steps)
            counter += 1

        # Changes back to json for API call
        program_canvas_json = json.loads(program_canvas)

        # Creates program with given data
        program_id = api.eloqua_create_program(
            program_name, program_canvas_json)[0]

        # Save to outcome json file
        assets_created['Program'].append([program_name, program_id])

    # Loads json file with email groups
    with open(file('email-groups'), 'r', encoding='utf-8') as f:
        countries = json.load(f)
    countries_list = list(countries.keys())[1:]

    # Prints countires available in json file
    print(f'\n{Fore.GREEN}Countries available in json:')
    for i, country_option in enumerate(countries_list):
        print(
            f'{Fore.WHITE}[{Fore.YELLOW}{i}{Fore.WHITE}]\t» [{Fore.YELLOW}{country_option}{Fore.WHITE}]')
    print(
        f'{Fore.WHITE}[{Fore.YELLOW}Q{Fore.WHITE}]\t» [{Fore.YELLOW}Quit{Fore.WHITE}]')

    # Allows user to choose which country assets he wants to generate
    while True:
        print(
            f'{Fore.YELLOW}Enter number associated with chosen country:', end='')
        choice = input(' ')
        if choice.lower() == 'q':
            print(f'\n{Fore.GREEN}Ahoj!')
            raise SystemExit
        try:
            choice = int(choice)
        except (TypeError, ValueError):
            print(f'{Fore.RED}Please enter numeric value!')
            choice = ''
            continue
        if 0 <= choice < len(source_country):
            break
        else:
            print(f'{Fore.RED}Entered value does not belong to any country!')
            choice = ''

    # Modifies chosen country to a list of tuples
    groups = countries.get(countries_list[choice])
    groups = list(groups.items())

    # Creates forms and shared filters
    assets_created = defaultdict(list)
    form_builder(countries, groups)
    sharedfilter_builder(countries, groups)
    program_builder(assets_created)

    with open(file('outcome-json', name='GDPR-Email-Group-Assets'), 'w', encoding='utf-8') as f:
        json.dump(assets_created, f)

    print(
        f'\n{Fore.WHITE}[{Fore.GREEN}FINISHED{Fore.WHITE}] List of created assets saved to Outcomes folder')

    # Asks user if he would like to repeat
    print(f'\n{Fore.YELLOW}» {Fore.WHITE}Do you want to create another batch? {Fore.WHITE}({YES}/{NO}):', end=' ')
    choice = input(' ')
    if choice.lower() == 'y':
        email_groups()

    return


'''
=================================================================================
                                Form Processing Reporter
=================================================================================
'''


def form_data():
    '''
    Gets data on form processing steps related to GCR via API
    '''

    def append_form_fields(field):
        '''
        Takes selected field data and append it to form_fields list of dicts
        '''
        field_id = field.get('id')
        field_name = field.get('name')
        field_html_name = field.get('htmlName')
        field_email_group = field.get('emailGroupId')
        field_merge_id = field.get('fieldMergeId')
        field_option_list_id = field.get('optionListId')
        field_global_subscription = field.get(
            'useGlobalSubscriptionStatus')
        form_fields.append({
            'id': field_id,
            'name': field_name,
            'htmlName': field_html_name,
            'fieldMergeId': field_merge_id,
            'optionListId': field_option_list_id,
            'emailGroup': field_email_group,
            'globalSubscription': field_global_subscription
        })

        return

    # Get query string from the user
    print(f'\n{Fore.YELLOW}»{Fore.WHITE} Write or copypaste search {Fore.YELLOW}query string',
          f'{Fore.WHITE}and click [Enter]')
    search_query = input(' ')
    if not search_query:
        search_query = pyperclip.paste()
        if not search_query:
            search_query = '*'
    print(f'\n{Fore.WHITE}[{Fore.YELLOW}SYNC{Fore.WHITE}] ', end='')

    # Get json of all froms based on query
    page = 1
    count = 50
    forms = []
    while True:
        # Gets full data on first part of assets connected with campaign
        assets_partial = api.eloqua_get_assets(
            search_query, 'form', count=count, page=page)

        # Add existing to a list
        for single_asset in assets_partial['elements']:
            forms.append(single_asset)

        # Stops iteration when full list is obtained
        if assets_partial['total'] - page * count < 0:
            break

        # Else increments page to get next part of outcomes
        page += 1

        # Every ten batches draws hyphen for better readability
        if page % 10 == 0:
            print(f'{Fore.YELLOW}-', end='', flush=True)

    # Create dict with selected data from the forms
    forms_dict = {}  # Dict with structure {formID:formData}
    source_country_trigger_list = naming['sourceCountrySharedUpdate']
    contact_update_trigger_list = naming['contactDataSharedUpdate']
    for form in forms:
        form_id = form.get('id')
        form_name = form.get('name')
        form_html_name = form.get('htmlName')
        form_creation_date = helper.epoch_to_date(form.get('createdAt'))
        form_fields = []
        for field in form['elements']:
            if field['type'] in ['FormFieldGroup', 'ProgressiveProfile']:
                if field.get('fields'):
                    for subfield in field['fields']:
                        if subfield['displayType'] == 'checkbox':
                            append_form_fields(subfield)
                elif field.get('stages'):
                    for stage in field['stages']:
                        for subfield in stage['fields']:
                            if subfield['displayType'] == 'checkbox':
                                append_form_fields(subfield)
            elif field['displayType'] == 'checkbox':
                append_form_fields(field)
        form_processing_steps = []
        source_country_trigger = []
        contact_update_trigger = []
        for processing_step in form['processingSteps']:
            # Catch shared update rule processing steps
            if processing_step['type'] == 'FormStepCreateUpdateContact':
                try:
                    if processing_step['sharedContactUpdateRuleSet']['id'] in source_country_trigger_list:
                        source_country_trigger.append(
                            processing_step['sharedContactUpdateRuleSet']['name'])
                    elif processing_step['sharedContactUpdateRuleSet']['id'] in contact_update_trigger_list:
                        contact_update_trigger.append(True)
                except KeyError:
                    source_country_trigger.append(False)
                    contact_update_trigger.append(False)
            # Catch subscription based processing steps
            if processing_step['type'] in [
                    'FormStepGroupSubscription',
                    'FormStepGlobalUnsubscribe',
                    'FormStepGlobalSubscribe'
            ]:
                step_type = processing_step.get('type')
                step_execute = processing_step.get('execute')
                try:
                    if step_execute == 'conditional':
                        step_condition = processing_step.get('condition')
                    else:
                        step_condition = ''
                except KeyError:
                    step_condition = ''
                try:
                    step_email_group = [
                        processing_step['emailGroupId']['valueType'],
                        processing_step['emailGroupId']['formFieldId']
                    ]
                except KeyError:
                    step_email_group = ''
                try:
                    step_subscription = [
                        processing_step['isSubscribing']['valueType'],
                        processing_step['isSubscribing']['formFieldId']
                    ]
                except KeyError:
                    step_subscription = ''

                form_processing_steps.append({
                    'type': step_type,
                    'execute': step_execute,
                    'condition': step_condition,
                    'emailGroup': step_email_group,
                    'isSubscribing': step_subscription
                })
            else:
                continue

        source_country_trigger = [e for e in source_country_trigger if e]
        if not source_country_trigger:
            source_country_trigger = False
        contact_update_trigger = True if contact_update_trigger else False

        forms_dict[form_id] = {
            'id': form_id,
            'name': form_name,
            'creationDate': form_creation_date,
            'htmlName': form_html_name,
            'formFields': form_fields,
            'formProcessingSteps': form_processing_steps,
            'sharedSourceCountryUpdate': source_country_trigger,
            'sharedContactUpdateTrigger': contact_update_trigger
        }

    with open(file('outcome-json', name=f'FormProcessing-{search_query}'), 'w', encoding='utf-8') as f:
        json.dump(forms_dict, f)

    print(
        f'\n{Fore.WHITE}[{Fore.GREEN}FINISHED{Fore.WHITE}] JSON of {len(forms_dict.keys())}',
        f'{Fore.YELLOW}{search_query}{Fore.WHITE} forms saved to Outcomes folder')

    # Create list of completed campaigns
    if 'WKPL' in search_query:
        modifier.country_naming_setter(source_country)
        completed_campaigns = modifier.get_completed_campaigns(
            redirected_campaigns=[])
        completed_campaigns_string = str(completed_campaigns)
        print()

    # Create list of forms that need a fix
    no_shared_source_country_update = [('ID', 'Name')]
    no_shared_contact_update_trigger = [('ID', 'Name')]
    for form in forms_dict:
        if not forms_dict[form]['sharedSourceCountryUpdate']:
            no_shared_source_country_update.append(
                (forms_dict[form]['id'], forms_dict[form]['name']))
        if not forms_dict[form]['sharedContactUpdateTrigger']:
            no_shared_contact_update_trigger.append(
                (forms_dict[form]['id'], forms_dict[form]['name']))
    print(f'\n{Fore.YELLOW}» {Fore.WHITE}Found:')
    print(f'{Fore.WHITE} › {Fore.YELLOW}{len(no_shared_source_country_update) - 1}'
          f'{Fore.WHITE} forms without {Fore.YELLOW}shared Source Country Update Rule', end=' ')
    if 'WKPL' in search_query:
        uncompleted_source_country_errors = [('ID', 'Name')]
        for form in no_shared_source_country_update[1:]:
            form_base = ('_').join((form[1].split('_'))[0:4])
            if form_base not in completed_campaigns_string:
                uncompleted_source_country_errors.append(form)
        print(
            f'{Fore.WHITE}({Fore.YELLOW}{len(uncompleted_source_country_errors) - 1}'
            f'{Fore.WHITE} in live campaigns)')
    else:
        print()
    print(f'{Fore.WHITE} › {Fore.YELLOW}{len(no_shared_contact_update_trigger) - 1}'
          f'{Fore.WHITE} forms without {Fore.YELLOW}shared Contact Update Trigger Date', end=' ')
    if 'WKPL' in search_query:
        uncompleted_contact_update_errors = [('ID', 'Name')]
        for form in no_shared_contact_update_trigger[1:]:
            form_base = ('_').join((form[1].split('_'))[0:4])
            if form_base not in completed_campaigns_string:
                uncompleted_contact_update_errors.append(form)
        print(
            f'{Fore.WHITE}({Fore.YELLOW}{len(uncompleted_contact_update_errors) - 1}'
            f'{Fore.WHITE} in live campaigns)')
    else:
        print()
    print(f'{Fore.YELLOW}» {Fore.WHITE}IDs saved to Outcomes folder')
    with open(file('outcome-csv', name=f'FormProcessing-{search_query}-no-source-country-update'), 'w', encoding='utf-8') as f1:
        writer = csv.writer(f1)
        writer.writerows(no_shared_source_country_update)
    with open(file('outcome-csv', name=f'FormProcessing-{search_query}-no-contact-update'), 'w', encoding='utf-8') as f2:
        writer = csv.writer(f2)
        writer.writerows(no_shared_contact_update_trigger)
    if 'WKPL' in search_query:
        with open(file('outcome-csv', name=f'FormProcessing-{search_query}-live-no-source-country-update'), 'w', encoding='utf-8') as f3:
            writer = csv.writer(f3)
            writer.writerows(uncompleted_source_country_errors)
        with open(file('outcome-csv', name=f'FormProcessing-{search_query}-live-no-contact-update'), 'w', encoding='utf-8') as f4:
            writer = csv.writer(f4)
            writer.writerows(uncompleted_contact_update_errors)

        # Asks user if he would like to repeat
    print(f'\n{Fore.YELLOW}» {Fore.WHITE}Do you want to create another batch? {Fore.WHITE}({YES}/{NO}):', end=' ')
    choice = input(' ')
    if choice.lower() == 'y':
        form_data()

    return


'''
=================================================================================
                                Admin module menu
=================================================================================
'''


def admin_module(country):
    '''
    Lets user choose which link module utility he wants to use
    '''
    # Create global source_country and load json file with naming convention
    country_naming_setter(country)

    print(
        f'\n{Fore.GREEN}ELQuent.link Utilites:'
        f'\n{Fore.WHITE}[{Fore.YELLOW}1{Fore.WHITE}]\t» [{Fore.YELLOW}EmailGroups{Fore.WHITE}] Create e-mail group program canvas related to GCR'
        f'\n{Fore.WHITE}[{Fore.YELLOW}2{Fore.WHITE}]\t» [{Fore.YELLOW}FormProcessing{Fore.WHITE}] Get data on form processing steps related to GCR'
        f'\n{Fore.WHITE}[{Fore.YELLOW}Q{Fore.WHITE}]\t» [{Fore.YELLOW}Quit to main menu{Fore.WHITE}]'
    )
    while True:
        print(f'{Fore.YELLOW}Enter number associated with chosen utility:', end='')
        choice = input(' ')
        if choice.lower() == 'q':
            break
        elif choice == '1':
            email_groups()
            break
        elif choice == '2':
            form_data()
            break
        else:
            print(f'{Fore.RED}Entered value does not belong to any utility!')
            choice = ''

    return
