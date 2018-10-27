import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wsnsimpy",
    version="0.1.2",
    author="Chaiporn Jaikaeo",
    author_email="chaiporn.j@ku.ac.th",
    description="SimPy-based WSN Simulator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/cjaikaeo/wsnsimpy",
    packages=setuptools.find_packages(),
    install_requires=[
        'simpy',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
)
