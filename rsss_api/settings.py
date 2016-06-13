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
    'django_cassandra_engine',
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
#

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
#Here is the first one...
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
#second one....
#DATABASES = {
#   'default': {
#     'ENGINE' : 'django.db.backends.mysql',
#     'NAME'   : 'motif_score_test_db',
#     'USER'   : 'snp_test', 
#     'PASSWORD' : 'tester',
#     'HOST'     : 'fugu.biostat.wisc.edu',
#     'PORT'     : '3306',
#     'TEST'     : {  
#        'NAME'   :  'subset_db_for_testing' ,
#      }
#   }
#}
#
#DATABASES = {
#        'default': {
#            'ENGINE': 'django_cassandra_engine',
#            'NAME': 'rsnp_data',
#            'TEST_NAME': 'rsnp_data_test_db',
#            'HOST': 'quasar-18,quasar-19,quasar-25',
#            'OPTIONS': {
#                'replication': {
#                    'strategy_class': 'SimpleStrategy',
#                    'replication_factor': 1
#                },
#                'session': {
#                    'default_timeout' : 50,
#                    'default_fetch_size': 1000
#                },
#                'connection': {
#                      'consistency': ConsistencyLevel.LOCAL_ONE,
#                      'retry_connect': True
#                      # + All connection options for cassandra.cluster.Cluster()
#                }
#            }
#        }
#    }
# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

ELASTICSEARCH_URL='http://quasar-19:9200'


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

DEFAULT_P_VALUE = 0.05


HARD_LIMITS = {
  'MAX_NUMBER_OF_SNPIDS_ALLOWED_TO_REQUEST': 1000000000,
  'MAX_BASES_IN_GL_REQUEST': 100000000000
}

