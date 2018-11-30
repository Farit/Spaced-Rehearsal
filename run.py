#!/usr/bin/env python3.6

import os
import os.path
import argparse
import logging.config
import site

project_dir = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(project_dir)

# Change the scripts working directory to the script's own directory,
# so that relative paths will work.
os.chdir(project_dir)

from src.app import SpacedRehearsal
from src.mediator import get_mediator, list_mediators
from src.utils import log_config_as_dict


logging.config.dictConfig(log_config_as_dict)

parser = argparse.ArgumentParser()
parser.add_argument(
    '--mediator',
    choices=list_mediators(),
    required=True
)
args = parser.parse_args()

spaced_rehearsal = SpacedRehearsal(
    mediator=get_mediator(name=args.mediator)
)
spaced_rehearsal.run()
