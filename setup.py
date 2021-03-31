from setuptools import setup

# https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html
# From https://packaging.python.org/tutorials/packaging-projects/#configuring-metadata
setup(
    name="difflens-kubedzero",
    version="0.1",
    packages=["difflens", "difflens/util"],
    url="https://github.com/kubedzero/difflens",
    license="MIT",
    author="KZ",
    author_email="kubedzero@gmail.com",
    description="A package to compute, export, and analyze BLAKE3 file hashes and directory structures",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Operating System :: OS Independent"
    ],
    entry_points={"console_scripts": ["difflens = difflens.difflens:main"]},
    py_modules=["difflens/difflens"],
    install_requires=["psutil~=5.8.0", "pandas~=1.2.3", "blake3~=0.1.8"]
)
