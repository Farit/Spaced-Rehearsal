#!/usr/bin/env python3.6

import os
import os.path
import site


def run():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    site.addsitedir(project_dir)
    # Change the scripts working directory to the script's own directory,
    # so that relative paths will work.
    os.chdir(project_dir)

    from src.app import SpacedRehearsal
    spaced_rehearsal = SpacedRehearsal()
    spaced_rehearsal.run()


if __name__ == '__main__':
    run()
