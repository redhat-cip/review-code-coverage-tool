review-code-coverage-tool
=========================

This tool runs the run_tests.sh and lists the not covered newly added/modified lines number for the given review_id or review_url.

Usage:
======

	review-code-coverage.py [-h] [--work_dir WORK_DIR] review_id

        positional arguments:
            review_id            review id or review url

        optional arguments:
            -h, --help           show this help message and exit
            --work_dir WORK_DIR  defaults to /tmp/tmp

Example:
========
	./review-code-coverage.py 76113 --work_dir='/home/test'

Sample Output:
==============

+----------------------------+------------------------+
|         File Name          | Not executed lines No. |
+----------------------------+------------------------+
| cinderclient/exceptions.py |       [151, 152]       |
|   cinderclient/client.py   |         [193]          |
+----------------------------+------------------------+



