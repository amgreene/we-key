import cgi
import codecs
import collections
import re
import os

data_dir = '/data/amg/Dropbox/Genealogy/web/'
def data_open(file_name):
    return codecs.open(os.path.join(data_dir, file_name), 'r', 'utf-8')

class Page:
    def __init__(self, page_name):
        self.info = collections.defaultdict(list)
        self.text = []
        self.xrefs = []
        self.page_name = page_name

        if '.' in page_name:
            return
        if '/' in page_name:
            return
        if '\\' in page_name:
            return
        if ':' in page_name:
            return
        
        file_name = page_name + '.html'
        if file_name[0] == '@':
            file_name = file_name[1:]
        self.load(file_name)
        if len(self.text) == 0:
            self.text.append("This page is a stub. Nothing more is known at this time.")
        
        for xref_line in data_open('xrefs.txt'):
            if xref_line.startswith(page_name + ' '):
                self.xrefs = xref_line.split(' ', 1)[1].split(',')

    def find_name_for(self, at_path):
        try:
            at_path2 = at_path
            if at_path2[0] == '@':
                at_path2 = at_path2[1:]
            at_page = Page(at_path2)
            return at_page.name[0]
        except Exception as e:
            # print e
            for line in data_open('etc.html'):
                if line.startswith(at_path + ' '):
                    return line.split(' ', 1)[1]
            return at_path
        
    def find_extended_name_for(self, at_path):
        try:
            at_page = Page(at_path)
            n = at_page.name[0]
            parents = []
            parents += at_page.father
            parents += at_page.mother
            if len(parents):
                n += " (Child of " + ", ".join([
                    self.find_name_for(p) for p in parents
                    ]) + ")"
            return n
        except:
            for line in data_open('etc.html'):
                if line.startswith('@' + at_path + ' '):
                    return line.split(' ', 1)[1]
            return at_path
        
    def load(self, file_name):
        if not os.path.exists(os.path.join(data_dir, file_name)):
            self.info['name'] = [file_name.split('.')[0]]
            return
        for line in data_open(file_name):
            line = line.rstrip()
            if line == '':
                self.text.append(line)
            elif line[0] == '\\':
                if '=' in line:
                    (key, value) = line[1:].split('=', 2)
                else:
                    key=line[1:]
                    value=True
                self.info[key].append(value)
            else:
                self.text.append(line)

    def __getattr__(self, name):
        if self.info.has_key(name):
            return self.info[name]
        raise AttributeError

    # TO DO -- if an @Name can be resolved, use the person's real name. Otherwise, expand out the camel case
    def resolve_info(self, key):
        def do_lookup(at_path):
            at_path = at_path.group(1)
            return "<a href='" + at_path + "'>" + self.find_extended_name_for(at_path) + "</a>"
        s = ''.join([cgi.escape(s) for s in self.info[key]])
        s = re.sub(r'@(\S+) qua{(.*?)}', r'<a href="\1">\2</a>', s)
        s = re.sub(r'@(\S+)', do_lookup, s) # r'<a href="\1">\1</a>', s)
        return s

    def resolve_value(self, val):
        def do_lookup(at_path):
            at_path = at_path.group(1)
            return "<a href='" + at_path + "'>" + self.find_extended_name_for(at_path) + "</a>"
        s = cgi.escape(val)
        s = re.sub(r'@(\S+) qua{(.*?)}', r'<a href="\1">\2</a>', s)
        s = re.sub(r'@(\S+)', do_lookup, s) # r'<a href="\1">\1</a>', s)
        return s

    def header_stuff(self, outlines):
        # TO DO - generalize/refactor this (allowing for more complex patterns/hierachies)
        outlines.append("<div class='header'>")
        if self.info.has_key('name'):
            outlines.append("<div class='name'>" + self.resolve_info('name') + "</div>")
        if self.info.has_key('hebname'):
            outlines.append("<div class='hebname'>" + self.resolve_info('hebname') + "</div>")
        if self.info.has_key('born'):
            outlines.append("<div class='born'>Born " + self.resolve_info('born') + "</div>")
        if self.info.has_key('married'):
            outlines.append("<div class='married'>Married " + self.resolve_info('married') + "</div>")
        if self.info.has_key('died'):
            outlines.append("<div class='died'>Died " + self.resolve_info('died') + "</div>")
        if self.info.has_key('father'):
            outlines.append("<div class='parent father'>Father: " + self.resolve_info('father') + "</div>")
        if self.info.has_key('mother'):
            outlines.append("<div class='parent mother'>Mother: " + self.resolve_info('mother') + "</div>")
        if len(self.xrefs):
            outlines.append("<div class='xrefs'>Referenced by: " + ', '.join(
                self.resolve_value(v) for v in self.xrefs
            ) + "</div>")
        outlines.append("</div>")

    def turn_page_into_html(self):
        outlines = []
        outlines.append("<title>" + self.page_name + "</title>")
        self.header_stuff(outlines)
        outlines.append("<div class='text'>")
        if self.info.has_key('isform'):
            outlines.append("<table cellpadding=0 cellborders=0>")
        for line in self.text:
            line = cgi.escape(line)

            line = re.sub(r'\\addr\{(.*?)\}', r'<span class="addr">\1</a>', line)
            line = re.sub(r'\\age\{(.*?)\}', r'\1', line) # TO DO --> implied birth year
            line = re.sub(r'@(\S+) qua{(.*?)}', r'<a href="\1">\2</a>', line)
            line = re.sub(r'@(\S+)', r'<a href="\1">\1</a>', line)
            line = re.sub(r'(\d{4}-\d{2}-\d{2})', r'<span class="date">\1</span>', line)

            if self.info.has_key('isform'):
                if ': ' in line:
                    line = "<tr><td>" + re.sub(r': (.*)', r':</td><td><b>\1</b>', line) + "</td></tr>"
                else:
                    line = "<tr><td colspan=2>" + line + "</td></tr>"
            else:
                line += "<br>"

            outlines.append(line)
        if self.info.has_key('isform'):
            outlines.append("</table>")
        outlines.append("</div>")

        for line in data_open('images-index.txt'):
            splits = line.split(' ')
            if re.sub('@', '', splits[0]) == self.page_name:
                for url in splits[1:]:
                    outlines.append("<img src='" + url + "'><br>")

        return u'\n'.join([unicode(s) for s in outlines])

def make_index():
    refs = collections.defaultdict(set)
    for f in os.listdir(data_dir):
        if not f.endswith('.html'):
            continue
        for line in data_open(f):
            for m in re.findall(r'@(\S+)', line):
                refs[m].add('@' + f[:-5])
    with open(os.path.join(data_dir, 'xrefs.txt'), 'w') as o:
        for r in sorted(refs.keys()):
            print >> o, r, ','.join(sorted(list(refs[r])))

if __name__ == '__main__':
    import sys
    print turn_page_into_html(sys.argv[1])
