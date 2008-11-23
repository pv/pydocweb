"""
Unit tests for ToctreeCache functionality

"""
import os, sys, re
from django.test import TestCase
from django.conf import settings
from StringIO import StringIO
import lxml.etree as etree

import docweb.models as models

class TestToctree(TestCase):
    
    def test_simple_parsing(self):
        toc, code = models.ToctreeCache._parse_toctree_autosummary(TEST_TEXT)

        self.assertEqual(toc, "foo bar quux bar baz".split())

        for item in code:
            if item[1] == 'scipy.interpolate':
                self.assertEqual(item[0], '')
            else:
                self.assertEqual(item[0], 'scipy.interpolate.', item)

        names = """
        interp1d BarycentricInterpolator KroghInterpolator PiecewisePolynomial
        barycentric_interpolate krogh_interpolate
        piecewise_polynomial_interpolate interp2d Rbf UnivariateSpline
        InterpolatedUnivariateSpline LSQUnivariateSpline
        splrep splprep splev splint sproot spalde bisplrep bisplev
        BivariateSpline SmoothBivariateSpline LSQBivariateSpline
        bisplrep bisplev lagrange approximate_taylor_polynomial
        scipy.interpolate
        """.split()
        found_names = [item[1] for item in code]
        self.assertEqual(sorted(names), sorted(found_names))


TEST_TEXT = """
========================================
Interpolation (:mod:`scipy.interpolate`)
========================================

.. module:: scipy.interpolate

.. toctree::

   foo
   bar
   quux


Univariate interpolation
========================

.. autosummary::
   :toctree: generated/

   interp1d
   BarycentricInterpolator
   KroghInterpolator
   PiecewisePolynomial
   barycentric_interpolate
   krogh_interpolate
   piecewise_polynomial_interpolate


Multivariate interpolation
==========================

.. autosummary::
   :toctree: generated/

   interp2d
   Rbf


1-D Splines
===========

.. autosummary::
   :toctree: generated/

   UnivariateSpline
   InterpolatedUnivariateSpline
   LSQUnivariateSpline

Low-level interface to FITPACK functions:

.. autosummary::
   :toctree: generated/

   splrep
   splprep
   splev
   splint
   sproot
   spalde
   bisplrep
   bisplev


2-D Splines
===========

.. seealso:: scipy.ndimage.map_coordinates

.. autosummary::
   :toctree: generated/

   BivariateSpline
   SmoothBivariateSpline
   LSQBivariateSpline

Low-level interface to FITPACK functions:

.. autosummary::
   :toctree: generated/

   bisplrep
   bisplev

Additional tools
================

.. autosummary::
   :toctree: generated/

   lagrange
   approximate_taylor_polynomial

.. autosummary::

   not_linked_to_toctree

.. toctree::

   bar

   baz

"""

