#!/usr/bin/python2
# -*- coding: utf-8 -*-
import datetime
import os
import poppler
import subprocess
import tempfile
import urllib
import urlparse

tiff_extensions = ["tiff", "tif"]
pdf_extensions = ["pdf"]

class Document(object):
    """
    class representing a single document.
    """
    def __init__(self):
        self._paths = []
        self._tempfiles = []
        self._attributes = {}
    def add(self, path):
        if os.path.isfile(path) and os.access(path, os.R_OK):
            self._addpath(path)
        else:
            raise IOError(str(path) + " not readable")

    def _addpath(self, path):
        basename = os.path.basename(path)
        encoded_file_name, ext = os.path.splitext(basename)
        ext = ext[1:].lower()
        if ext in tiff_extensions:
            _, tmppdf = tempfile.mkstemp(suffix=".pdf", prefix="tiff_")
            subprocess.check_call(["tiff2pdf", "-o", tmppdf, path])
            self._addpdf(tmppdf)
        elif ext in pdf_extensions:
            self._addpdf(path)
        else:
            raise IOError(ext+" is neither a TIFF nor a PDF extension")
        self._parse_name(encoded_file_name)


    def _addpdf(self, path):
        fileurl = urlparse.urljoin("file:", urllib.pathname2url(os.path.abspath(path)))
        ## above code snippet by Dave Abrahams, cc-by-sa:
        ## http://stackoverflow.com/a/14298190/4433386
        pdfdoc = poppler.document_new_from_file(fileurl, "")
        n_pages = pdfdoc.get_n_pages()
        self._paths.append((path, n_pages))

    def total_pages(self):
        return sum([n for n, _ in self._paths])

    def mergeable(self, name):
        try:
            pre_type = self._attributes["type"]
            fdict = FilenameParser(name)
            post_type = fdict.pop("type")
            if len(FilenameParser.types[pre_type]) >= 4 and FilenameParser.types[pre_type][2] == post_type:
                return all([fdict.get(key) == self._attributes.get(key) for key in fdict.keys()])
        except:
            pass
        return False
    def get_type(self):
        return self._attributes.get("type")

    def get_pdf(self):
        if len(self._paths) == 1:
            return self._paths[0]
        elif len(self._paths) > 1:
            _, tmppdf = tempfile.mkstemp(suffix=".pdf", prefix="joined_")
            subprocess.check_call("pdfjoin", "-o", tmppdf, [filename for filename, _ in self._paths])
            self._del_tempfiles()
            self._addpdf(tmppdf)
            return self.get_pdf()
    def _parse_name(self, name):
        pre_type = self._attributes.get("type")
        self._attributes.update(FilenameParser(name))
        post_type = self._attributes.get("type")
        if pre_type and post_type and len(FilenameParser.types[pre_type]) >= 4 and FilenameParser.types[pre_type][2] == post_type:
            self._attributes["type"] = FilenameParser.types[pre_type][3]

    def __add__(self, other):
        otherpdf = other.get_pdf()
        self._paths.append( (other.total_pages(), otherpdf) )

    def __del__(self):
        self._del_tempfiles()

    def _del_tempfiles(self):
        for tmpfile in self._tempfiles:
            os.unlink(tmpfile)
        self._tempfiles = []


class FilenameParser(dict):
    partnames = ["date", "type", "lecturer", "sequence"]
    types = {
            "b" : ("Bewertung" , 1, "f", "B"),
            "f" : ("Fragen" , 1),
            "B" : ("Fragen & Bewertung" , 1),
            "t" : ("Tipps und Tricks" , 2),
            "s" : ("Skript" , 2),
            "k" : ("Klausur" , 0),
            "K" : ("Klausur" , 0),
            "p" : ("Klausur (Gedächtnisprotokoll)" , 0),
            "l" : ("Musterlösung" , 0),
            "n" : ("Formelsammlung" , 2),
            "i" : ("Index zu Skript/Buch" , 2),
            "z" : ("Sonstiges" , 2)
    }
    def __init__(self, name):
        self.parsers = {"date": lambda s: self.parse_date(s),"type": lambda s: self.parse_type(s), "lecturer": str, "sequence": int}
        self.filename = name
        assert(len(name) >= 6)
        parts = name.split("_")
        assert(len(parts) <= len(self.parsers))
        for partname, part in zip(self.partnames, parts):
            self[partname] = self.parsers[partname](part)
    def __repr__(self):
        date = self.get("date")
        if not date is None:
            date = date.strftime("%Y%m%d")
        else:
            date = "0"*8
        return "{:s}|{:03d}|{:s}|{:s}".format(
                date,
                self.get("sequence", 0),
                self.get("type"),
                self.get("lecturer") )
    def __str__(self):
        return "Date: {:s} ({:s}): {:d}. {:s}".format(
                str(self["date"]),
                str(self.get("lecturer")),
                self.get("sequence",0),
                self.types[self["type"]][0]
        )
    @staticmethod
    def parse_date(string):
        if len(string) != 8:
            print "ATT:"+string
        assert(len(string) == 8)
        if string == "0" * 8:
            return None
        indexes = [0, 4, 6, 8]
        year, month, day = [ max(int(string[start:stop]), 1) for start,stop in zip(indexes[:-1], indexes[1:]) ]
        return datetime.date(year, month, day)

    @staticmethod
    def parse_type(s):
        assert(len(s) == 1)
        assert(s in FilenameParser.types)
        return s
