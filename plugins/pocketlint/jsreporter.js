// Copyright (C) 2009-2013 - Curtis Hovey <sinzui.is at verizon.net>
// This software is licensed under the MIT license (see the file COPYING).

// Run like:
// <seed|gjs> jsreporter.js <path/to/fulljslint.js> <path/file/to/lint.js>


function get_seed() {
    // Define a common global object like seed.
    var argv = ['gjs', 'jsreporter.js'];
    var i;
    for (i = 0; i < ARGV.length; i++) {
        argv.push(ARGV[i]);
        }
    return {
        'print': print,
        'argv': argv
        };
    }


var Seed = Seed || get_seed();


jslint_path = Seed.argv[2].substring(0, Seed.argv[2].lastIndexOf('/'));
imports.searchPath.push(jslint_path);
var JSLINT = imports.fulljslint.JSLINT;


function get_file_content(file_path) {
    // Return the content of the file.
    var Gio = imports.gi.Gio;
    var file = Gio.file_new_for_path(file_path);
    var istream = file.read(null);
    var dstream = new Gio.DataInputStream({base_stream: istream});
    var content_and_count = dstream.read_upto("", -1, null);
    istream.close(null);
    dstream = null;
    return content_and_count[0];
    }


function report_implied_names() {
    // Report about implied global names.
    var implied_names = [];
    var prop;
    for (prop in JSLINT.implied) {
        if (JSLINT.implied.hasOwnProperty(prop)) {
            implied_names.push(prop);
            }
        }
    if (implied_names.length > 0) {
        implied_names.sort();
        return '0::0::Implied globals:' + implied_names.join(', ');
        }
    return '';
    }


function report_lint_errors() {
    // Report about lint errors.
    var errors = [];
    var i;
    for (i = 0; i < JSLINT.errors.length; i++) {
        var error = JSLINT.errors[i];
        if (error === null) {
            error = {
                'line': -1,
                'character': -1,
                'reason': 'JSLINT had a fatal error.'
                };
            }
        // Fix the line and character offset for editors.
        error.line += 1;
        error.character += 1;
        errors.push(
            [error.line, error.character, error.reason].join('::'));
        }
    return errors.join('\n');
    }


function lint_script() {
    // Lint the source and report errors.
    var script = get_file_content(Seed.argv[3]);
    var result = JSLINT(script);
    if (! result) {
        var issues = [];
        errors = report_lint_errors();
        if (errors) {
            issues.push(errors);
            }
        implied = report_implied_names();
        if (implied) {
            issues.push(implied);
            }
        Seed.print(issues.join('\n'));
        }
    }

lint_script();
