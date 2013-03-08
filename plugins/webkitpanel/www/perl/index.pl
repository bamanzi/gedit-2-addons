#!/usr/bin/perl -w

use strict;
use CGI::Carp qw(fatalsToBrowser);

my $headline = "Un script propre!";

print "Content-type: text/html\n\n";
print '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">', "\n";
print "<html><head><title>Test</title></head><body>\n";
print "<h1>$headline</h1>\n";
print "<p>on ne renonce ici qu'au module CGI ;-)</p>\n";
print "</body></html>\n";

