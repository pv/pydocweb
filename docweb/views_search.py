from pydocweb.docweb.utils import *
from pydocweb.docweb.models import *

#------------------------------------------------------------------------------
# Search
#------------------------------------------------------------------------------

class SearchForm(forms.Form):
    _choices = [('any', 'Anything'),
                ('wiki', 'Wiki page'),
                ('module', 'Module'),
                ('class', 'Class'),
                ('callable', 'Callable'),
                ('object', 'Object')]
    fulltext = forms.CharField(required=False,
            help_text="Use % as a wild characted; as in an SQL LIKE search")
    invert = forms.BooleanField(required=False,
            help_text="Find non-matching items")
    type_code = forms.CharField(widget=forms.Select(choices=_choices),
                                label="Item type")

def search(request):
    docstring_results = []
    wiki_results = []

    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data['fulltext'] != '':
                data['fulltext'] = '%%%s%%' % data['fulltext']
            if data['type_code'] != 'wiki':
                docstring_results = Docstring.fulltext_search(
                    data['fulltext'], data['invert'], data['type_code'])
            if data['type_code'] in ('any', 'wiki'):
                wiki_results = WikiPage.fulltext_search(data['fulltext'],
                                                        data['invert'])
    else:
        form = SearchForm()

    return render_template(request, 'search.html',
                           dict(form=form,
                                docstring_results=docstring_results,
                                wiki_results=wiki_results))

