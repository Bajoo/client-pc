#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup


# Load the __version__ variable
exec(open('bajoo/__version__.py').read())


with open('README.rst') as readme_file:
    long_description = readme_file.read()


setup(
    name="bajoo",
    version=__version__,
    description="Official client for the cloud storage service Bajoo",
    long_description=long_description,
    url="https://www.bajoo.fr",
    author="Bajoo",
    author_email="support@bajoo.fr",
    license="GPLv3",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Communications :: File Sharing"
    ],
    keywords="bajoo storage cloud file-sharing",
    packages=find_packages(),
    install_requires=[],
    include_package_data=True,
    package_data={},
    entry_points={
        "console_scripts": [
            "bajoo=bajoo:main"
        ]
    },
    zip_safe=True
)
