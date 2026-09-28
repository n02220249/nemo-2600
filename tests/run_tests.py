#!/usr/bin/env python3
from tests.test_compiler import *

tests = [test_v064_exact_regression, test_v07_exact_regression, test_vectors_and_table]
for t in tests:
    t()
    print("PASS", t.__name__)
print("ALL TESTS PASS")
