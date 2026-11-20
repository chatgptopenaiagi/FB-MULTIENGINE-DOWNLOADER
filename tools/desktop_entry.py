import sys
from fbmd.cli import main as cli_main
from fbmd.gui import main as gui_main

if len(sys.argv) > 1:
    raise SystemExit(cli_main())
gui_main()
