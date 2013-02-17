import sys, os
import unittest

import docweb.models as models

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
upgrader = __import__('upgrade-schema')
sys.path.pop(0)

INITIAL_SQL = os.path.join(os.path.dirname(__file__), 'db-0.1-dump.sql')

class TestDatabaseUpgrade(unittest.TestCase):

    def setUp(self):
        # Load 0.1 schema
        upgrader.run_sql(INITIAL_SQL, verbose=False)

    def test_upgrade(self):
        # Upgrade it to current schema version
        upgrader.upgrade(verbose=False)

        # Perform some minor checks
        schema = models.DBSchema.objects.all()
        assert len(schema) == 1

        doc = models.Docstring.on_site.get(name='numpy.lib.function_base.hamming')
        assert doc.text.startswith('Return the Hamming window.')
        revs = doc.revisions.all()
        assert revs[0].revno == 113
        assert revs[1].revno == 108
        assert revs[2].revno == 21

        page = models.WikiPage.on_site.get(name='Front Page')
        revs = page.revisions.all()

if __name__ == "__main__":
    unittest.main()
