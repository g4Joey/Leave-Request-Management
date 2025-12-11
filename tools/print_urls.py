import os
import django
from django.urls import URLPattern, URLResolver, get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
try:
    import sys
    # Ensure project root is in sys.path so the project module can be imported when running from the tools folder
    sys.path.insert(0, os.getcwd())
    django.setup()
except Exception as e:
    print('Django setup error:', e)

resolver = get_resolver()

found = []

def list_patterns(patterns, prefix=''):
    for p in patterns:
        if isinstance(p, URLPattern):
            path = prefix + str(p.pattern)
            print(path)
            if 'export' in path or 'requests' in path:
                found.append(path)
        elif isinstance(p, URLResolver):
            new_prefix = prefix + str(p.pattern)
            print(new_prefix + ' -> include')
            list_patterns(p.url_patterns, new_prefix)

list_patterns(resolver.url_patterns)

print('\n-- Matches (containing export or requests) --')
for f in found:
    print(f)

# Try resolving specific paths to see which view is bound
for test_path in ['/api/leaves/requests/export_all/', '/api/leaves/manager/export_all/']:
    try:
        match = resolver.resolve(test_path)
        print('\nResolved:', test_path)
        print('func:', match.func)
        print('args:', match.args)
        print('kwargs:', match.kwargs)
    except Exception as e:
        print('\nCould not resolve', test_path, '-', e)
