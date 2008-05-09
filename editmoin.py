"""
Copyright (c) 2002-2006  Gustavo Niemeyer <gustavo@niemeyer.net>

This program allows you to edit moin (see http://moin.sourceforge.net)
pages with your preferred editor. The default editor is vi. If you want
to use any other, just set the EDITOR environment variable.

To define your moin id used when logging in in a specifc moin, edit a
file named ~/.moin_ids and include lines like "http://moin.url/etc myid".

WARNING: This program expects information to be in a very specific
         format. It will break if this format changes, so there are
         no warranties of working at all. All I can say is that it
         worked for me, at least once. ;-)

Tested moin versions: 0.9, 0.11, 1.0, 1.1, 1.3.5, 1.5, 1.5.1, 1.5.4, 1.5.5, 1.6
"""

__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__version__ = "1.9.1"
__license__ = "GPL"

import tempfile
import textwrap
import sys, os
import urllib
import shutil
import md5
import re


USAGE = "Usage: editmoin [-t <template page>] <moin page URL>\n"

IDFILENAME = os.path.expanduser("~/.moin_ids")
ALIASFILENAME = os.path.expanduser("~/.moin_aliases")


BODYRE = re.compile('<textarea.*?name="savetext".*?>(.*)</textarea>',
                    re.M|re.DOTALL)
DATESTAMPRE = re.compile('<input.*?name="datestamp".*?value="(.*?)".*?>')
NOTIFYRE = re.compile('<input.*?name="notify".*?value="(.*?)".*?>')
COMMENTRE = re.compile('<input.*?name="comment".*>')
TRIVIALRE = re.compile('<input.*?name="trivial".*?value="(.*?)".*?>')
MESSAGERE1 = re.compile('^</table>(.*?)<a.*?>Clear message</a>',
                        re.M|re.DOTALL)
MESSAGERE2 = re.compile('<div class="message">(.*?)</div>', re.M|re.DOTALL)
MESSAGERE3 = re.compile('<div id="message">\s*<p>(.*?)</p>', re.M|re.DOTALL)
STATUSRE = re.compile('<p class="status">(.*?)</p>', re.M|re.DOTALL)
CANCELRE = re.compile('<input.*?type="submit" name="button_cancel" value="(.*?)">')
EDITORRE = re.compile('<input.*?type="hidden" name="editor" value="text">')
TICKETRE = re.compile('<input.*?type="hidden" name="ticket" value="(.*?)">')
REVRE = re.compile('<input.*?type="hidden" name="rev" value="(.*?)">')
CATEGORYRE = re.compile('<option value="(Category\w+?)">')
SELECTIONRE = re.compile("\(([^)]*)\)\s*([^(]*)")
EXTENDMSG = "Use the Preview button to extend the locking period."


marker = object()


class Error(Exception): pass


