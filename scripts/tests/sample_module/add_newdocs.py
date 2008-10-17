
def add_newdoc(modname, place, doc):
    ns = {}
    exec "from %s import %s" % (modname, place) in ns
    if isinstance(doc, str):
        ns[place].__doc__ = doc
    else:
        setattr(ns[place], doc[0], doc[1])

add_newdoc('sample_module.sample3', 'func0',
           """
           func0 docstring
           """)

add_newdoc('sample_module.sample3', 'Cls4', ('func1',
           "sample_module.sample3.Cls4.func1 docstring"))


add_newdoc('sample_module.sample3',
           'Cls4', ('func2', """
    sample_module.sample3.Cls4.func2 docstring

    """))
