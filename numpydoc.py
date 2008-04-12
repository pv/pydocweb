"""
This programs allows you to generate the numpy documentation wiki
"""


import inspect
import numpy
import editmoin

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


def main(url):
    """
        Given a url address, writes a list of numpy functions to the url webpage, 
        and creates an individual documentation page for each function.  
    """
    numpy_names = [name for name in inspect.getmembers(numpy) if (callable(name[1]) and \
    (inspect.getdoc(name[1]) is not None)and inspect.isfunction(name[1]))]
    mfp = MoinPage(url)

    # Open temporary file for storing information. This is a hack to reuse code in editmoin
    file = open('numpy_list','w')

    # Generate front page, which is a numbered list of functions (1. with moin syntax)
    for n in numpy_names:
        file.write(' 1. [:/%s:%s]\n' % (n[0],n[0]))
    file.close()
    mfp.write_file('numpy_list')

    # Generate a page for each function
    for n,fn in numpy_names:
        n_url = url +'/'+ n
        print fn
        mf = MoinPage(n_url)
        # Another temporary file
        file = open('temp','w')
        n_doc = inspect.getdoc(fn) # doc
        argspec = inspect.getargspec(fn) # arguments
        args = inspect.formatargspec(*argspec)
        file.write("== %s ==\n" %n) # title
        file.write("{{{\n#!rst\n") # start code block in rst
        file.write('**%s** ' %(n)+args+'\n')
        file.write(inspect.getdoc(fn))
        file.write("}}}\n") # end code block
        file.close()
        mf.write_file('temp') # write to page


if __name__ == "__main__":
    main("http://localhost:8000/NumpyDoc")


# vim:et:ts=4:sw=4
