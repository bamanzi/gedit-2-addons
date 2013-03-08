#! /usr/bin/python
# -*- coding: utf-8 -*-
import os, sys
import cgi                        # Module d'interface avec le serveur 
                                  # w
form = cgi.FieldStorage()         # Réception de la requête utilisateur :
                                   # il s'agit d'une sorte de dictionnaire
if form.has_key("phrase"):        # La clé n'existera pas si le champ
	text = form["phrase"].value    # correspondant est resté vide
else:
	text ="*** le champ phrase était vide ! ***"
	
if form.has_key("visiteur"):      # La clé n'existera pas si le champ
	nomv = form["visiteur"].value  # correspondant est resté vide
else:
	nomv ="mais vous ne m'avez pas indiqué votre nom"

print "Content­Type: text/html\n"
print """
<html>
<head>
 <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
 <title>Gedit </title>
</head>
<body>
<h3>Merci, %s !</h3>
<h4>La phrase que vous m'avez fournie était : </h4>
<h3><FONT Color="red"> %s </FONT></h3>""" % (nomv, text)

histogr ={}
for c in text:
	histogr[c] = histogr.get(c, 0) +1

liste = histogr.items()       # conversion en une liste de tuples
liste.sort()                  # tri de la liste
print "<h4>Fréquence de chaque caractère dans la phrase :</h4>"
for c, f in liste:
	print 'le caractère <B>"%s"</B> apparaît %s fois <BR>' % (c, f)
print "</body></html>"

