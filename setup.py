#  Copyright (C) 2013 Matt Hagy <hagy@gatech.edu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

name = 'jamenson'
version = '0.0.1'

from distutils.core import setup

setup(
    name=name,
    version=version,
    url='https://github.com/matthagy/Jamenson',
    author='Matt Hagy',
    author_email='hagy@gatech,.edu',
    description='Scheme compiler and runtime for Python',
    long_description='''
Jamenson is a robust scheme implementation, including a full runtime, compiler, and
libraries, for the Python programming language. This language allows Python programmers
to write select portions of their applications in a scheme dialect using our many cherished
lispy features; i.e. code-as-data and macros. Additionally, with the its feature-full
optimizing compiler, Jamenson code runs atop the Python virtual machine and is commonly more
efficient than comparable Python code. Current uses include code generators, such as a pattern
matching compiler to transform declarative languages into efficient implementation functions.
Future plans include partial static type analysis with the aim of compiling to machine code
via an external c-compiler. Your comments and contributions are always more than welcome. 
    ''',
    classifiers = [
    "Development Status :: 1 - Planning",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    ],
    packages = ['jamenson'],
    )
