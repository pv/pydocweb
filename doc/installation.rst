============
Installation
============

Requirements
============

Pydocweb requires that the following dependencies are installed:

   - Django (>= 1.0; http://www.djangoproject.com/)
   - RCS 'merge' tool (in package "rcs" in Ubuntu/Debian), OR, Bzr
   - Python Imaging Library (in package "python-imaging" in Ubuntu/Debian)
   - lxml
   - LaTeX (optional, for math)
   - Dvipng (optional, for math)

Initial setup
=============

Before serious deployment, you'll likely want to test it and
initialize it first. This is probably easiest to try on your desktop
instead of doing it on the deployment server.

1. Edit :file:`settings.py` and:

   - Fill in a random string to SECRET_KEY

   - Fill in ADMINS (they get mail when DEBUG=False and something fails)

   - Adjust the database setup, if you want to use something else than
     SQLite for the database.

     .. warning:: Using anything else than SQLite or MySQL may not work yet.

2. Create database by running::

       ./manage.py syncdb

   Remember to answer 'yes' when it asks you to create a superuser account.

3. Install "Editor" and "Reviewer" groups by::

       sqlite3 data.db < scripts/template-groups.sql

4. Try it out *now*, by running::

       ./manage.py runserver

   and navigating your browser to the address this command prints.
   You should see the a working front page greeting you.

Module setup
============

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
=============

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

4. Don't like the visual appearance? Edit the templates and CSS.


Deployment
==========

There are many ways to deploy Django-based applications on servers,
and all of them should work for Pydocweb (provided you make the
:file:`modules` directory writable for the web server and otherwise
take care of file permissions). For general documentation, see
Django's `deployment guide`_.

Some example configurations are, however, explained below.

.. _`deployment guide`: http://docs.djangoproject.com/en/dev/howto/deployment/


Example: Simple Apache + ``mod_python``
---------------------------------------

Aim: we want to serve Pydocweb for Numpy in ``/numpy``, ASAP.

Make the directory layout as follows::

   /wherever/pydocweb
   |-- media
   |   |-- math [*]
   |   ...
   |-- modules [*]
   |   |-- data.db [*]
   |   `-- pull-numpy.sh
   |-- settings.py
   | ... pydocweb's source code ...

   /var/www
   |-- site_media -> /wherever/pydocweb/media
   `-- admin_media -> /usr/local/lib/python2.5/site-packages/Django-1.0_final-py2.5.egg/django/contrib/admin/media

Entries marked [*] need to be writable by the web server, and
everything needs to be readable by it. Note the link to Django's admin
app's static files.

The Apache configuration looks like the following::

    <VirtualHost *:80>
      DocumentRoot /var/www
      <Location "/numpy/">
        SetHandler python-program
        PythonHandler django.core.handlers.modpython
        SetEnv DJANGO_SETTINGS_MODULE pydocweb.settings
        PythonOption django.root /numpy
        PythonPath "['/wherever'] + sys.path"
        PythonDebug On
      </Location>
    </VirtualHost>

The ``settings.py`` file contains the following relevant variables::

    DEBUG = False
    PULL_SCRIPT = relative_dir("modules/pull-numpy.sh")
    MODULE_DIR = relative_dir("modules")
    ADMINS = (('Foo Bar', 'foo.bar@quux.com.invalid'),)
    SECRET_KEY = 'example-secret-key-1kovAouhk5y8auwhyPWPgs4YYbO0SauE'
    DATABASES['default']['ENGINE'] = 'sqlite3'
    DATABASES['default']['NAME'] = relative_dir("modules/data.db")
    SITE_PREFIX = '/numpy'
    ADMIN_MEDIA_PREFIX = '/admin_media/'

Finally, go to Control -> Admin site -> Sites and change the site 'domain'
to "www.domain.com/numpy".

And that's pretty much there's to it.

Continuation: Another Pydocweb site, sharing users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Aim: Now that a site for Numpy is set up, we'd like to put up a site for
Numpy's reference guide.

Go to Control -> Admin site -> Sites (on the Numpy site) and add a new site
with 'domain' "www.domain.com/numpy-refguide" and appropriate name.
Pay heed to the SITE ID the new site gets (after adding the site, click
the new site, and look at the URL: "../admin/sites/site/2/" -> the site id
is 2).

Create a :file:`settings_numpy_refguide.py` in the :file:`pydocweb`
directory::

    from settings import *
    SITE_ID = 2
    PULL_SCRIPT = relative_dir("modules/pull-numpy-refguide.sh")
    SITE_PREFIX = "/numpy-refguide"

and add to the Apache configuration::

      <Location "/numpy-refguide/">
        SetHandler python-program
        PythonHandler django.core.handlers.modpython
        SetEnv DJANGO_SETTINGS_MODULE pydocweb.settings_numpy_refguide
        PythonOption django.root /numpy-refguide
        PythonPath "['/wherever'] + sys.path"
        PythonDebug On
        PythonInterpreter refguidesite
      </Location>

You can leave out the ``PythonInterpreter`` statement if you put the
new site definition into a different VirtualHost.

Finally, note that the shell scripts ``generate-path.sh``,
``import-docstrings.sh``, ``update-docstrings.sh``, and
``upgrade-db-schema.sh`` hard-code the name of the ``settings``
module.  They are very simple scripts, so you can adapt them if you
need to run them against a different site than the default one.


Example: More involved Apache + ``mod_python``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    DATABASES['default']['ENGINE'] = 'sqlite3'
    DATABASES['default']['NAME'] = '/var/www/lib/pydocweb-numpy/data.db'
    SITE_PREFIX = '/numpy'
    ADMIN_MEDIA_PREFIX = '/site_media/admin/'
    MATH_ROOT = '/var/www/lib/pydocweb-numpy/math-images'

We also go to Control -> Admin site -> Sites and change the site 'domain'
to "www.domain.com/numpy".
