from setuptools import setup
import subprocess


def commit_count():
    return str(
        subprocess.check_output('git rev-list head --count'),
        'ascii'
    ).strip()


setup(
    name='dsa-extras',
    version=f'{commit_count()}',
    author='Paulette S. Serrano',
    author_email='paulette.s.serrano@gmail.com',
    description='GBAFE Definitions and Utilities for DSA',
    packages=['dsa_extras'],
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Free To Use But Restricted',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            'nmm2dsa=dsa_extras.nmm2dsa:nmm2dsa.invoke'
        ]
    }
)
