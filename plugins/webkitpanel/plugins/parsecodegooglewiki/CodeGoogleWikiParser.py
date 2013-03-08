#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re

HTML_HEADERS = '''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd"><html>
<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
<head>
    <style>
    body {
        font: 82% arial, sans-serif;
        min-width: 768px;
    }
    h3 {
        font-size: 1.25em;
        padding-top: 3px;
        padding-bottom: 2px;
    }
    pre {
        background-color:#EEEEEE;
        color:black;
        max-width: 70em;
        padding: 0.6em;
        font-size: 93%;
        font-family: 'Lucida Console',monospace;
        line-height: 1.25em;
    }
    li, ul {
        padding-top: 0px;
    }
    blockquote {
        margin: 20px;
    }
    .code {
        font-family: monospace;
    }
    #content {
        background: none repeat scroll 0 0 #F8F8F8;
        pading-bottom: 10px;
        padding-left: 5px;
        line-height: 1.30em;
    }
    #wiki_content {
        border: 1px solid #CCCCCC;
        background-color:#FFFFFF;
        max-width: 64em;
        padding: 5px 25px 10px 10px;
    }
    
    </style>
</head>
<body>
<div id="content">
<h3>   PageName</h3>
<div id="wiki_content">
'''

HTML_FOOTER    = '</div></div></body></html>'
HTML_LINK      = '<a href="%(link)s">%(text)s</a>'
HTML_IMG       = '<img src="%(s)s%(link)s" />%(e)s'
HTML_IMG_LINK  = '<a href="%(link)s"><img src="%(link)s" /></a>'
HTML_SPAN_CODE = r'<span class="code">\2</span>'
ESC_HEADERS    = ['#summary', '#labels', '#sidebar']


class FindReplace(object):
    def replace_liste(self, line, arg, att):
        nws = re.match('(^ *)\%s'%arg, line)
        if not nws:
            return line
        nws = len(nws.group(1))
        line_return = ''
        if self.current_nws == -1:
            line_return+='<ul type="%s">\n'%att
            self.nb_list_open+=1
        else:
            if nws > self.current_nws:
                line_return+='<ul type="circle">\n'
                self.nb_list_open+=1
            elif nws < self.current_nws:
                line_return+='</ul>'
                self.nb_list_open-=1
        line = re.match(' *\%s (.*)'%arg, line).group(1)
        line = self.replace_marks(line)
        line_return+='<li>%s</li>' % line
        self.current_nws = nws
        return line_return

    def replace_backquote(self, line):
        return re.sub(self.re_backq,
                      HTML_SPAN_CODE,
                      line)
    
    def replace_style(self, line, re_comp, bal):
        return re.sub(re_comp,
                      r'\1<%(bal)s>\2</%(bal)s>\3' % locals(),
                      line)
    
    def replace_equal(self, line):
        return re.sub(self.re_equal, self.re_equal_cb, line)
    
    def re_equal_cb(self, m): 
        n = str(len(m.group(1)))
        bals = '<h%s>' % n
        bale = '</h%s>' % n
        return '%s%s%s' % (bals, m.group(2), bale)
        
    def replace_link(self, line):
        return re.sub(self.re_link, self.re_link_cb, line)
    
    def re_link_cb(self, m):
        link = text = m.group(2)
        if ' ' in link:
            link, text = link.split(' ', 1)
        return HTML_LINK % locals()
    
    def replace_img(self, line):
        return re.sub(self.re_img, self.re_img_cb, line)
    
    def re_img_cb(self, m):
        s, name, ext, e = m.groups()
        link = '%s.%s' % (name, ext)
        if s == '[':
            return HTML_IMG_LINK % locals()
        return HTML_IMG % locals()
    
    
