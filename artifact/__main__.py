import artifact
import sys
# replace "__main__.py" in sys.argv[0] with more useful info
# to be displayed in usage hint when printing the help
if sys.argv[0].endswith("__main__.py"):
    import os.path
    executable = os.path.basename(sys.executable)
    sys.argv[0] = executable + " -m artifact"
    del os

artifact.main()
