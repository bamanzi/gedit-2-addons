#!/usr/bin/env python
#-*- coding:utf-8 -*-
#

import gtk
import gio
import os
from subprocess import Popen, PIPE
from random import randint



FIXED_PARAMS = [ \
    'FALSE', 'False', 'false', \
    'TRUE', 'True', 'true', \
    'None', \
    'NULL', 'Null', 'null']


DOC_DELIMITERS = ' \t,.():=+-*/[]'




def first_valid_char(line):
    c = 0
    while c < len(line):
        if line[c] == ' ' or line[c] == '\t':
            c += 1
            continue
        break
    return c


def strip_and_get_indent(line):
    c = first_valid_char(line)
    return line.strip(), line[0:c]



# ex.: extract_words( s, "", ",:=()", '"' )
#
def extract_words(p, separators, separators_include, connectors):
    if not(' ' in separators_include) and not(' ' in connectors):
        separators += ' '
    if not('\t' in separators_include) and not('\t' in connectors):
        separators += '\t'
    if not('\n' in separators_include) and not('\n' in connectors):
        separators += '\n'

    resp = []
    s = ""
    i = 0
    while i < len(p):
        ch = p[i]
        if ch in connectors:
            j = i + 1
            while j < len(p):
                ch2 = p[j]
                if ch2 in connectors:
                    break
                j += 1

            s = p[i:j+1]
            resp.append( s )
            s = ""
            i = j + 1
            continue

        in_sep = ch in separators
        in_sep_inc = ch in separators_include

        if in_sep or in_sep_inc:
            if len(s) > 0:
                resp.append( s )
                s = ""
            if in_sep_inc:
                resp.append( ch )
            i += 1
            continue

        s += ch
        i += 1

    if len(s) > 0: resp.append( s )
    return resp




def format_doc(s, keywords, params):
    params = extract_words( params[1:-1].strip(), ',', '', '' ) + FIXED_PARAMS

    s2 = ""
    for line in s.split('\n'):
        if line.strip() == '' and s2 == "":
            continue
        
        line = format_doc_line(line, keywords, params)
        s2 += line + '\n'
    return s2[:-1]


def format_doc_line(line, keywords, params):
    line, indent = strip_and_get_indent(line)
    if len(line) == 0: return ""
    
    if line[0:2] == '- ':
        line = '• ' + line[2:]
    
    termos = extract_words( line, '', DOC_DELIMITERS, '' )
    for i in range( len(termos) ):
        termo = termos[i]
        if termo in params:
            termos[i] = "<b>%s</b>" % termo        
        elif termo in keywords:
            termos[i] = "<tt><a href='%s'>%s</a></tt>" % (termo, termo)
    
    s = ""
    for termo in termos: s += termo
    return indent + s




def parse_items_from_ctags(code, lang):
    tmp = '/tmp/gedit.%s.python-defs.%d.tmp' % (os.getlogin(), randint(1,5))

    f = open( tmp, 'w' )
    f.write(code)
    f.close()
    
    cmd = 'ctags --language-force=%s --fields=Kn -f - %s' % (lang, tmp)
    p = Popen( shell=True, args = cmd, stdin=PIPE, stdout=PIPE )
    p.stdin.write( code )
    p.stdin.close()
    resp = p.stdout.read()
    p.stdout.close()

    items = []
    for line in resp.split('\n'):
        # ex.: 'func<tab>test 1.c<tab>/^int func()$/;"<tab>function<tab>line:4
        
        line = line.strip()
        if len(line) == 0: continue

        p1, p2 = line.split(';"\t')
        termos = p1.split('\t')
        nome, arq = termos[0:2]
        expr = '\t'.join( termos[2:] )
        kind, line = p2.split('\t')

        if expr[0:2] == '/^': expr = expr[2:]
        if expr[-2:] == '$/': expr = expr[:-2]
        line = int(line[5:])
        
        p1 = expr.find('(')
        p2 = expr.rfind(')')
        if p1 != -1 and p2 != -1:
            params = expr[p1:p2+1]
            if params == "()": params = "( )"
        else:
            params = ""
        
        if kind == 'function':
            items.append( ['p', nome, line, expr, params] )
    
    os.remove( tmp )
    return items




