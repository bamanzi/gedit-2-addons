#! /usr/bin/python
# -*- coding: utf-8 -*-
# Affichage d'un formulaire HTML simplifié :
print "Content­Type: text/html\n"
print """
<HTML>
<HEAD><META HTTP-EQUIV="Content-Type" CONTENT="text/html; CHARSET=utf-8"></HEAD>
<BODY>
<H3><FONT COLOR="Royal blue">
Page web produite par un script Python
</FONT></H3>
<FORM ACTION="print_result.py" METHOD="post">
<P>Veuillez entrer votre nom dans le champ ci­dessous, s.v.p. :</P>
<P><INPUT NAME="visiteur" SIZE=20 MAXLENGTH=20 TYPE="text"></P>
<P>Veuillez également me fournir une phrase quelconque :</P>
<TEXTAREA NAME="phrase" ROWS=2 COLS=50>Mississippi</TEXTAREA>
<P>J'utiliserai cette phrase pour établir un histogramme.</P>
<INPUT TYPE="submit" NAME="send" VALUE="Action">
</FORM>
<BODY>
</HTML>
"""