class Parser(FindReplace):
    def __init__(self):
        self.re_backq  = re.compile("(`)([^ ][^`]*[^ ])(`)")
        self.re_equal  = re.compile("(^=+)([^=]+)(=+)")
        self.re_link   = re.compile("(\[)([^\]]+)(\])")
        self.re_img    = re.compile("(.|^)([^ ]*)\.(jpg|png|gif|bmp)(.|$)")
        self.re_bold   = re.compile("(^| )\*([^\*]+.*[^\*])\*( |$)")
        self.re_ital   = re.compile("(^| )\_([^\_]+.*[^\_])\_( |$)")
        self.re_strike = re.compile("(^| )\~\~([^\~]+.*[^\~])\~\~( |$)")
        self.parag_open   = 0
        self.nb_list_open = 0
        self.current_nws  = -1
        self.flag_text = True
    
    def escape_headers_line(self, line):
        flag_esc = False
        for esc in ESC_HEADERS:
            if line.startswith(esc):
                flag_esc = True
                break
        return flag_esc
    
    def parse(self, text):
        converted = []
        flag_code = False
        for line in text.split('\n'):
            if self.escape_headers_line(line): continue
            if '<code' in line:
                line = line.replace('<code language', '<pre class')
                flag_code = True
                self.flag_text = False
            if '</code>' in line:
                flag_code = False
                line = line.replace('</code', '</pre')
                converted.append(line)
                continue
            if '{{{' in line:
                line = line.replace('{{{','<pre>')
                flag_code = True
                self.flag_text = False
            if '}}}' in line:
                flag_code = False
                line = line.replace('}}}','</pre>')
                converted.append(line)
                continue
            if flag_code: 
                converted.append(line)
                continue
            if line.startswith(' '):
                self.ws_starting_line(line, converted)
                self.flag_text = False
            else:
                if line == '' or line == '<br>':
                    if line == '<br>':
                        line = '<div><br> </div>'
                    if (line == '' and self.flag_text
                        and self.nb_list_open == 0): #empty line between text
                        line = '<br>'
                        #self.flag_text = False
                    if self.nb_list_open > 0:
                        converted = converted+['</ul>']*self.nb_list_open
                        self.nb_list_open = 0
                        self.current_nws = -1
                    if self.parag_open:
                        converted = converted+['</div>']*self.parag_open
                        self.parag_open = False
                    converted.append(line)
                    continue
                if not self.parag_open:
                    if line.startswith('='): # to put <h> before <div>
                        converted.append(self.replace_marks(line))
                        converted.append('<div>')
                        self.parag_open = True
                        continue
                    converted.append('<div>')
                    self.parag_open = True
                converted.append(self.replace_marks(line))
                self.flag_text = True
        return '\n'.join(converted)
    
    def replace_marks(self, line):
        if line.startswith('----'): return '<hr>'
        line = self.replace_equal(line)
        line = self.replace_backquote(line)
        line = self.replace_style(line, self.re_bold, 'b')
        line = self.replace_style(line, self.re_ital, 'i')
        line = self.replace_style(line, self.re_strike, 's')
        line = self.replace_img(line)
        line = self.replace_link(line)
        return line
    
    def ws_starting_line(self, line, converted):
        line = self.replace_liste(line,'*','circle')
        line = self.replace_liste(line,'#','1')
        if line.startswith(' '):
            converted.append('<blockquote>')
            converted.append(self.replace_marks(line))
            converted.append('</blockquote>')
            return
        converted.append(line)


if __name__ == '__main__':
    import sys
    out = '/tmp/preview_gedit_webbit_panel.html'
    try:
        wiki = sys.argv[1]
    except:
        print 'USAGE: %s file.wiki [file.html]' % sys.argv[0].split('/')[-1]
        print 'default [file.html] => %s' % out
        exit(2)
    try:
        out = sys.argv[2]
    except: pass
    html = Parser().parse(file(wiki,'r').read())
    all_html = HTML_HEADERS + html + HTML_FOOTER
    file(out,'w').write(all_html)

