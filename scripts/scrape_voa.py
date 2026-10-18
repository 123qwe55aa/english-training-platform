#!/usr/bin/env python3
"""Standalone entry point; uses configured lesson URLs and Django import validation.
Example: .venv/bin/python scripts/scrape_voa.py --start 1 --end 12 --publish
"""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.core.management import execute_from_command_line
execute_from_command_line([sys.argv[0],'import_voa',*sys.argv[1:]])
