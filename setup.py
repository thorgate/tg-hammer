#!/usr/bin/env python
import uuid

import hammer

from pip.req import parse_requirements

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


requirements = [str(ir.req) for ir in parse_requirements('requirements/base.txt', session=uuid.uuid1())]
test_requirements = [str(ir.req) for ir in parse_requirements('requirements/development.txt', session=uuid.uuid1())]

setup(
    name=hammer.__name__,
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
