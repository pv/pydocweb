"""
This programs allows you to generate the numpy documentation wiki
"""


import inspect
import numpy
import editmoin
import os
import string

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

    def retrieve_docstring(self):
        template = None
        urlopener = editmoin.get_urlopener(self.url, id)
        moinfile = editmoin.fetchfile(urlopener, self.url, id, template)
        geturl = self.url+"?action=edit"
        filename, headers = urlopener.retrieve(geturl)
        mf = editmoin.MoinFile(filename, id)
        dumpfile = "coucou"
        filename = moinfile.write_file(dumpfile)
        fid = open(dumpfile,'r')
        lines = fid.readlines()
        return lines[5:-1] #Needs better parsing of course !!
        
        

class DocModificator():

    def __init__(self, module, wiki_url = None, base_dir = None):
        self.module = module
        self.wiki_url = wiki_url
        self. base_dir = base_dir

    def get_docs(self):
        self.module_names = [name for name in inspect.getmembers(self.module) if \
        (callable(name[1]) and (inspect.getdoc(name[1]) is not None) \
        and inspect.isfunction(name[1]))]

    def write_doc_to_wiki(self):
        mfp = MoinPage(self.wiki_url)
        # Open temporary file for storing information. 
        # This is a hack to reuse code in editmoin 
        file = open('numpy_list','w')
        # Generate front page, which is a numbered list of functions (1. with moin syntax)
        for n in self.module_names:
            file.write(' 1. [:/%s:%s]\n' % (n[0],n[0]))
        file.close()
        mfp.write_file('numpy_list')

        # Generate a page for each function
        for n,fn in self.module_names:
            n_url = os.path.join(self.wiki_url, n)
            print n_url
            print fn
            fn_doc = function_doc(n,fn)
            mf = MoinPage(n_url)
            # Another temporary file
            file = open('temp','w')
            file.write(fn_doc)
            file.close()
            mf.write_file('temp') # write to page

    def write_doc_from_wiki(self):
        fl = filelist(base_dir)


    def write_fndoc_from_string(self,fn,string,fl):
        fn_doc = inspect.getdoc(fn)
        print fn_doc
        for file in fl:
            fid = open(file,'r')
            st = fid.read()
            if fn_doc in st:
                print "trouve", file


def function_doc(n,fn):
    n_doc = inspect.getdoc(fn) # doc
    argspec = inspect.getargspec(fn) # arguments
    args = inspect.formatargspec(*argspec)
    doc_str = "== %s ==\n"%n + "{{{\n#!rst\n"+'**%s** '%(n)+args+'\n\n'+ \
        inspect.getdoc(fn) + "\n}}}\n"
    return doc_str

def filelist(base_dir):
    fl = []
    for (root, subs, files) in os.walk(base_dir):
        fl += [os.path.join(root,file) for file in files]
    return fl




# vim:et:ts=4:sw=4
