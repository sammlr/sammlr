"""Compatibility entrypoint: PAX-04 intentionally replaces the extra-open/list UX.
The current gate retains 16/20 boundaries, fixture, isolation and fan checks.
Historical PAX-01–03 screenshots and audit remain unchanged.
"""
from check_pax_04 import main

if __name__ == '__main__':
    main()