class MoinFile:

    multi_selection = ["notify", "trivial", "add_category"]

    def __init__(self, filename, id):
        self.filename = filename
        self.id = id
        self.data = open(filename).read()
        self.body = self._get_data(BODYRE, "body")

        try:
            self.datestamp = self._get_data(DATESTAMPRE, "datestamp")
        except Error:
            self.datestamp = None

        try:
            self.notify = self._get_data(NOTIFYRE, "notify")
            self.comment = "None"
        except Error:
            self.notify = None
            if COMMENTRE.search(self.data):
                self.comment = "None"
            else:
                self.comment = None

        try:
            self.trivial = self._get_data(TRIVIALRE, "trivial")
        except Error:
            self.trivial = None

        self.categories = self._get_data_findall(CATEGORYRE, "category", [])
        self.add_category = None

        match = STATUSRE.search(self.data)
        if match:
            self.status = strip_html(match.group(1))
        else:
            self.status = None

        self.rev = self._get_data(REVRE, "rev", None)
        self.ticket = self._get_data(TICKETRE, "ticket", None)

    def _get_data(self, pattern, info, default=marker):
        match = pattern.search(self.data)
        if not match:
            if default is not marker:
                return default
            message = get_message(self.data)
            if message:
                print message
            raise Error, info+" information not found"
        else:
            return match.group(1)

    def _get_data_findall(self, pattern, info, default=marker):
        groups = pattern.findall(self.data)
        if not groups:
            if default is not marker:
                return default
            raise Error, info+" information not found"
        return groups

    def _get_selection(self, str):
        for selected, option in SELECTIONRE.findall(str):
            if selected.strip():
                return option.strip()
        return None

    def _unescape(self, data):
        data = data.replace("&lt;", "<")
        data = data.replace("&gt;", ">")
        data = data.replace("&amp;", "&")
        return data

    def has_cancel(self):
        return (CANCELRE.search(self.data) is not None)

    def has_editor(self):
        return (EDITORRE.search(self.data) is not None)

    def write_file(self, file_or_name):
        if hasattr(file_or_name,'write'):
            file = file_or_name
            close_after_use = False
        else:
            file = open(filename, "w")
            close_after_use = True

        file.write(self._unescape(self.body))

        if close_after_use:
            file.close()

        return file_or_name


    def write_raw(self):
        filename = tempfile.mktemp(".moin")
        file = open(filename, "w")
        file.write("@@ vim:ft=moin\n")
        if not self.id:
            file.write("@@ WARNING! You're NOT logged in!\n")
        else:
            file.write("@@ Using ID %s.\n" % self.id)
        if self.status is not None:
            text = self.status.replace(EXTENDMSG, "").strip()
            lines = textwrap.wrap(text, 70,
                                  initial_indent="@@ Message: ",
                                  subsequent_indent="@           ")
            for line in lines:
                file.write(line+"\n")
        if self.comment is not None:
            file.write("@@ Comment: %s\n" % self.comment)
        if self.trivial is not None:
            file.write("@@ Trivial: ( ) Yes  (x) No\n")
        if self.notify is not None:
            yes, no = (self.notify and ("x", " ") or (" ", "x"))
            file.write("@@ Notify: (%s) Yes  (%s) No\n" % (yes, no))
        if self.categories:
            file.write("@@ Add category: (x) None\n")
            for category in self.categories:
                file.write("@                ( ) %s\n" % category)
        file.write(self._unescape(self.body))
        file.close()
        return filename

    def read_raw(self, filename):
        file = open(filename)
        lines = []
        data = file.readline()
        while data != "\n":
            if data[0] != "@":
                break
            if len(data) < 2:
                pass
            elif data[1] == "@":
                lines.append(data[2:].strip())
            else:
                lines[-1] += " "
                lines[-1] += data[2:].strip()
            data = file.readline()
        self.body = data+file.read()
        file.close()
        for line in lines:
            sep = line.find(":")   
            if sep != -1:
                attr = line[:sep].lower().replace(' ', '_')
                value = line[sep+1:].strip()
                if attr in self.multi_selection:
                    setattr(self, attr, self._get_selection(value))
                else:
                    setattr(self, attr, value)

    def read_string(self, str):
        self.body = str
        print self.body


def get_message(data):
    match = MESSAGERE3.search(data)
    if not match:
        # Check for moin < 1.3.5 (not sure the precise version it changed).
        match = MESSAGERE2.search(data)
    if not match:
        # Check for moin <= 0.9.
        match = MESSAGERE1.search(data)
    if match:
        return strip_html(match.group(1))
    return None 

def strip_html(data):
    data = re.subn("\n", " ", data)[0]
    data = re.subn("<p>|<br>", "\n", data)[0]
    data = re.subn("<.*?>", "", data)[0]
    data = re.subn("Clear data", "", data)[0]
    data = re.subn("[ \t]+", " ", data)[0]
    data = data.strip()
    return data

def get_id(moinurl):
    if os.path.isfile(IDFILENAME):
        file = open(IDFILENAME)
        for line in file.readlines():
            line = line.strip()
            if line and line[0] != "#":
                tokens = line.split()
                if len(tokens) > 1:
                    url, id = tokens[:2]
                else:
                    url, id = tokens[0], None
                if moinurl.startswith(url):
                    return id
    return None

def translate_shortcut(moinurl):
    if "://" in moinurl:
        return moinurl
    if "/" in moinurl:
        shortcut, pathinfo = moinurl.split("/", 1)
    else:
        shortcut, pathinfo = moinurl, ""
    if os.path.isfile(ALIASFILENAME):
        file = open(ALIASFILENAME)
        try:
            for line in file.readlines():
                line = line.strip()
                if line and line[0] != "#":
                    alias, value = line.split(None, 1)
                    if pathinfo:
                        value = "%s/%s" % (value, pathinfo)
                    if shortcut == alias:
                        if "://" in value:
                            return value
                        if "/" in value:
                            shortcut, pathinfo = value.split("/", 1)
                        else:
                            shortcut, pathinfo = value, ""
        finally:
            file.close()
    if os.path.isfile(IDFILENAME):
        file = open(IDFILENAME)
        try:
            for line in file.readlines():
                line = line.strip()
                if line and line[0] != "#":
                    url = line.split()[0]
                    if shortcut in url:
                        if pathinfo:
                            return "%s/%s" % (url, pathinfo)
                        else:
                            return url
        finally:
            file.close()
    raise Error, "no suitable url found for shortcut '%s'" % shortcut


