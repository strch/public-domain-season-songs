﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
parses the input folder for .ly files, makes some costum modifikation to the ly
file, writes a pdf + some extracted data
"""


import subprocess
import os
import re
import shutil
from optparse import OptionParser

######################

inFolder = "../"
outFolder = "pdfs"
outFolderText = "texts"
filenames = []

no_songs = ['default.ly']


def process_file(ly, dryrun):
    infile = os.path.join(inFolder, ly)
    inp = open(infile, 'rb')
    outp = open("temp.ly", 'wb')
    outp.write("""
\header{{
    tagline = " " %remove the »Music engraving by LilyPond«
}}

\paper {{
  myStaffSize = #20
  %{{
     run
         lilypond -dshow-available-fonts blabla
     to show all fonts available in the process log.
  %}}

  #(define fonts
    (make-pango-font-tree "DejaVu Sans"
                          "DejaVu Sans"
                          "DejaVu Sans Mono"
    (/ myStaffSize 20)))
    %system-system-spacing #'stretchability = #0
    %ragged-last-bottom = ##t
    %ragged-bottom = ##t
    %print-page-number = ##f
    #(set-paper-size "a4")
}}
""".format(margin=0))

    tw = inp.read()
    tw = tw.replace(u"\ufeff".encode("utf-8"), "")
    inpaper = False
    filename = None
    name = None
    removed_lines = []
    markup = False
    markupc = 0
    texxt = ""
    composer = poet = ""
    for line in tw.split("\n"):
        r = re.match(r'\W*title\W*=\W*"([^"]+)"', line)
        rcomposer = re.match(r'\W*composer\W*=\W*"([^"]+)"', line)
        rpoet = re.match(r'\W*poet\W*=\W*"([^"]+)"', line)
        komplizierter_poet = re.findall(r'"([^"]+)"', line)
        if inpaper or "\paper" in line:
            inpaper = True
            if "}" in line:
                inpaper = False
            removed_lines.append(line)
        if markup or re.findall(r"^\s*\\markup", line):
            markup = True
            markupc += line.count("{")
            markupc -= line.count("}")
            if markupc == 0:
                markup = False
            if r"\bold" in line:
                num = re.findall(r'"\s*(\d+)\s*\.?\s*"', line)
                if num:
                    texxt = texxt[:-1] + "\r" + num[0] + ".\t"
                else:
                    line = re.sub('["{}]', "", re.sub(r"\\.*?[{ ]", "", line)).strip()
                    texxt += line
                    #removed_lines.append(line)
            else:
                m = re.match(r'\s*"([^"]*)"\s*', line)
                if m:
                    texxt += m.groups()[0] + "\n"
        elif r and len(r.groups()) == 1:
            filename = r.groups()[0]
            name = filename.decode("utf-8")
            filename = filename.decode("utf-8")
            filename = filename.replace(u"’", "_").replace(u"…", "_")
            while filename in [a[0] for a in filenames]:
                filename = filename + "-"
            removed_lines.append(line)
        elif rcomposer and len(rcomposer.groups()) == 1:
            composer = rcomposer.groups()[0].decode("utf-8")
        elif rpoet and len(rpoet.groups()) == 1:
            poet = rpoet.groups()[0].decode("utf-8")
        elif "set-global-staff-size" in line:
            removed_lines.append(line)
        elif "set-default-paper-size" in line:
            removed_lines.append(line)
        elif "version" in line:
            removed_lines.append(line)
        elif "opus" in line:
            removed_lines.append(line)
        elif r"\tempo" in line:
            removed_lines.append(line)
        elif "copyright" in line and "=" in line and "\"" in line:
            removed_lines.append(line)
        elif "subtitle" in line and "=" in line:
            removed_lines.append(line)
        #elif "\hspace #0.1" in line:
        #    print "- - ", line
        #    outp.write("\hspace #5")
        elif "poet" in line and komplizierter_poet:
            #print komplizierter_poet
            komplizierter_poet = map(lambda x: x.decode("utf-8"), komplizierter_poet)
            gr = u"\n".join(komplizierter_poet[1:])
            poet = u"{0} {1}".format(komplizierter_poet[0], gr)
            #print type(poet), poet
        else:
            outp.write(line + "\n")
    with open(os.path.join(outFolderText, filename + ".txt"), "wb") as textf:
        textf.write(texxt[:-1])
    filenames.append((filename, name, poet.replace("\n", "\\n"), composer.replace("\n", "\\n")))
    inp.seek(0)
    file_content = inp.read()
    inp.close()
    outp.flush()
    outp.close()

    outfile = os.path.join(outFolder, filename)

    if (not dryrun):
        cl = [
            "lilypond",
            "-V",
            "-I",
            os.path.abspath("../"),
            "-d",
            "point-and-click=#f",
            "-o",
            outfile,
            "temp.ly"
        ]
        sub = subprocess.Popen(
            cl, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        status = sub.wait()
        if os.path.exists(outfile + ".ps"):
            os.remove(outfile + ".ps")
        if os.path.exists(outfile + ".midi"):
            os.remove(outfile + ".midi")

    return {
        "lilypond": status,
        "removed_lines": removed_lines,
        "lilypond_stdout": sub.stdout.read(),
        "lilypond_stderr": sub.stderr.read(),
        "file_content": file_content,
        "data": {"name": name, "poet": poet, "composer": composer}}


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
        "-v", "--verbose", dest="verbose", action="count", default=0,
        help="increment verbose level")
    parser.add_option(
        "-r", "--remove", dest="remove", action="store_true", default=False,
        help="remove old pdfs")
    parser.add_option(
        "-f", "--filter", dest="filter",
        help="only renders files that contain FILTER", metavar="FILTER")
    parser.add_option(
        "-d", "--dryrun", action="store_true", dest="dryrun", default=False,
        help="don't render files with lilypond, just check if parsing files "
             "will work and generate list.txt")

    (options, args) = parser.parse_args()

    if options.remove:
        shutil.rmtree(outFolder)

    if not os.path.exists(outFolder):
        os.mkdir(outFolder)

    if not os.path.exists(outFolderText):
        os.mkdir(outFolderText)

    files = filter(lambda x: re.match(".*\.ly$", x), os.listdir(inFolder))
    files = filter(lambda x: x not in no_songs, files)

    if options.filter:
        print "#" * 80
        print "# filter for " + options.filter + "!"
        print "# files without filtering:", len(files)
        files = filter(lambda x: options.filter in x, files)
        print "# files now:", len(files)
        print "#" * 80

    for ly in files:
        status = process_file(ly, options.dryrun)
        print("{:.<60} {}{}{}".format(
            ly,
            "C" if status["data"].get("composer", "") else " ",
            "P" if status["data"].get("poet", "") else " ",
            "N" if status["data"].get("name", "") else " ",
        ))
        if options.verbose > 0:
            for key in sorted(status["data"]):
                print u"    {: <20} : {}".format(key, status["data"][key])
        if options.verbose > 0:
            print "    removed lines:"
            print "   ", "    \n".join(status["removed_lines"])
        if status["lilypond"] == 1:
            for line_number, line in enumerate(status["file_content"].splitlines()):
                print "{:0<3}: {}".format(line_number, line)
            print status["lilypond_stdout"]
            print status["lilypond_stderr"]
            print "\n\n\nLILYPOND FAILED\n\n"
            break

    if not options.filter:
        print "liste"
        import codecs
        f = open("list.txt", "wb")
        f.write( codecs.BOM_UTF8 )
        f.write("@pdf\tname\n")
        for filename, name, poet, composer in filenames:
            #f.write( + u"\t" + + u"\n")
            f.write(filename.encode("utf-8")+".pdf")
            f.write("\t")
            f.write(name.encode("utf-8"))
            f.write("\t")
            f.write(poet.encode("utf-8"))
            f.write("\t")
            f.write(composer.encode("utf-8"))
            f.write("\n")
        f.flush()
        f.close()
