============
Installation
============

1. Install requirements:

   - Django (>= 1.0; http://www.djangoproject.com/)
   - RCS 'merge' tool (in package "rcs" in Ubuntu/Debian)
   - Python Imaging Library (in package "python-imaging" in Ubuntu/Debian)
   - LaTeX (optional, for math)
   - Dvipng (optional, for math)

2. Create database by running::

       ./manage.py syncdb

3. If you want sample "Editor" and "Reviewer" groups, do::

       sqlite3 data.db < scripts/template-groups.sql

4. If you want just to try it out *now*, run::

       ./manage.py runserver

5. Create a "pull script" for your project. See "settings.py" for
   an explanation, and check the examples under modules/

6. Edit 'settings.py' to match your setup.

   - Adjust PULL_SCRIPT to match the Python module you are documenting

   - Fill in a random string to SECRET_KEY

   - Fill in ADMINS (they get mail when DEBUG=False and something fails)

   Before going production,

   - Publish the media/ subdirectory on your web server, and adjust MEDIA_URL
     accordingly.

   - Set DEBUG=False

   For production deployment, see Django's deployment guide at
   http://docs.djangoproject.com/en/dev/howto/deployment/

7. Change the site name: Go to the "Control" tab -> Administration site
   on the site, and change the "example.com" in the Sites to something
   that suits you.

   To understand what the Sites in general do, see
   http://docs.djangoproject.com/en/dev/ref/contrib/sites/
   In short, they allow you to share user and docstring data between different
   sites (that use the same DB). Wiki pages are not shared.

8. Run "Pull from" on the "Control" tab.
   Note that this compiles your module, imports it, and collects its docstrings
   (in a separate process).

   If this fails with a server timeout, run ./update-docstrings.sh instead.

9. Write a proper front page and modify the "registration" page, if needed.

10. Set up regular backups of your database.

11. Start writing!
