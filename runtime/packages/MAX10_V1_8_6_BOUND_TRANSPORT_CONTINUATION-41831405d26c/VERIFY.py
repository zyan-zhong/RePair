import sys,json
from resume_entry import verify
print('TRANSPORT_PACKAGE_SHA='+verify(),flush=True)
if '--server' in sys.argv:
    from server_checks import main
    main()
print('PROVIDER_SEND_COUNT=0',flush=True)
