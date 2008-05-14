
def add_newdoc(a, b, c): pass

func0 = lambda x: x
func0.__name__ = "func0"

class Cls4(object):
    func1 = lambda x: x
    func1.__name__ = "func1"
    func2 = lambda x: x
    func2.__name__ = "func2"

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