class CodeAnalyser:
    def __init__(self):
        self.items = []
        # [type: 'p' (proc), 'c' (class), name, line number, doc (None), params (None) ]
    
    
    def from_gedit_document(self, doc):
        start, end = doc.get_bounds()
        code = doc.get_text( start, end )
        
        lg = doc.get_language()
        lang = lg.get_id() if lg != None else None

        self.from_code( code, lang )


    def from_file(self, filename):
        f = open( filename )
        code = f.read()
        f.close()
        
        ext = os.path.splitext( filename )[1].lower()
        if ext == '.c': lang = 'c'
        elif ext == '.cpp' or ext == '.h': lang = 'c++'
        elif ext == '.py': lang = 'python'
        else: lang = None
        
        self.from_code( code, lang )
    
    
    def from_code(self, code, lang):
        if lang == 'c' or lang == 'c++':
            self.items = parse_items_from_ctags(code, lang)
        elif lang == 'python':
            self.parse_items_from_python_code(code)
    
        
    
    def parse_items_from_python_code(self, code):
        prev_line_was_def = False
        inside_doc = False
        doc = ""
        pre_line = None

        lines = code.split('\n')
        for line_num in range( len(lines) ):
            line_text, indent = strip_and_get_indent( lines[ line_num ] )
            
            if line_text[0:3] == '"""':
                inside_doc = not inside_doc
                if inside_doc:
                    doc = indent + line_text[3:]
                    if doc[-3:] == '"""':
                        doc = doc[:-3]
                        self.add_doc(doc)
                        doc = ""
                else:
                    self.add_doc(doc)
                    doc = ""
                                
            elif inside_doc:
                if line_text[-3:] == '"""':
                    doc += "\n" + indent + line_text[:-3]
                    self.add_doc(doc)
                    doc = ""
                    inside_doc = False
                else:
                    doc += "\n" + indent + line_text
                
            else:
                # connect lines ending with '\' for one unified "big line text".
                # obs.: string[-1] needs the last char; string[-1:] returns '' if empty.
                #
                if line_text[-1:] == '\\':
                    if pre_line == None:    pre_line = line_text[:-1]
                    else:                   pre_line += line_text[:-1]
                else:
                    if pre_line != None:
                        line_text = pre_line + line_text
                        pre_line = None
                        
                    if len(line_text) != 0 and line_text[0] != "#":
                        if  self.try_proc( line_text, line_num ) or \
                            self.try_class( line_text, line_num ):
                                prev_line_was_def = True
                        elif prev_line_was_def and self.try_doc( line_text, line_num ):
                            pass
                        else:
                            prev_line_was_def = False



    def try_proc(self, lin, lin_num):
        if lin[:4] == 'def ':
            p = lin.find( "(", 4 )
            if p != -1:
                proc_name = lin[4:p].strip()
                params = lin[p:-1].strip()
                
                wp = params[1:-1].strip()
                if wp[0:4] == 'self':
                    wp = wp[4:].strip()
                    if wp[0:1] == ',':
                        wp = wp[1:].strip()
                    if wp == '':
                        params = '( )'
                    else:
                        params = '( ' + wp + ' )'
                
                self.items.append( ['p', proc_name, lin_num, None, params] )
                return True
        return False


    def try_class(self, lin, lin_num):
        if lin[:6] == 'class ':
            p1 = lin.find( "(", 5 )
            p2 = lin.find( ":", 5 )
            if p1 == -1 and p2 != -1:
                p = p2
            elif p1 != -1 and p2 == -1:
                p = p1
            elif p1 != -1 and p2 != -2:
                p = min( p1, p2 )
            else:
                return False
            class_name = lin[6:p].strip()
            self.items.append( ['c', class_name, lin_num, None, None] )
            return True
        return False


    def try_doc(self, lin, lin_num):
        if lin[0] == '"' or lin[0] == "'":
            doc = ""
            ch = lin[0]
                        
            ok = False
            i = 1
            while i < len(lin):
                if lin[i] == ch and lin[i-1] != '\\':
                    ok = True
                    break
                i += 1
            
            if ok:
                doc = lin[1:i]
                self.add_doc(doc)
                return True            
        return False



    def add_doc(self, doc):
        if len(self.items) == 0:
            return
        it = self.items[-1]
        if it[3] == None:
            
            doc_lines = doc.split('\n')
            s = ""

            first_indent_n = first_valid_char( doc_lines[0] )
            for line in doc_lines:
                line, indent = strip_and_get_indent( line )
                indent = indent[first_indent_n:]
                
                new_line = indent + line + "\n"
                s += new_line
            
            it[3] = s[:-1]

