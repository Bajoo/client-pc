#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Entry Point for the executable.

This file is used by setup.py, during the build_esky phase.
"""

import sys

import bajoo

if __name__ == "__main__":
    sys.exit(bajoo.main())
