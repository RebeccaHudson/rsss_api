"""
Django settings for rsss_api project.

Generated by 'django-admin startproject' using Django 1.9.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'g*$z7a@8w+7-jr^atm1df!l&77dwfb(z^*qrma&ka0oapztsnp'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'api_v0.apps.ApiV0Config',
    'rest_framework',
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rsss_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rsss_api.wsgi.application'

#Should be able to remove this.
#ELASTICSEARCH_URL='http://atsnp-db1.biostat.wisc.edu:9200' #remove this?

#ELASTICSEARCH_URLS = [ 'http://atsnp-db'+ str(x) +'.biostat.wisc.edu:9200' for x in range(2,4) ]

#Cannot connect to atsnp-db2
#ELASTICSEARCH_URLS = [ 'http://atsnp-db'+ str(x) +'.biostat.wisc.edu:9200' for x in range(1,3) ]

ELASTICSEARCH_URLS = [ 'http://atsnp-db'+ str(x) +'.biostat.wisc.edu:9200' for x in range(1,2) ]
ELASTICSEARCH_PAGE_SIZE = 50  # this should be pretty large, ultimately.

#
ES_INDEX_NAMES = { 'ATSNP_DATA' : 'atsnp_data', #atsnp_reduced_test
                   'GENE_NAMES' : 'gencode_genes',
                    'SNP_INFO'  : 'snp_info',
                    'MOTIF_BITS': 'motif_plotting_data' }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')
STATIC_URL = os.path.join(BASE_DIR, "static/")



DEFAULT_P_VALUE = 0.05


HARD_LIMITS = {
  'MAX_NUMBER_OF_SNPIDS_ALLOWED_TO_REQUEST': 1000,
  'MAX_BASES_IN_GL_REQUEST': 1000000000,
  'ELASTIC_MAX_RESULT_WINDOW' : 10000
}

#TODO: make the naming conventions match the queries
GAIN_AND_LOSS_DEFS = {
    "gain" : { 
        "pval_ref" : { 'operator': 'gt', 'cutoff' : 0.05 },
        "pval_snp" : { 'operator': 'lte', 'cutoff' : 0.05 },
    },
    "loss" : {
        "pval_ref" : { 'operator': 'lte', 'cutoff' : 0.05 },
        "pval_snp" : { 'operator': 'gt' , 'cutoff' : 0.05 }
    }
}



