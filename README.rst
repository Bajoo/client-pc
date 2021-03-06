Bajoo client
============

Official client for the cloud storage service Bajoo.

Bajoo is a service which lets you store your files in the cloud, and share them
into multiples devices and multiples users.
All files are encrypted client-side (before being sent to the bajoo servers)
with your secret phrase you're the only one to know.

This client is a graphic program aimed to interact with the bajoo service. It
can synchronize local folders with files stored in the Bajoo cloud.

For more details, see https://www.bajoo.fr


Installation from source
------------------------

Bajoo can run on Python 2.7 or Python 3.4 and higher. However, it's recommended to use the Python2 version.

- Ubuntu with Python2.7:

  Uses the packaged version of wxpython (classic version).

  .. code-block:: bash

     sudo apt-get install python-pip python-wxgtk3.0 build-essential python-dev libssl-dev libffi-dev python-dbus

     # For Unity only; You don't need these packages if you use another DE (eg: XFCE)
     sudo apt-get install python-gi gir1.2-appindicator3-0.1 libappindicator3-1

     sudo pip2 install .

- Ubuntu with Python3.4+

  Uses the last nightly version of wxpython (Phoenix).

  .. code-block:: bash

    sudo apt-get install python3-pip build-essential python3-dev libssl-dev libffi-dev libgtk-3-dev python3-dbus mesa-common-dev libglu1-mesa-dev libgstreamer0.10-dev libgstreamer-plugins-base0.10-dev libgtk2.0-dev libwebkitgtk-dev

    # For Unity only; You don't need these packages if you use another DE (eg: XFCE)
    sudo apt-get install python3-gi gir1.2-appindicator3-0.1 libappindicator3-1

    sudo pip3 install --process-dependency-links --allow-unverified wxpython --trusted-host wxpython.org .

License and copyright
---------------------

Copyright © 2015-2016 Bajoo

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.

Contact
-------

If you have bug reports, comments, questions, or just want to share a word
with us, feel free to contact us at support-fr@bajoo.fr (in french) or 
support-en@bajoo.fr (english).
We'll be happy to discuss this with you!
We don't bite and neither Bajoo does.
