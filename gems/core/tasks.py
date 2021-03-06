from __future__ import absolute_import
from celery import task
from gems.core.models import SurveyResult, ExportTypeMapping, Survey, TaskLogger
from django.conf import settings
from django.db import connection
from django.core.mail import EmailMessage
import logging
import json
from pygments.lexers.lisp import EmacsLispLexer
import requests
from go_http.contacts import ContactsApiClient
from go_http.metrics import MetricsApiClient
from go_http.account import AccountApiClient
from go_http.send import HttpApiSender
from gems.core.models import Contact, ContactGroupMember, SentMessage
from gems.core.viewhelpers import get_surveyresult_hstore_keys
from gems.core.viewhelpers import process_group_member, remove_group_member
from datetime import datetime, timedelta
from gems.core.viewhelpers import default_survey_name
from gems.core.csv_utils import process_file

logger = logging.getLogger(__name__)


def perform_casting(name, value):
    result = ExportTypeMapping.objects.filter(field__exact=name).first()

    if result:

        if result.cast == 1:
            # cast to int
            try:
                return int(value)
            except:
                pass

        elif result.cast == 2:
            # cast to float
            try:
                return float(value)
            except:
                pass

    return value


def process_results(result_set):
    results = []

    for sr in result_set:
        result = {
            'keys': ['id'],
            'id': sr.id,
            'survey': sr.survey.name,
            'contact': sr.contact.vkey,
            'created_at': sr.created_at.isoformat(),
            'updated_at': sr.updated_at.isoformat()
        }

        for key in sr.answer.keys():
            result[key] = perform_casting(name=key, value=sr.answer[key])

        results.append(result)

    return results


def fetch_results():
    try:
        raw_results = SurveyResult.objects.select_related().filter(sent=False)[:100]
    except Exception as ex:
        logger.error('export_data[Task]->fetch_results->DB failed: %s' % ex)
        raise

    try:
        processed_results = process_results(raw_results)
    except Exception as ex:
        logger.error('export_data[Task]->fetch_results->process failed: %s' % ex)
        raise

    return processed_results, raw_results.values('id')


def submit_results(sendable_results, raw_results):

    payload = json.dumps(sendable_results)

    url = settings.RJ_METRICS_URL + \
        settings.RJ_METRICS_CID + \
        '/table/' + \
        settings.RJ_METRICS_TABLE + \
        '/data'
    headers = {'Content-Type': 'application/json'}
    params = {'apikey': settings.RJ_METRICS_API_KEY}

    result = requests.post(
        url,
        headers=headers,
        params=params,
        data=payload
    )

    if result.status_code == 201:
        try:
            update_results(raw_results)
        except Exception as ex:
            logger.error(
                'export_data[Task]->submit_results->update_results failed: %s' % ex
            )
            raise
    else:
        logger.error(
            'export_data[Task]->submit_results failed: message: %s'
            % result.content
        )
        if result.status_code != 200:
            result.raise_for_status()


def update_results(results):
    SurveyResult.objects.filter(pk__in=results).update(sent=True)


@task(bind=True)
def export_data(self):

    logger.info('export_data[Task] :: Started')

    try:
        while True:
            pr, rr = fetch_results()

            # exit loop when all the rows have been submitted
            if len(rr) == 0:
                break

            submit_results(pr, rr)

    except Exception as ex:
        logger.error('export_data[Task] failed: %s' % ex)

    logger.info('export_data[Task] :: Completed')


@task(bind=True)
def import_contacts(self):
    task_name = 'import_contacts'
    msg = 'Importing contacts :: STARTED'
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)

    api = ContactsApiClient(settings.VUMI_TOKEN)

    all_contacts = list()
    try:
        TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
        for contact in api.contacts():
            all_contacts.append(contact)
    except Exception as e:
        msg = 'importing contacts :: Failed to fetch contacts. %s' % e
        TaskLogger.objects.create(task_name=task_name, success=False, message=msg)
        logger.exception(msg)

    count = 0
    for item in all_contacts:
        if 'msisdn' in item:
            try:
                contact, created = Contact.objects.get_or_create(msisdn=item['msisdn'])
                if not created:
                    continue
                contact.vkey = item['key']
                contact.save()
                count += 1
            except Exception as e:
                msg = 'creating contact :: Failed to create a contact %s. %s' % (item['msisdn'], e)
                TaskLogger.objects.create(task_name=task_name, success=False, message=msg)
                logger.exception(msg)
        else:
            msg = 'Contact does not contain msisdn. vkey: %s' % item['vkey']
            TaskLogger.objects.create(task_name=task_name, success=False, message=msg)
            logger.info(msg)

    msg = '%s contacts imported' % count
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)
    msg = 'Importing contacts :: COMPLETED'
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)


