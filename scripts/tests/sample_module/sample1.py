"""
sample1 docstring

"""

def func1():
    """sample1.func1 docstrings"""
    pass

def func2():
    r"""sample1.func2 docstring

    quux
    \r
    """
    
    pass

def func3(a,
               b={1:
                  3, 4: 5},
               c=1, d="""foobar"""):
    pass

def func4(a,
               b='baz',
               c=123,
               ):        # foobar
    """sample1.func4 docstring docstring"""
    pass

def func5(a,
               b={3:
                  """Foo bar quux"""
                  },
               c=6
               ):
    "sample1.func5 docstring"
    pass
