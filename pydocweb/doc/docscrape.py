"""Extract reference documentation from the NumPy source tree.

"""

import inspect
import textwrap
import re
from StringIO import StringIO

class Reader(object):
    """A line-based string reader.

    """
    def __init__(self, data):
        """
        Parameters
        ----------
        data : str
           String with lines separated by '\n'.

        """
        if isinstance(data,list):
            self._str = data
        else:
            self._str = data.split('\n') # store string as list of lines

        self.reset()

    def __getitem__(self, n):
        return self._str[n]

    def reset(self):
        self._l = 0 # current line nr

    def read(self):
        if not self.eof():
            out = self[self._l]
            self._l += 1
            return out
        else:
            return ''

    def seek_next_non_empty_line(self):
        for l in self[self._l:]:
            if l.strip():
                break
            else:
                self._l += 1

    def eof(self):
        return self._l >= len(self._str)

    def read_to_condition(self, condition_func):
        start = self._l
        for line in self[start:]:
            if condition_func(line):
                return self[start:self._l]
            self._l += 1
            if self.eof():
                return self[start:self._l+1]
        return []

    def read_to_next_empty_line(self):
        self.seek_next_non_empty_line()
        def is_empty(line):
            return not line.strip()
        return self.read_to_condition(is_empty)

    def read_to_next_unindented_line(self):
        def is_unindented(line):
            return (line.strip() and (len(line.lstrip()) == len(line)))
        return self.read_to_condition(is_unindented)

    def peek(self,n=0):
        if self._l + n < len(self._str):
            return self[self._l + n]
        else:
            return ''

    def is_empty(self):
        return not ''.join(self._str).strip()


class NumpyDocString(object):
    def __init__(self,docstring):
        docstring = docstring.split('\n')

        # De-indent paragraph
        try:
            indent = min(len(s) - len(s.lstrip()) for s in docstring
                         if s.strip())
        except ValueError:
            indent = 0

        for n,line in enumerate(docstring):
            docstring[n] = docstring[n][indent:]

        self._doc = Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': '',
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'See Also': [],
            'Notes': [],
            'References': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def __getitem__(self,key):
        return self._parsed_data[key]

    def __setitem__(self,key,val):
        if not self._parsed_data.has_key(key):
            raise ValueError("Unknown section %s" % key)
        else:
            self._parsed_data[key] = val

    def _is_at_section(self):
        self._doc.seek_next_non_empty_line()

        if self._doc.eof():
            return False

        l1 = self._doc.peek().strip()  # e.g. Parameters

        if l1.startswith('.. index::'):
            return True

        l2 = self._doc.peek(1).strip() #    ----------
        return (len(l1) == len(l2) and l2 == '-'*len(l1))

    def _strip(self,doc):
        i = 0
        j = 0
        for i,line in enumerate(doc):
            if line.strip(): break

        for j,line in enumerate(doc[::-1]):
            if line.strip(): break

        return doc[i:len(doc)-j]

    def _read_to_next_section(self):
        section = self._doc.read_to_next_empty_line()

        while not self._is_at_section() and not self._doc.eof():
            if not self._doc.peek(-1).strip(): # previous line was empty
                section += ['']

            section += self._doc.read_to_next_empty_line()

        return section

    def _read_sections(self):
        while not self._doc.eof():
            data = self._read_to_next_section()
            name = data[0].strip()

            if name.startswith('..'): # index section
                yield name, data[1:]
            elif len(data) < 2:
                yield StopIteration
            else:
                yield name, self._strip(data[2:])

    def _parse_param_list(self,content):
        r = Reader(content)
        params = []
        while not r.eof():
            header = r.read().strip()
            if ' : ' in header:
                arg_name, arg_type = header.split(' : ')[:2]
            else:
                arg_name, arg_type = header, ''

            desc = r.read_to_next_unindented_line()
            for n,line in enumerate(desc):
                desc[n] = line.strip()
            desc = desc #'\n'.join(desc)

            params.append((arg_name,arg_type,desc))

        return params

    def _parse_index(self, section, content):
        """
        .. index: default
           :refguide: something, else, and more

        """
        def strip_each_in(lst):
            return [s.strip() for s in lst]

        out = {}
        section = section.split('::')
        if len(section) > 1:
            out['default'] = strip_each_in(section[1].split(','))[0]
        for line in content:
            line = line.split(':')
            if len(line) > 2:
                out[line[1]] = strip_each_in(line[2].split(','))
        return out

    def _parse(self):
        self._doc.reset()

        # grab signature (if given) and summary
        summary = self._doc.read_to_next_empty_line()
        if len(summary) == 1 and \
               re.compile('^[\w\.]+\(.*\)$').match(summary[0].strip()):
            self['Signature'] = summary[0]
            if not self._is_at_section():
                self['Summary'] = self._doc.read_to_next_empty_line()
        else:
            self['Summary'] = summary

        if not self._is_at_section():
            self['Extended Summary'] = self._read_to_next_section()

        for (section,content) in self._read_sections():
            if not section.startswith('..'):
                section = ' '.join([s.capitalize() for s in section.split(' ')])
            if section in ('Parameters','Returns','Raises','Warns'):
                self[section] = self._parse_param_list(content)
            elif section.startswith('.. index::'):
                self['index'] = self._parse_index(section, content)
            else:
                self[section] = content

    # string conversion routines

    def _str_header(self, name, symbol='-'):
        return [name, len(name)*symbol]

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        return [self['Signature'].replace('*','\*')] + ['']

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Extended Summary'] + ['']

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            for param,param_type,desc in self[name]:
                out += ['%s : %s' % (param, param_type)]
                out += self._str_indent(desc)
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += self[name]
            out += ['']
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            out += ['   :%s: %s' % (section, ', '.join(references))]
        return out

    def __str__(self):
        out = []
        out += self._str_signature()
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters','Returns','Raises'):
            out += self._str_param_list(param_list)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
        out += self._str_index()
        return '\n'.join(out)


