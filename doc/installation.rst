============
Installation
============

Basic setup
===========

Requirements
------------

Pydocweb requires that the following dependencies are installed:

   - Django (>= 1.0; http://www.djangoproject.com/)
   - RCS 'merge' tool (in package "rcs" in Ubuntu/Debian)
   - Python Imaging Library (in package "python-imaging" in Ubuntu/Debian)
   - LaTeX (optional, for math)
   - Dvipng (optional, for math)

Initial setup
-------------

Before serious deployment, you'll likely want to test it and
initialize it first. This is probably easiest to try on your desktop
instead of doing it on the deployment server.

0. Edit :file:`settings.py` and:

   - Fill in a random string to SECRET_KEY

   - Fill in ADMINS (they get mail when DEBUG=False and something fails)

   - Adjust the database setup, if you want to use something else than
     SQLite for the database.

1. Create database by running::

       ./manage.py syncdb

   Remember to answer 'yes' when it asks you to create a superuser account.

2. Install "Editor" and "Reviewer" groups by::

       sqlite3 data.db < scripts/template-groups.sql

3. Try it out *now*, by running::

       ./manage.py runserver

   and navigating your browser to the address this command prints.
   You should see the a working front page greeting you.

Module setup
------------

Next, you will need to tell Pydocweb what Python module or
documentation you want to use it for.

1. Create a "pull script" for your project. The pull script extracts
   docstring etc. from your Python module sources, and dumps the
   results to an XML file. Typically it is a shell script that calls
   Pydocweb's :ref:`pydoc-tool.py <pydoc-tool>`.

   See the file "settings.py", and check the examples under modules/

2. In :file:`settings.py`, adjust PULL_SCRIPT and MODULE_DIR according
   to your setup.

3. Navigate to the running test server, go to "Control" tab and
   click "Pull from sources".

   Note that this compiles your module, imports it, and collects its docstrings
   (in a separate process), so it will take some time.

4. You should now see your module's docstrings in the "Docstrings" tab.

Customisation
-------------

1. Change the site name: Go to the "Control" tab -> Administration site
   on the site, and change the "example.com" entry in the Sites section
   to something that suits you.

   To understand what the Sites in general do, see
   http://docs.djangoproject.com/en/dev/ref/contrib/sites/
   In short, they allow you to share user and docstring data between different
   sites (that use the same DB). Wiki pages are not shared.

2. Decide on user policy. By default Pydocweb allows new users to register
   accounts, but doesn't give edit permissions to them.

   If you want to change this, you can adjust the ``DEFAULT_USER_GROUPS``
   setting in :file:`settings.py`

3. Write a proper front page and modify the "registration" page, if needed.


Deployment
----------

There are many ways to deploy Django-based applications on servers,
and all of them should work for Pydocweb. For general documentation,
see Django's `deployment guide`_.

Some example configurations are, however, explained below.

.. _`deployment guide`: http://docs.djangoproject.com/en/dev/howto/deployment/


Example: Apache + ``mod_python``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Aim: we want to serve Pydocweb for Numpy in ``/numpy``, as a part of a
site containing also many other parts. We also want to put all data to
a separate directory than source code. The web server is Apache.

Make the directory layout as follows::

   /var/www
   |-- lib
   |   |-- pydocweb
   |   |   |-- LICENSE.txt
   |   |   ... pydocweb's source code; unmodified ...
   |   `-- pydocweb-numpy [*]
   |       |-- data.db [*]
   |       |-- modules [*]
   |       |   `-- pull-numpy.sh
   |       |-- math-images [*]
   |       `-- settings_numpy.py
   `-- root
       `-- site_media
           |-- css -> ../../lib/pydocweb/media/css
           |-- js -> ../../lib/pydocweb/media/js
           |-- math -> ../../lib/pydocweb-numpy/math-images
           `-- admin -> /usr/local/lib/python2.5/site-packages/Django-1.0_final-py2.5.egg/django/contrib/admin/media

Entries marked [*] need to be writable by the web server.
Note the link to Django's admin app's static files.

The Apache configuration looks like the following::

    <VirtualHost *:80>
      DocumentRoot /var/www/root
      <Location "/numpy/">
        SetHandler python-program
        PythonHandler django.core.handlers.modpython
        SetEnv DJANGO_SETTINGS_MODULE settings_numpy
        PythonOption django.root /numpy
        PythonPath "['/var/www/lib', '/var/www/lib/pydocweb-numpy'] + sys.path"
        PythonDebug On
      </Location>
    </VirtualHost>

and the active Django settings file, :file:`settings_numpy.py` reads::

    from pydocweb.settings import *
    DEBUG = False
    PULL_SCRIPT = "/var/www/lib/pydocweb-numpy/modules/pull-numpy.sh"
    MODULE_DIR = "/var/www/lib/pydocweb-numpy/modules"
    ADMINS = (('Foo Bar', 'foo.bar@quux.com.invalid'),)
    SECRET_KEY = 'example-secret-key-1kovAouhk5y8auwhyPWPgs4YYbO0SauE'
    DATABASE_ENGINE = 'sqlite3'
    DATABASE_NAME = '/var/www/lib/pydocweb-numpy/data.db'
    SITE_PREFIX = '/numpy'
    ADMIN_MEDIA_PREFIX = '/site_media/admin/'

We also go to Control -> Admin site -> Sites and change the site 'domain'
to "www.domain.com/numpy".

And that's pretty much there's to it.


Multiple sites
--------------

Pydocweb uses the django.contrib.sites_ framework, which allows you to
share users and docstrings between multiple Pydocweb instances
("sites"). In short, each "site" should have its own
:file:`settings.py` file (each with a different ``SITE_ID``) and entry
in web server configuration, but share the same database. (But note
that you can do ``from another_settings import *`` in a
``settings.py`` file to get settings from another file.)

.. _django.contrib.sites: http://docs.djangoproject.com/en/dev/ref/contrib/sites/
