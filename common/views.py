# -*- coding: utf-8 -*-

import urllib
import requests
import json
from django.urls import reverse
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from candidates.models import *
from companies.models import *
from TRM.settings import PROJECT_NAME, SITE_URL
from django.contrib import messages
from django.contrib.auth import login
from common.models import User, AccountVerification, Profile, Gender, send_email_to_TRM, SocialAuth
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from common import registration_settings
from common.forms import ChangeEmailForm, ContactForm, RegisterEmailForm
from common.models import EmailVerification
from datetime import datetime
from payments.models import Subscription, PriceSlab
from TRM.context_processors import subdomain
from activities.utils import post_notification
from TRM import settings
try:
    from requests_oauthlib import OAuth1
except ImportError:  # social posting is disabled
    OAuth1 = None
from utils import is_ajax

"""
View functions for the common app.

This module provides view functions and classes for:
- User registration and activation
- Social authentication
- Profile management
- Email management
- Password management
- Contact form handling
- Social media integration

Most views require authentication unless explicitly noted.
"""


# ------------------- #
# Start Registration #
# ------------------- #
def save_candidate_social_data(backend, user, response, *args, **kwargs):
    """
    Save additional candidate data from social authentication.
    
    Called after successful social authentication to store additional
    profile information from the social platform.
    
    Args:
        backend: Social auth backend instance
        user: User instance
        response: Social platform's response data
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments
    """
    # Register candidate and profile when entering with Facebook or Google
    # print backend.name
    # print response
    user = User.objects.get(pk=user.id)
    try:
        candidate = Candidate.objects.get(user_id=user.pk)
        if not candidate.first_name and not candidate.last_name:
            candidate.first_name = user.first_name
            candidate.last_name = user.last_name
            candidate.save()
        pass
    except:
        try:
            gender = Gender.objects.get(codename__iexact=str(response.get('gender', '')))
        except:
            gender = None
        candidate = Candidate.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            gender = gender,
        )
        user.profile = Profile.objects.get(codename__exact='candidate')
        if backend.name == 'facebook':
            user.logued_by = 'FB'
        elif backend.name == 'google-oauth2':
            user.logued_by = 'GO'
        user.save()
        try:
            # Notification of New Registration
            date = datetime.strftime(datetime.now(), '%d-%m-%Y %I:%M:%S %p')
            body_email = 'User: %s<br><br>Candidate: %s<br><br>Date: %s' % (candidate.user, candidate.user.get_full_name(), date)
            send_email_to_TRM(subject='New Candidate Registration', body_email=body_email)
        except:
            pass


def registration_activate(request, activation_key):
    """
    Activate a user account using the provided activation key.
    
    Args:
        request: HttpRequest object
        activation_key: String key for account activation
        
    Returns:
        HttpResponse: Activation success/failure page
    """
    activation_key = activation_key.lower()
    account = AccountVerification.objects.activate_user(activation_key)

    if account:
        account.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, account)
        # print account
        user_profile = account.profile.codename
        # print user_profile
        if user_profile == 'candidate':
            try:
                # Notification
                candidate = Candidate.objects.get(user=account)
                date = datetime.strftime(datetime.now(), '%d-%m-%Y %I:%M:%S %p')
                body_email = 'User: %s<br><br>Candidate: %s<br><br>Date: %s' % (candidate.user, candidate.user.get_full_name(), date)
                send_email_to_TRM(subject='New Candidate Registration', body_email=body_email)
            except:
                pass

            messages.success(request, _(u'Welcome to %s. We have successfully activated your account. The next step is to complete your Profile.'%PROJECT_NAME))
            post_notification(user = request.user,action = "Welcome to SpotAxis!")
            return redirect('candidates_edit_curriculum')
        elif user_profile == 'recruiter':
            try:
                # Notifications
                company = Company.objects.select_related('user').get(user_id=account)

                #Inform company of the recommendation
                # try:
                #     recommendation =  Recommendations.objects.select_related('to_company').get(from_company=company)
                #     recommendation.status = Recommendation_Status.objects.get(codename__iexact='inactive')
                #     recommendation.save()
                #     context_email = {
                #         'user': company.user,
                #         'company': company.name,
                #         'companies_company_recommendations': True,
                #     }
                #     subject_template_name='mails/company_recommendation_subject.html',
                #     email_template_name='mails/company_recommendation_email.html',
                #     send_TRM_email(subject_template_name=subject_template_name, email_template_name=email_template_name, context_email=context_email, to_user=recommendation.to_company.user.email)
                # except Exception, err:
                #     print(traceback.format_exc())
                #     pass

                # Notification
                date = datetime.strftime(datetime.now(), '%d-%m-%Y %I:%M:%S %p')
                body_email = 'User: %s<br><br>Company: %s<br><br>Date: %s' % (company.user, company.name, date)
                send_email_to_TRM(subject='New Company Registration', body_email=body_email)
            except:
                pass

            messages.success(request, _(u'Welcome to %s. We have successfully activated your account.' % PROJECT_NAME))
            return redirect('companies_record_company')
        else:
            raise Http404

    return render(request, 'new_registration_messages.html')