def indent(str,indent=4):
    indent_str = ' '*indent
    if str is None:
        return indent_str
    lines = str.split('\n')
    return '\n'.join(indent_str + l for l in lines)

def header(text, style='-'):
    return text + '\n' + style*len(text) + '\n'


class SphinxDocString(NumpyDocString):
    # string conversion routines
    def _str_header(self, name, symbol='`'):
        return ['**' + name + '**'] + [symbol*(len(name)+4)]

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        return ['``%s``' % self['Signature'].replace('*','\*')] + ['']

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Extended Summary'] + ['']

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += ['']
            for param,param_type,desc in self[name]:
                out += self._str_indent(['**%s** : %s' % (param, param_type)])
                out += ['']
                out += self._str_indent(desc,8)
                out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += ['']
            content = self._str_indent(self[name])
            out += content
            out += ['']
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            out += ['   :%s: %s' % (section, ', '.join(references))]
        return out

    def __str__(self, indent=0):
        out = []
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters','Returns','Raises'):
            out += self._str_param_list(param_list)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
#        out += self._str_index()
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class FunctionDoc(object):
    def __init__(self,func):
        self._f = func

    def __str__(self):
        out = ''
        doclines = inspect.getdoc(self._f) or ''
        try:
            doc = SphinxDocString(doclines)
        except Exception, e:
            print '*'*78
            print "ERROR: '%s' while parsing `%s`" % (e, self._f)
            print '*'*78
            #print "Docstring follows:"
            #print doclines
            #print '='*78
            return out

        if doc['Signature']:
            out += '%s\n' % header('**%s**' %
                                   doc['Signature'].replace('*','\*'), '-')
        else:
            try:
                # try to read signature
                argspec = inspect.getargspec(self._f)
                argspec = inspect.formatargspec(*argspec)
                argspec = argspec.replace('*','\*')
                out += header('%s%s' % (self._f.__name__, argspec), '-')
            except TypeError, e:
                out += '%s\n' % header('**%s()**'  % self._f.__name__, '-')

        out += str(doc)
        return out


class ClassDoc(object):
    def __init__(self,cls,modulename=''):
        if not inspect.isclass(cls):
            raise ValueError("Initialise using an object")
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename
        self._name = cls.__name__

    @property
    def methods(self):
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and callable(func)]

    def __str__(self):
        out = ''

        def replace_header(match):
            return '"'*(match.end() - match.start())

        for m in self.methods:
            print "Parsing `%s`" % m
            out += str(FunctionDoc(getattr(self._cls,m))) + '\n\n'
            out += '.. index::\n   single: %s; %s\n\n' % (self._name, m)

        return out


