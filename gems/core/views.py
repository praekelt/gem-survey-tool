from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.base import TemplateView
from django.core import serializers
from django.db import connection
from models import *
import json
import djqscsv
#
from django.shortcuts import render
from go_http.contacts import ContactsApiClient

#token for vumi authentication
VUMI_TOKEN = '996CA00F-6184-4734-B28F-0A56FD8367A3'

def user_login(request):
    # Like before, obtain the context for the user's request.
    context = RequestContext(request)

    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        username = request.POST['username']
        password = request.POST['password']

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your GEM account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Invalid login details supplied.")

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render_to_response('login.html', {}, context)


class ContactGroupsView(TemplateView):

    template_name = "contact-groups.html"

    def get_context_data(self, **kwargs):
        context = super(ContactGroupsView, self).get_context_data(**kwargs)

        contactgroups = ContactGroup.objects.all()
        context['contactgroups'] = contactgroups

        return context


class CreateContactGroupsView(TemplateView):

    template_name = "createcontactgroup.html"

    def get_context_data(self, **kwargs):
        context = super(CreateContactGroupsView, self).get_context_data(**kwargs)

        contactgroups = ContactGroup.objects.all()
        context['contactgroups'] = contactgroups

        return context


def save_data(request):

    if(request.method == 'POST'):
        data=json.loads(request.body)
        answers = None
        contact_msisdn = None
        conversation_key = None

        if data.has_key('user'):
            user = data['user']
            if user.has_key('answers'):
                answers = user["answers"]
        if data.has_key('contact'):
            contact = data['contact']
            if contact.has_key('msisdn'):
                contact_msisdn = contact['msisdn']
        if data.has_key('conversation_key'):
            conversation_key = data['conversation_key']

        # we have data
        if answers and contact_msisdn and conversation_key:
            try:
                # fetch/create the survey
                # fix this
                survey = Survey.objects.get_or_create(survey_id=conversation_key, defaults={'survey_id': conversation_key, 'name': 'New Survey - Please update name in Admin console'})
                survey.save()
                # add the contact
                contact = Contact.objects.get_or_create(msisdn=contact_msisdn)
                contact.save()
                # add the survey result
                survey_result = SurveyResult.objects.create();
                survey_result.survey_id = survey.survey_id
                survey_result.contact = contact
                survey_result.answer = answers
                survey.save()
            except:
                return HttpResponse('FAILED')
            else:
                return HttpResponse('OK')
    else:
        return HttpResponse('FAILED')


def export(request, pk):
    qs = SurveyResult.objects.filter(pk=pk)
    return djqscsv.render_to_csv_response(qs)

class UIField:
    def __init__(self, name, type):
        self.name = name
        self.type = type


class UIFieldEncoder(json.JSONEncoder):
    def default(self, obj):
        """
        :type obj: UIField
        """
        if isinstance(obj, UIField):
            return [obj.name, obj.type]
        return json.JSONEncoder.default(self, obj)


def get_exclusion_list():
    """
    Function that returns a list of fields to be excluded from the results
    :rtype : Tuple
    :return: a list of fields to be excluded from the results
    """
    return ('id', 'answer')


def get_surveyresult_meta_keys():
    """
    :rtype: List of UIField objects
    :return: Set of keys from the surveyresult meta
    """
    excluded_fields = get_exclusion_list()
    field_keys = []

    for field in sorted(SurveyResult._meta.concrete_fields + SurveyResult._meta.many_to_many + SurveyResult._meta.virtual_fields):
        if field.name not in  excluded_fields:
            field_keys.append(UIField(field.name, 'N'))

    return field_keys


def serialize_list_to_json(data, encoder):
    """
    Serialize data to a json string
    :param data: List of objects to serialize
    :param encoder: The encoder to use for the type
    :rtype: string
    :return: data serialized as a json string
    """
    #return json.dumps([x.__dict__ for x in data])
    return json.dumps(data, cls=encoder)


def query(request):
    """

    :param request:
    :return:
    """

    # TODO: Build query here
    results = SurveyResult.objects.all()

    return generate_json_response(serializers.serialize('json', list(results), fields=('survey', 'contact', 'created_at', 'updated_at', 'answer')))


def get_surveyresult_hstore_keys():
    """
    :rtype: List of UIField objects
    :return: Unique set of keys from the answer hstore field in the surveyresult table
    """
    sql = 'select distinct hKey from (select skeys(answer) as hKey from core_surveyresult) as dt'
    cursor = connection.cursor()
    answer_keys = []

    cursor.execute(sql)

    for answer_key in cursor.fetchall():
        answer_keys.append(UIField(answer_key, 'H'))

    return answer_keys


def generate_json_response(content):
    """
    :param content: JSON content for the response body
    :rtype: HttpResponse
    :return: Returns a JSON response
    """
    response = HttpResponse(content,content_type='application/json')
    response['Content-Length'] = len(content)

    return response


def get_unique_keys(request):
    """
    Function returns a unique set of fields from the meta and the hstore
    :rtype: HttpResponse
    :return: HttpResponse with json payload
    """
    answer_keys = get_surveyresult_hstore_keys()
    field_keys = get_surveyresult_meta_keys()
    keys = sorted(answer_keys + field_keys, key=lambda f: f.name)

    return generate_json_response(serialize_list_to_json(keys, UIFieldEncoder))

#for testing menu.html in home.html
def view_home(request):
    return render(request, 'home.html')

def get_contact_groups(request):
    return HttpResponse("hello")
    #contact_groups = ContactGroup.objects.all()
    #data = serializers.serialize("json", contact_groups)
    #return HttpResponse(json.dump(data), content_type="application/json")

def load_contact_groups(request):
    return render(request, 'contact-groups.html')

def delete_group_contact(request):
    if(request.method == 'POST'):
        data=json.loads(request.body)
        group_id = None

        if data.has_key('group_id'):
             group_id = data['group_id']

        ContactGroup.objects.filter(group_id=group_id).delete()

        key = 'f578cbcb16bc4171a7ccc50d250dca96'
        api = ContactsApiClient(VUMI_TOKEN)
        api.delete_group(key)

        return HttpResponse('OK')
    else:
        return HttpResponse('FAILED')

def create_groupcontact(request):
    if request.method == 'POST':
        data=json.loads(request.body)

        if data.has_key('group_name'):
            group_data = {u'name': data['group_name'],}

        api = ContactsApiClient(VUMI_TOKEN)
        group = api.create_group(group_data)
        return HttpResponse(group[u'key'])
    else:
        return HttpResponse("Failed to create group.")

def update_groupcontact(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        if data.has_key('group_key'):
            group_key = {u'key': data['group_key'],}

        if data.has_key('group_name'):
            group_name = {u'name': data['group_name'],}

        api = ContactsApiClient(VUMI_TOKEN)
        api.update_group(group_key, group_name)



def create_contact(request):
    if request.method == 'POST':
        data=json.loads(request._body)

        if data.has_key(''):
            data =  0

        api = ContactsApiClient(VUMI_TOKEN)
        api.create_contact()
        return HttpResponse()
    else:
        return HttpResponse()

def update_contact(request):
    api = ContactsApiClient(VUMI_TOKEN)
    api.update_contact()
    return HttpResponse()

def delete_contact(request):

    api = ContactsApiClient(VUMI_TOKEN)
    api.delete_contact()
    return HttpResponse()