def registration_complete(request, template_name=None):
    """
    Display registration completion page.
    
    Args:
        request: HttpRequest object
        template_name: Optional template to use
        
    Returns:
        HttpResponse: Registration completion page
    """
    # raise ValueError(request.session.keys());
    if not template_name:
        template_name = 'new_registration_messages.html'
    return render(request, template_name, {
        'account_verification_active': registration_settings.USE_ACCOUNT_VERIFICATION,
        'email': request.session.get('new_email','you'),
        'expiration_days': registration_settings.ACCOUNT_VERIFICATION_DAYS,
        'static_header': True
    })

# ---------------- #
# End Registration #
# ---------------- #


@login_required
def register_blank_email(request):
    """
    Handle registration of email for users without one.
    
    Typically used after social authentication when email is not provided.
    
    Args:
        request: HttpRequest object
        
    Returns:
        HttpResponse: Email registration form or success page
    """
    """ Register e-mail when the user does not have registered in the database """
    if request.method == 'POST':
        form = RegisterEmailForm(instance=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('common_redirect_after_login')
    else:
        form = RegisterEmailForm(instance=request.user)

    return render(request, 'register_blank_email.html', {'actual_email': request.user.email, 'form': form})


@login_required
def redirect_after_login(request):
    """ Redirecting the user depending on your profile """
    #profile = request.user.profile.codename
    profile = getattr(getattr(request.user, 'profile', None), 'codename', None)
    redirect_page = 'TRM-Subindex'    
    context={}
    subdomain_data = subdomain(request)
    context['success']=True
    # redirect_page = request.session.pop('next','')
    # if redirect_page:
    #     return redirect(redirect_page)
        
    if not request.user.email:
        # If you have registered without email
        redirect_page = 'common_register_blank_email'
    if profile == 'recruiter':
        # If is Recruiter/Company
        recruiter = Recruiter.objects.get(user=request.user, user__is_active=True)
        if recruiter.company.all():
            subscription,created = Subscription.objects.get_or_create(company = recruiter.company.all()[0])
            if created:
                subscription.price_slab = PriceSlab.objects.first()
                subscription.save()
            if subdomain_data['active_host']:
                redirect_page = request.scheme + "://" + subdomain_data['active_host'].replace('http://','').replace('https://','')
            else:
                redirect_page = request.scheme + "://" + recruiter.company.all()[0].getsubdomainurl().replace('http://','').replace('https://','')
        else:
            redirect_page = 'companies_record_company'
    elif profile == 'candidate':
        # If is Candidate
        try:
            host = subdomain_data['active_host']
        except:
            host=None
        if host:
            redirect_page = reverse('TRM-Subindex')
        else:
            #redirect_page = reverse('TRM-index')
            redirect_page = reverse('candidates_edit_curriculum')
    elif profile == 'Admin':
        redirect_page = SITE_URL + '/admin/'
    if not is_ajax(request):
        return redirect(redirect_page)
    else:
        return JsonResponse(context)

# ------------ #
# Email Change #
# ------------ #
@login_required
def email_change(request):
    """
    Handle email address change requests.
    
    Processes the email change form and initiates verification process.
    
    Args:
        request: HttpRequest object
        
    Returns:
        HttpResponse: Email change form or confirmation page
    """
    if request.method == 'POST':
        form = ChangeEmailForm(request.POST)
        if form.is_valid():
            verification = form.save(request.user)
            email = request.POST['new_email']
            request.session['new_email'] = email
            return redirect('common_email_change_requested')
    else:
        form = ChangeEmailForm()

    return render(request, 'email_change.html', {'actual_email': request.user.email, 'form': form})


@login_required
def email_change_requested(request):
    return render(request, 'email_change_requested.html',
                  {'email': request.session['new_email'],
                   'expiration_days': registration_settings.EMAIL_VERIFICATION_DAYS,})


@login_required
def email_change_approve(request, token, code):
    try:
        verification = EmailVerification.objects.get(token=token, code=code,
            user=request.user, is_expired=False, is_approved=False)
        verification.is_approved = True
        verification.save()
        messages.success(request, _(u'The email has changed to %(email)s' % {
            'email': verification.new_email}))
    except EmailVerification.DoesNotExist:
        messages.error(request,
            _(u'You cannot change the Email address. The confirmation link is invalid.'))
    profile = request.user.profile.codename
    if profile == 'candidate':
        return redirect('candidates_edit_curriculum')
    else:
        return redirect('companies_recruiter_profile')


# ---------------------- #
# Password Change #
# ---------------------- #
@login_required
def password_change_done(request):
    profile = request.user.profile
    messages.success(request, _(u'Your password has changed successfully.'))
    if profile == 'candidate':
        return redirect('candidates_edit_curriculum')
    else:
        return redirect('companies_recruiter_profile')


def custom_password_reset_complete(request):
    """ When the password is reset """
    messages.success(request, _(u'Your password has been successfully restored'))
    return redirect('auth_login')


def recover_user_requested(request):
    """ Recover User """
    return render(request, 'new_recover_user_requested.html',{'static_header':True})


# ------------------ #
# Contact Page #
# ------------------ #
from django.views.generic.edit import FormView

def contact_form(request):
    form = ContactForm(data=request.POST, request=request)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('common_contact_form_sent')
    return render(request,'contact_page.html',{'form':form,})

class ContactFormView(FormView):
    """
    View for handling contact form submissions.
    
    Provides:
    - Form display
    - Validation
    - Email sending
    - Success handling
    
    Attributes:
        form_class: The form class to use
        template_name: Template for rendering the form
    """
    form_class = ContactForm
    template_name = 'contact_page.html'

    def form_valid(self, form):
        """
        Handle valid form submission.
        
        Args:
            form: Validated form instance
            
        Returns:
            HttpResponse: Redirect to success page
        """
        form.save()
        return super(ContactFormView, self).form_valid(form)

    def get_form_kwargs(self):
        # ContactForm instances require instantiation with an
        # HttpRequest.
        kwargs = super(ContactFormView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_success_url(self):
        # This is in a method instead of the success_url attribute
        # because doing it as an attribute would involve a
        # module-level call to reverse(), creating a circular
        # dependency between the URLConf (which imports this module)
        # and this module (which would need to access the URLConf to
        # make the reverse() call).
        return reverse('common_contact_form_sent')

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response with a template rendered with the given context.
        """
        context['isContact'] = True
        return self.response_class(
            request = self.request,
            template = self.get_template_names(),
            context = context,
            **response_kwargs
        )

def debug_fb_token(fbtoken):
    """
    Debug a Facebook access token.
    
    Args:
        fbtoken: Facebook access token
        
    Returns:
        dict: Token debug information
    """
    consumer_key = settings.SOCIALAUTH_FACEBOOK_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_FACEBOOK_OAUTH_SECRET
    url = "https://graph.facebook.com/debug_token?input_token="+str(fbtoken)+"&access_token="+consumer_key+"|"+consumer_secret
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data

def revoke_fb_token(fbtoken):
    consumer_key = settings.SOCIALAUTH_FACEBOOK_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_FACEBOOK_OAUTH_SECRET
    url = "https://graph.facebook.com/debug_token?input_token="+str(fbtoken)+"&access_token="+consumer_key+"|"+consumer_secret
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data

def debug_gp_token(ghtoken):
    consumer_key = settings.SOCIALAUTH_GOOGLEPLUS_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_GOOGLEPLUS_OAUTH_SECRET
    url = " https://www.googleapis.com/oauth2/v1/tokeninfo?access_token="+ghtoken
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data

def debug_gh_token(ghtoken):
    consumer_key = settings.SOCIALAUTH_GITHUB_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_GITHUB_OAUTH_SECRET
    url = "https://api.github.com/user?access_token="+ghtoken
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data

def debug_so_token(sotoken):
    consumer_key = settings.SOCIALAUTH_STACKOVERFLOW_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_STACKOVERFLOW_OAUTH_SECRET
    url = "https://api.stackexchange.com/2.2/access-tokens/"+sotoken
    resp = requests.get(url)
    Data = json.loads(resp.content)
    return Data

def debug_li_token(litoken):
    consumer_key = settings.SOCIALAUTH_LINKEDIN_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_LINKEDIN_OAUTH_SECRET
    url = "https://api.linkedin.com/v1/people/~:(id,picture-url,headline,first-name,last-name)?format=json&oauth2_access_token="+litoken
    resp = requests.get(url)
    Data = json.loads(resp.content)
    return Data

def revoke_li_token(litoken):
    consumer_key = settings.SOCIALAUTH_LINKEDIN_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_LINKEDIN_OAUTH_SECRET
    url = "https://api.linkedin.com/v1/people/~:(id,picture-url,headline,first-name,last-name)?format=json&oauth2_access_token="+litoken
    resp = requests.get(url)
    Data = json.loads(resp.content)
    return Data

def debug_tw_token(twtoken):
    consumer_key = settings.SOCIALAUTH_TWITTER_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_TWITTER_OAUTH_SECRET
    access_token = twtoken.split('|-|')[0]
    access_token_secret = twtoken.split('|-|')[1]
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
    url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    resp = requests.get(url, auth=auth)
    Data = json.loads(resp.content)
    return Data

def revoke_tw_token(twtoken):
    consumer_key = settings.SOCIALAUTH_TWITTER_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_TWITTER_OAUTH_SECRET
    access_token = twtoken.split('|-|')[0]
    access_token_secret = twtoken.split('|-|')[1]
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
    url = "https://api.twitter.com/oauth2/invalidate_token"
    resp = requests.get(url, auth=auth)
    Data = json.loads(resp.content)
    return Data

def debug_token(token,social_code):
    if social_code == 'fb':
        return debug_fb_token(token)
    elif social_code == 'gp':
        return debug_gp_token(token)
    elif social_code == 'gh':
        return debug_gh_token(token)
    if social_code == 'li':
        return debug_li_token(token)
    elif social_code == 'so':
        return debug_so_token(token)    
    if social_code == 'tw':
        return debug_tw_token(token)
def revoke_token(token,social_code):
    if social_code == 'fb':
        return revoke_fb_token(token)
    # elif social_code == 'gp':
        # return revoke_gp_token(token)
    # elif social_code == 'gh':
        # return revoke_gh_token(token)
    elif social_code == 'li':
        return revoke_li_token(token)
    # elif social_code == 'so':
        # return revoke_so_token(token)    
    elif social_code == 'tw':
        return revoke_tw_token(token)
def get_account(social_code, identifier, email):
    auth = SocialAuth.objects.filter(social_code=social_code, identifier = identifier)
    if auth:
        return auth[0].user
    user = User.objects.filter(email=email)
    if user:
        return user[0]
    return None

def get_fb_web_response(suffix, socialauth=None):
    url = "https://graph.facebook.com/v2.8/" + suffix
    if socialauth:
        url = url + '&access_token=' + str(socialauth)
    resp = urllib.urlopen(url)
    return resp

def get_fb_user_groups(user):
    consumer_key = settings.SOCIALAUTH_FACEBOOK_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_FACEBOOK_OAUTH_SECRET
    socialUser = SocialAuth.objects.get(user = user, social_code = 'fb')
    url = "https://graph.facebook.com/me/groups?access_token="+socialUser.oauth_token
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data

def get_fb_user_pages(user):
    consumer_key = settings.SOCIALAUTH_FACEBOOK_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_FACEBOOK_OAUTH_SECRET
    socialUser = SocialAuth.objects.get(user = user, social_code = 'fb')
    url = "https://graph.facebook.com/me/accounts?access_token="+socialUser.oauth_token
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data

def get_fb_profile(user):
    consumer_key = settings.SOCIALAUTH_FACEBOOK_OAUTH_KEY
    consumer_secret = settings.SOCIALAUTH_FACEBOOK_OAUTH_SECRET
    socialUser = SocialAuth.objects.get(user = user, social_code = 'fb')
    url = "https://graph.facebook.com/me/?fields=name,picture&access_token="+socialUser.oauth_token
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data
    
def get_li_companies(user):
    socialUser = SocialAuth.objects.get(user = user, social_code = 'li')
    url = 'https://api.linkedin.com/v1/companies?format=json&is-company-admin=true&oauth2_access_token='+socialUser.oauth_token
    resp = urllib.urlopen(url)
    Data = json.loads(resp.read())
    return Data
