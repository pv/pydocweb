from setuptools import setup, find_packages
setup(
    name = "pydocweb",
    version = "0.5.dev",
    author = "Pauli Virtanen",
    author_email = "pav@iki.fi",
    description = "Collaborative Python docstring editor on the web",
    url = "http://code.google.com/p/pydocweb/",
    include_package_data = True,
	packages = find_packages('pydocweb'),
	package_dir = {'': 'pydocweb'},
	install_requires = ['setuptools'],
)
