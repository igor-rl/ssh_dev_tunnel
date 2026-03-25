from setuptools import setup, find_packages

setup(
    name="ssh-dev-tunnel",
    version="3.3",
    author="Igor Lage",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'tunnel=src.main:main',
        ],
    },
)