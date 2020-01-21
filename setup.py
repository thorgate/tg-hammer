#!/usr/bin/env python
import uuid
import sys

import hammer

try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


base_filename = 'base.txt' if sys.version_info[0] < 3 else 'base3.txt'

requirements = [str(ir.req) for ir in parse_requirements('requirements/%s' % base_filename, session=uuid.uuid1())]
test_requirements = [str(ir.req) for ir in parse_requirements('requirements/development.txt', session=uuid.uuid1())]

setup(
    name=hammer.hammer_name,
    version=hammer.__version__,
    description=hammer.__description__,
    long_description=open('README.md').read(),
    author='Thorgate',
    author_email='hi@thorgate.eu',
    url='https://github.com/thorgate/tg-hammer',
    packages=[
        'hammer',
    ],
    include_package_data=True,
    install_requires=requirements,
    test_suite='py.test',
    tests_require=test_requirements,
    license="BSD",
    keywords='tg-hammer hammer fabric vcs git hg',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
    ],
)