@task
def construct_dashboard_survey_results_table():
    construct_summary_table_sql()


def construct_summary_table_sql():
    keys = get_surveyresult_hstore_keys(False)
    key_columns = ''

    for key in keys:
        if len(key_columns) > 0:
            key_columns += ', '

        key_columns += "answer->'%s' \"%s\"" % (key, key)

    sql = '''
    select s.survey_id, s.name "survey_name", s.series, s.created_on "survey_created_on",
      c.vkey "contact_vkey", %s, sr.created_at "result_created_on"
    into gems_reporting.dashboard_survey_results
    from core_surveyresult sr
      inner join core_survey s
        on s.survey_id = sr.survey_id
      inner join core_contact c
        on c.msisdn = sr.contact_id
    ''' % key_columns

    cursor = connection.cursor()

    cursor.execute('drop table if exists gems_reporting.dashboard_survey_results')
    cursor.execute(sql)


@task
def add_members_to_group(api, group, members):
    task_name = 'add_members_to_group'
    msg = 'Adding members to %s group :: STARTED' % group.name
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)
    for member in members:
        try:
            contact = Contact.objects.get(msisdn=member['value'])
        except Contact.DoesNotExist:
            msg = 'Contact with msisdn %s does not exist' % member['value']
            TaskLogger.objects.create(task_name=task_name, success=False, message=msg)
            logger.info(msg)
            continue
        process_group_member(api, contact, group)
    msg = 'Adding members to %s group :: COMPLETED' % group.name
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)


@task
def add_new_members_to_group(api, group, members):
    task_name = 'add_new_members_to_group'
    msg = 'Adding members to %s group :: STARTED' % group.name
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)
    for member in members:
        process_group_member(api, member, group)
    msg = 'Adding members to %s group :: COMPLETED' % group.name
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)


@task
def remove_members_from_group(api, group, members):
    task_name = 'remove_members_from_group'
    msg = 'Removing members from %s group :: STARTED' % group.name
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)
    for member in members:
        remove_group_member(api, member, group)
    msg = 'Removing members from %s group :: COMPLETED' % group.name
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    logger.info(msg)


@task(bind=True)
def sync_group_members(self):
    task_name = 'sync_group_members'
    msg = 'Syncing group members :: STARTED'
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
    unsynced_members = ContactGroupMember.objects.filter(synced=False)
    api = ContactsApiClient(settings.VUMI_TOKEN)
    for member in unsynced_members:
        process_group_member(api, member.contact, member.group)
    msg = 'Syncing group members :: COMPLETED'
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)


def date_construct_helper(today, delta):
    t = today

    if delta is not None:
        t = today - delta

    t = t.replace(hour=0, minute=0, second=0, microsecond=0)
    return t


