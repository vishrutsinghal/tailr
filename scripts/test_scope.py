import sys
sys.path.insert(0, r'D:\PD\tailr-main\tailtrail\scripts')
from scripts.navigator_scope import requested_scope_mode

# Test cases from TT-CUR-05 acceptance criteria
tests = [
    ('add new test cases', 'test-only'),
    ('create E2E scenarios', 'test-only'),
    ('tests only', 'test-only'),
    ('implement an endpoint and add tests', 'code-change'),
    ('add regression test', 'test-only'),
    ('test coverage only', 'test-only'),
]

for goal, expected in tests:
    result = requested_scope_mode(goal, [])
    status = 'OK' if result == expected else 'FAIL'
    print(f'{status} "{goal}" -> {result} (expected: {expected})')