def get_urlopener(moinurl, id=None):
    urlopener = urllib.URLopener()
    proxy = os.environ.get("http_proxy")
    if proxy:
        urlopener.proxies.update({"http": proxy})
    if id:
        # moinmoin < 1.6
        urlopener.addheader("Cookie", "MOIN_ID=\"%s\"" % id)
        # moinmoin >= 1.6
        urlopener.addheader("Cookie", "MOIN_SESSION=\"%s\"" % id)
    return urlopener

def fetchfile(urlopener, url, id, template):
    geturl = url+"?action=edit"
    if template:
        geturl += "&template=" + urllib.quote(template)
    filename, headers = urlopener.retrieve(geturl)
    return MoinFile(filename, id)

def editfile(moinfile):
    edited = 0
    filename = moinfile.write_raw()
    editor = os.environ.get("EDITOR", "vi")
    digest = md5.md5(open(filename).read()).digest()
    os.system("%s %s" % (editor, filename))
    if digest != md5.md5(open(filename).read()).digest():
        shutil.copyfile(filename, os.path.expanduser("~/.moin_lastedit"))
        edited = 1
        moinfile.read_raw(filename)
    os.unlink(filename)
    return edited

def sendfile(urlopener, url, moinfile):
    if moinfile.comment is not None:
        comment = "&comment="
        if moinfile.comment.lower() != "none":
            comment += urllib.quote(moinfile.comment)
    else:
        comment = ""
    data = "button_save=1&savetext=%s%s" \
           % (urllib.quote(moinfile.body), comment)
    if moinfile.has_editor():
        data += "&action=edit"      # Moin >= 1.5
    else:
        data += "&action=savepage"  # Moin < 1.5
    if moinfile.datestamp:
        data += "&datestamp=" + moinfile.datestamp
    if moinfile.rev:
        data += "&rev=" + moinfile.rev
    if moinfile.ticket:
        data += "&ticket=" + moinfile.ticket
    if moinfile.notify == "Yes":
        data += "&notify=1"
    if moinfile.trivial == "Yes":
        data += "&trivial=1"
    if moinfile.add_category and moinfile.add_category != "None":
        data += "&category=" + urllib.quote(moinfile.add_category)
    url = urlopener.open(url, data)
    answer = url.read()
    url.close()
    message = get_message(answer)
    if message is None:
        print answer
        raise Error, "data submitted, but message information not found"
    else:
        print message

def sendcancel(urlopener, url, moinfile):
    if not moinfile.has_cancel():
        return
    data = "button_cancel=Cancel"
    if moinfile.has_editor():
        data += "&action=edit&savetext=dummy"  # Moin >= 1.5
    else:
        data += "&action=savepage"             # Moin < 1.5
    if moinfile.datestamp:
        data += "&datestamp=" + moinfile.datestamp
    if moinfile.rev:
        data += "&rev=" + moinfile.rev
    if moinfile.ticket:
        data += "&ticket=" + moinfile.ticket
    url = urlopener.open(url, data)
    answer = url.read()
    url.close()
    message = get_message(answer)
    if not message:
        print answer
        raise Error, "cancel submitted, but message information not found"
    else:
        print message

def main():
    argv = sys.argv[1:]
    template = None
    if len(argv) > 2 and argv[0] == "-t":
        template = argv[1]
        argv = argv[2:]
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        sys.stderr.write(USAGE)
        sys.exit(1)
    try:
        url = translate_shortcut(argv[0])
        id = get_id(url)
        urlopener = get_urlopener(url, id)
        moinfile = fetchfile(urlopener, url, id, template)
        try:
            if editfile(moinfile):
                sendfile(urlopener, url, moinfile)
            else:
                sendcancel(urlopener, url, moinfile)
        finally:
            os.unlink(moinfile.filename)
    except (IOError, OSError, Error), e:
        sys.stderr.write("error: %s\n" % str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()

# vim:et:ts=4:sw=4
