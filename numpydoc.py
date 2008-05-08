#!/usr/bin/env python

"""
This programs allows you to generate the numpy documentation wiki
"""


import inspect
import numpy
import editmoin
import os
import string
import sys
import types
from StringIO import StringIO
from optparse import make_option, OptionParser

class MoinPage():

    def __init__(self,url):
        self.url = url
    

    def write_file(self,sourcefile, id = None):
        template = None
        urlopener = editmoin.get_urlopener(self.url, id)
        moinfile = editmoin.fetchfile(urlopener, self.url, id, template)
        geturl = self.url+"?action=edit"
        filename, headers = urlopener.retrieve(geturl)
        mf = editmoin.MoinFile(filename, id)
        mf.read_raw(sourcefile)
        editmoin.sendfile(urlopener, self.url, mf)
        #editmoin.sendcancel(urlopener, self.url, mf)

    def retrieve_docstring(self):
        template = None
        urlopener = editmoin.get_urlopener(self.url, id)
        moinfile = editmoin.fetchfile(urlopener, self.url, id, template)
        dump = StringIO()
        moinfile.write_file(dump)
        dump.seek(0)
        lines = dump.readlines()
        return string.join(lines[5:-1],"").strip() #Needs better parsing of course !!


class DocModificator():

    def __init__(self, wiki_url=None, base_module_dir='numpy'):
        """Creates doc modificator object from
        - wiki_url: url address of the wiki where the doc is to be exposed, 
        and possibly modified by users
        - base_module_dir: directory where the module files are stored 
        (could be a bzr branch e.g.)
        """
        print base_module_dir
        sys.path.append('')
        self.base_dir = os.path.dirname(base_module_dir)
        sys.path.insert(0,self.base_dir)
        self.module = __import__(base_module_dir)
        #self.module = __import__(os.path.basename(base_module_dir))
        print self.module
        self.wiki_url = wiki_url

    def _get_funcs(self):
        """Returns a list of functions to be documented

        Uses utilities from module inspect.
        """
        self.module_names = [(name,func) for name,func in \
                             inspect.getmembers(self.module) if \
                             callable(func) and inspect.getdoc(func) and \
                             (isinstance(func,types.FunctionType) or
                              isinstance(func,self.module.ufunc))]

    def upload_to_wiki(self):
        """Writes wiki pages from the module's documentation

        Writes a front page with a list of all function, linking to individual 
        wiki pages with the documentation for each function. Uses the class MoinPage. 
        """
        self._get_funcs()

        mfp = MoinPage(self.wiki_url)
        # Open temporary file for storing information. 
        # This is a hack to reuse code in editmoin 
        file = open('numpy_list','w')
        # Generate front page, which is a numbered list of functions (1. with moin syntax)
        for n in self.module_names:
            file.write(' 1. [:/%s:%s]\n' % (n[0],n[0]))
        file.close()
        print "Uploading index file..."
        mfp.write_file('numpy_list')

        # Generate a page for each function
        for n,fn in self.module_names:
            n_url = os.path.join(self.wiki_url, n)
            print "Generating %s..." % n_url
            fn_doc = function_doc(n,fn)
            mf = MoinPage(n_url)
            # Another temporary file
            file = open('temp','w')
            file.write(fn_doc)
            file.close()
            mf.write_file('temp') # write to page

    def download_from_wiki(self):
        """Grab docs from a wiki to files in a directory, replacing the old 
        docstrings by the new docstrings from the wiki
            
        Loops over functions in the module, retrieves doc from the corresponding page
        in the wiki, and calls the function self.write_fndoc_from_string to search for 
        the file where to replace the docstring, and replace the docstring. 
        """
        self._get_funcs()

        #fl = filelist(self.base_dir)
        # Keeps only .py extensions
        #fl = [file for file in fl if file[-3:]=='.py']
        for n,fn in self.module_names: 
            if n=='size':
                print fn
                n_url = os.path.join(self.wiki_url, n) #url of the wiki page
                mf = MoinPage(n_url)
                #try:
                str = mf.retrieve_docstring()
                self.write_fndoc_from_string(fn, str)
            #except:
            #    print "wiki page does not exist yet!"

    def write_fndoc_from_string(self,fn,str):
        """
            
        """
        fndoc = fn.__doc__
        indent_lv = indent_level(fndoc)
        sourcefile = inspect.getabsfile(fn)
        fid = open(sourcefile)
        str_file = fid.read()
        fid.close()
        if fndoc in str_file:
            str = string.join(str.split('\n'),'\n'+string.ljust('',indent_lv))
            fid = open(sourcefile, 'w')
            new_st = string.replace(str_file, fndoc, str)
            fid.write(new_st)
            fid.close()
        

def function_doc(n,fn):
    """For a function fn_name in module mod, returns a doc string correctly 
    formatted in rst with:
    - the name of the function 
    - the signature of the function (arguments)
    - the docstring

    This string is meant to be directly fed to a wiki page.
    """
    n_doc = inspect.getdoc(fn) # doc
    try:
        argspec = inspect.getargspec(fn) # arguments
        args = inspect.formatargspec(*argspec)
    except TypeError:
        args = '(x)'

    doc_str = "== %s ==\n{{{\n#!rst\n**%s** %s\n\n%s\n}}}\n" % \
            (n,n,args,inspect.getdoc(fn))
    return doc_str


def filelist(base_dir):
    fl = []
    for (root, subs, files) in os.walk(base_dir):
        fl += [os.path.join(root,file) for file in files]
    return fl

def indent_level(docstr):
    if not("\n" in docstr):
        return 4
    else:
        st = docstr.split('\n')[-1]
        if string.find(st, st.lstrip()):
            return string.find(st, st.lstrip()) 
        else:
            return len(st)

def main():
    parser = OptionParser()
    parser.add_option("-w", "--wiki", dest="url",
                  help = "write doc and fetch doc from the wiki at WIKI_URL ", metavar="WIKI_URL")
    parser.add_option("-D", "--dir", dest="dir",
                help = "write doc and fetch doc from the module locate in the directory DIR", metavar="DIR")
    parser.add_option("-u", "--uploadtowiki", action="store_true", dest="upload_to_wiki", default=False)
    parser.add_option("-d", "--downloadfromwiki", action="store_true", dest="download_from_wiki", default=False)
    (options, args) = parser.parse_args()
    print options
    dm = DocModificator(wiki_url = options.url, base_module_dir = options.dir)
    if options.upload_to_wiki:
        dm.upload_to_wiki()
    if options.download_from_wiki:
        dm.download_from_wiki()

if __name__ == "__main__":
    main()


# vim:et:ts=4:sw=4
