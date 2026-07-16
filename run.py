#!/usr/bin/env python3
"""启动入口:python run.py 或 uvicorn app.server:app"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.server import app, main

if __name__ == "__main__":
    main()
