from pathlib import Path
import unittest
suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern='test_*.py')
raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
