from setuptools import setup, find_packages

setup(
    name="ssh-dev-tunnel",
    version="3.9.0",
    author="Igor Lage",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        # keyring: usa o Keychain/Credential Manager do SO quando disponível.
        # cryptography: fallback (arquivo local criptografado) quando não há
        # backend de keyring no sistema.
        "keyring>=24",
        "cryptography>=42",
    ],
    entry_points={
        'console_scripts': [
            'tunnel=src.main:main',
        ],
    },
)