@task
def fetch_total_sent_smses():
    logger.info('Fetching TOTAL SENT SMSES::STARTED')
    api = MetricsApiClient(settings.VUMI_TOKEN)
    surveys = Survey.objects.values('survey_id').distinct()
    totals = [0, 0, 0, 0, 0, 0, 0]
    today = datetime.now()
    total_dates = [
        date_construct_helper(today, timedelta(days=6)),
        date_construct_helper(today, timedelta(days=5)),
        date_construct_helper(today, timedelta(days=4)),
        date_construct_helper(today, timedelta(days=3)),
        date_construct_helper(today, timedelta(days=2)),
        date_construct_helper(today, timedelta(days=1)),
        date_construct_helper(today, None)
    ]

    for survey in surveys:
        metric = 'conversations.' + survey['survey_id'] + '.outbound_unique_addresses.avg'
        logger.info('Fetching metric: ' + metric + ' for channel: ' + survey['survey_id'])

        try:
            results = api.get_metric(metric=metric, start='-7d', interval='1d', nulls='omit')

            if metric in results:
                for result in results[metric]:
                    d = datetime.fromtimestamp(result['x']/1000)
                    v = result['y']

                    if d in total_dates:
                        totals[total_dates.index(d)] = v

        except Exception as e:
            print('Fetching metric failed. Reason: ', e)
            logger.error('Fetching metric failed. Reason: ', e)

    logger.info('Results')

    for index, v in enumerate(totals):
        d = total_dates[index]
        logger.info('Result: %s : %s' % (d, v))

        try:
            msg, created = SentMessage.objects.get_or_create(created_at=d, defaults={'total': v})
            msg.total = v
            msg.save()
        except Exception as e:
            logger.error('Saving result failed. Reason: ', e)

    logger.info('Fetching TOTAL SENT SMSES::COMPLETED')


@task
def fetch_survey_names_task():
    fetch_survey_names()


def fetch_survey_names():
    task_name = 'fetch_survey_name'
    msg = 'Fetching Survey Names::STARTED'
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)

    # fetch all the surveys that need names
    surveys = Survey.objects.filter(name=default_survey_name)

    if surveys.count() > 0:
        conversations = []

        try:
            msg = 'Fetching Survey Names::Fetching vumi conversations - Start'
            TaskLogger.objects.create(task_name=task_name, success=True, message=msg)

            # if we have any fetch all the conversations from vumi
            api = AccountApiClient(settings.VUMI_TOKEN)
            conversations = api.conversations(settings.VUMI_ACCOUNT_KEY)

            msg = 'Fetching Survey Names::Fetching vumi conversations - Done'
            TaskLogger.objects.create(task_name=task_name, success=True, message=msg)
        except Exception as e:
            msg = 'Fetching Survey Names::Fetching vumi conversations - Failed. Reason: ', e
            TaskLogger.objects.create(task_name=task_name, success=False, message=msg)

        for c in conversations:
            for s in surveys:
                if 'uuid' in c and s.survey_id == c['uuid']:
                    try:
                        msg = 'Fetching Survey Names::Setting %s to %s' % (s.survey_id, c['name'])
                        TaskLogger.objects.create(task_name=task_name, success=True, message=msg)

                        s.name = c['name']
                        s.save()
                    except Exception as e:
                        msg = 'Fetching Survey Names::Setting %s to %s failed. Reason: %s' % \
                              (s.survey_id, c['name'], e)
                        TaskLogger.objects.create(task_name=task_name, success=False, message=msg)

    msg = 'Fetching Survey Names::COMPLETED'
    TaskLogger.objects.create(task_name=task_name, success=True, message=msg)


@task
def mail_csv_import_results(email_address, filename, f=None):
    task_name = 'mail_csv_import_results'
    
    logmsg = 'mail_csv_import_results - importing file '
    TaskLogger.objects.create(task_name=task_name, success=True, message=logmsg)
 
    errors, i = process_file(filename, f=f)
    subject = 'GEMS CSV import '
    msg = 'Rows processed: %i \n' % i
    
    if len(errors) > 0:
        subject += 'failed'
        msg += 'Errors occurred during import of %s. \n' % filename
        msg += ' \n'.join(['Row: %d - %s' % (entry["row"], entry["error"]) for entry in errors])
    else:
        subject += 'successful'
        msg += 'GEMS CSV import successful. \n'

    logmsg = 'mail_csv_import_results - email message: ' + msg
    TaskLogger.objects.create(task_name=task_name, success=True, message=logmsg)

    email = EmailMessage(
        subject=subject,
        body=msg,
        from_email='',
        to=(email_address,)
    )

    try:
        email.send()
        logmsg = 'mail_csv_import_results - sending email completed'
        TaskLogger.objects.create(task_name=task_name, success=True, message=logmsg) 
    except Exception as e:
        logmsg = 'mail_csv_import_results - sending email failed: ', e
        TaskLogger.objects.create(task_name=task_name, success=False, message=logmsg) 
