========
7bm-tomo
========

**tomo** is command-line-interface for running tomographic scans at beamline `beamline 7-BM <https://7bm-docs.readthedocs.io>`_ of the `Advanced Photon Source <https://www.aps.anl.gov/>`_
This is based on the command-line scripts authored by Francesco De Carlo for use at the 2-BM beamline of the APS.

Installation
============

::

    $ git clone https://github.com/aps-7bm/7bm-tomo.git
    $ cd 7bm-tomo
    $ python setup.py install

in a prepared virtualenv or as root for system-wide installation.

.. warning:: If your python installation is in a location different from #!/usr/bin/env python please edit the first line of the bin/tomo file to match yours.

Usage
=====

Running a scan
--------------

To run a tomographic scan::

    $ tomo scan

from the command line. To get correct results, you may need to set specific
options, for example to collect 10 tomographic dataset at 10 vertical positions separated by 1 mm::

    $ tomo scan --scan-type vertical --vertical-scan-start 0 --vertical-scan-end 10 --vertical-scan-step-size 1

to list of all available options::

    $ tomo scan -h


Configuration File
------------------

Scanning parameters are stored in **tomo7bm.conf**. You can create a template with::

    $ tomo init

**tomo2bm.conf** is constantly updated to keep track of the last stored parameters, as initalized by **init** or modified by setting a new option value. For example to re-run the last scan with identical parameters just use::

    $ tomo scan

A the end of each scan the current config file is copied in the raw data directory and renamed as **sample_name.conf**. To repeat the scan with the same condition just use::

    $ tomo scan --config /data_folder/sample_name.conf
