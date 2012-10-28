'''
Encoding converter plugin for gedit application
Copyright (C) 2009  Alexey Kuznetsov <ak@axet.ru>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import codecs

class DocHelper:

  doc = None
  enc = None

  def __init__(self, doc, enc = None):
    self.doc = doc

    if(enc == None):
      enc = doc.get_encoding()
    self.enc = enc

  def read_all(self):
    start, end = self.doc.get_bounds()
    text = self.doc.get_text(start, end)

    return text

  def replace_new(self, text):
    start, end = self.doc.get_bounds()

    self.doc.begin_user_action()

    it = self.doc.get_iter_at_mark(self.doc.get_insert())
    line = it.get_line()
    self.doc.delete(start, end)
    self.doc.insert(start, text)
    self.doc.goto_line(line)

    self.doc.end_user_action()

  def recode_text(self, fromEnc, toEnc, text):
    currentencoder = codecs.lookup(fromEnc)[0]

    utf8decoder = codecs.lookup('utf-8')[1]
    windecoder = codecs.lookup(toEnc)[1]
    utf8encoder = codecs.lookup('utf-8')[0]

    text = utf8decoder(text)[0]
    text = currentencoder(text)[0]
    text = windecoder(text)[0]
    text = utf8encoder(text)[0]

    return text

  def recode_doc(self, toEnc):
    text = self.read_all()
    enc = self.enc.get_charset()
    text = self.recode_text(enc, toEnc, text)
    self.replace_new(text)
