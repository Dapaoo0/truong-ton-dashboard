import sys
import streamlit as st

# Mock streamlit before importing the page to avoid execution of st commands causing exits
class MockST:
    def __getattr__(self, name):
        def _mock(*args, **kwargs): return args[0] if args else None
        return _mock

import pages._2_Dinh_Muc_test
