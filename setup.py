#!/usr/bin/env python3
"""Setup configuration for Wildlife Graduate Position Intelligence Platform."""

from setuptools import find_packages, setup

setup(
    name="wildlife-grad-dashboard",
    use_scm_version=True,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
)
