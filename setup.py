from setuptools import setup, find_packages

setup(
    name="ssh-dev-tunnel",
    version="3.6.22",
    author="Igor Lage",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # keyring removido: o vault agora usa base64 interno,
        # sem dependência de sistema de chaveiro do OS.
    ],
    entry_points={
        'console_scripts': [
            'tunnel=src.main:main',
        ],
    },
)