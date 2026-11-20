"""All tests of the recall hooks (delegation, decision capture, flags capture, the shared helpers).
Run: python -I scripts/recall/tests/run_tests.py [module-name ...]   (exit 1 if any fails; no real brain call is made)"""
import os, sys, tempfile, unittest

os.environ["RECALL_VERDICT_LOG"] = os.path.join(tempfile.mkdtemp(), "gate_verdicts.jsonl")  # the tests never write the real verdict log
os.environ["RECALL_SHADOW_LOG"] = os.path.join(tempfile.mkdtemp(), "shadow_select.jsonl")  # nor the shadow-select log
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
names = sys.argv[1:] or sorted(f[:-3] for f in os.listdir(HERE) if f.startswith("test_") and f.endswith(".py"))
r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
sys.exit(0 if r.wasSuccessful() else 1)
