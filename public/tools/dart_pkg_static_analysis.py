#!/usr/bin/env python
#
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility for static analysis test of dart packages generated by dart-pkg"""

import argparse
import errno
import json
import multiprocessing
import os
import shutil
import subprocess
import sys

DART_ANALYZE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "dart_analyze.py")

# List of analysis results.
result_list = []
def collect_result(result):
  result_list.append(result)

def analyze_entrypoints(dart_sdk, package_root, entrypoints):
  cmd = [ "python", DART_ANALYZE ]
  cmd.append("--dart-sdk")
  cmd.append(dart_sdk)
  cmd.append("--entrypoints")
  cmd.extend(entrypoints)
  cmd.append("--package-root")
  cmd.append(package_root)
  cmd.append("--no-hints")
  cmd.append("--show-sdk-warnings")
  try:
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    print('Failed analyzing %s' % entrypoints)
    print(e.output)
    return e.returncode
  return 0


def analyze_package(dart_sdk, package_root, package):
  package_name = package[0]
  package_entrypoints = package[1]
  print('Analyzing dart-pkg %s ' % package_name)
  return analyze_entrypoints(dart_sdk, package_root, package_entrypoints)

# Filter entrypoints for files that exist.
def filter_entrypoints(package_name, entrypoints):
  result = []
  for entrypoint in entrypoints:
    if os.path.isfile(entrypoint):
      result.append(entrypoint)
    else:
      print('WARNING: Could not find %s from %s ' % (entrypoint, package_name))
  return result

def main():
  parser = argparse.ArgumentParser(description='Generate a dart-pkg')
  parser.add_argument('--dart-sdk',
                      action='store',
                      metavar='dart_sdk',
                      help='Path to the Dart SDK.')
  parser.add_argument('--dart-pkg-dir',
                      action='store',
                      metavar='dart_pkg_dir',
                      help='Directory of dart packages',
                      required=True)
  parser.add_argument('--package-root',
                      metavar='package_root',
                      help='packages/ directory',
                      required=True)
  parser.add_argument('package_name',
                      nargs='?',
                      default=None)
  args = parser.parse_args()

  # Make sure we have a Dart SDK.
  dart_sdk = args.dart_sdk
  if dart_sdk is None:
    dart_sdk = os.environ.get('DART_SDK')
    if dart_sdk is None:
      print "Pass --dart-sdk, or define the DART_SDK environment variable"
      return 1

  jobs = []
  # Determine which packages to analyze
  for filename in os.listdir(args.dart_pkg_dir):
    if filename.endswith('.entries'):
      if not args.package_name or (filename == args.package_name + '.entries'):
        with open(os.path.join(args.dart_pkg_dir, filename)) as f:
            entrypoints = f.read().splitlines()
        package_name = os.path.splitext(filename)[0]
        entrypoints = filter_entrypoints(package_name, entrypoints)
        if entrypoints != []:
          jobs.append([package_name, entrypoints])

  # Create a process pool.
  pool = multiprocessing.Pool(multiprocessing.cpu_count())
  # Spawn jobs.
  for job in jobs:
    pool.apply_async(analyze_package,
                     args = (dart_sdk, args.package_root, job, ),
                     callback = collect_result)
  # Wait for them to complete.
  pool.close();
  pool.join();

  # Return the error code if any packages failed.
  for result in result_list:
    if result != 0:
      return result

  return 0

if __name__ == '__main__':
  sys.exit(main())