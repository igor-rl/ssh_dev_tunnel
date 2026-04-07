from setuptools import setup, find_packages

setup(
    name="ssh-dev-tunnel",
    version="3.6.10",
    author="Igor Lage",
    packages=find_packages(),
    install_requires=[
        "keyring",
    ],
    entry_points={
        'console_scripts': [
            'tunnel=src.main:main',
        ],
    },
)