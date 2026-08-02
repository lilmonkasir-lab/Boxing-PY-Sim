#!/usr/bin/env python3
"""Entry point:  python main.py  [--difficulty Champion] [--rounds 3] ..."""
import sys

from boxing_sim.app import main

if __name__ == "__main__":
    sys.exit(main())
