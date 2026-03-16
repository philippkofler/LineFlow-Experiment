import unittest
from lineflow_ef import Seq_Pro_Assembly


class TestRun(unittest.TestCase):
    def test_run(self):

        line = Seq_Pro_Assembly()
        line.run(1_000)
