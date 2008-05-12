"""
test1 docstring

"""

def test_func1():
    pass

def test_func2():
    r"""test1.func2 docstring

    quux
    \r
    """
    
    pass

def test_func3(a,
               b={1:
                  3, 4: 5},
               c=1, d="""foobar"""):
    pass

def test_func4(a,
               b='baz',
               c=123,
               ):        # foobar
    """test1.test_func4 docstring docstring"""
    pass

def test_func5(a,
               b={3:
                  """Foo bar quux"""
                  },
               c=6
               ):
    "test.test_func5 docstring"
    pass
