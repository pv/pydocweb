#
   #
#
##

"""
Test module.


ju

"""

__all__ = ['Cls1', 'func4']

class Cls1(object):
    def __init__(self, a, b): pass
    def func1(self, q, b):
        pass
    def func2(self, q):
        """Cls1.func2 docstring
        
        \"\"\"
        """
        pass

class Cls2(
    Cls1,
           dict





           ):






    
        'sample2.Cls2 docstring'
        def func1(a, b):
            pass
        def func2(a, b, c):
            "sample2.Cls2.func2 docstring \
                                        \
                                        \
            "
            pass

def func4(a, b):
	"Quux docstring"
	pass

