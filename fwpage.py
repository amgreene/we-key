import cgi
import codecs
import collections
import datetime
import json
import re
import os

data_dir = '/data/amg/Dropbox/Genealogy/web/'
def data_open(file_name):
    return codecs.open(os.path.join(data_dir, file_name), 'r', 'utf-8')

def uncamel_case(s):
    s = re.sub('([a-z])([A-Z])', r'\1 \2', s)
    s = re.sub('([0-9])([a-zA-Z])', r'\1 \2', s)
    s = re.sub('([a-zA-Z])([0-9])', r'\1 \2', s)
    s = re.sub('-', ' ', s)
    return s

class Page:
    cache = {}

    @staticmethod
    def find(page_name):
        return Page.cache.get(page_name, Page(page_name))

    def __init__(self, page_name):
        self.info = collections.defaultdict(list)
        self.text = []
        self.xrefs = []
        self.relations = {}
        self.page_name = page_name
        Page.cache[page_name] = self

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
        
        with codecs.open(os.path.join(data_dir, 'xrefs.json'), 'r', 'utf-8') as x_file:
            self.xrefs = json.load(x_file).get(page_name, [])
        with codecs.open(os.path.join(data_dir, 'relationships.json'), 'r', 'utf-8') as x_file:
            self.relations = json.load(x_file).get('@' + page_name, {})

    def __unicode__(self):
        return self.page_name

    def __str__(self):
        return str(unicode(self))

    def find_name_for(self, at_path):
        try:
            at_path2 = at_path
            if at_path2[0] == '@':
                at_path2 = at_path2[1:]
            at_page = Page.find(at_path2)
            return at_page.name[0]
        except Exception as e:
            # print e
            for line in data_open('etc.html'):
                if line.startswith(at_path + ' '):
                    return line.split(' ', 1)[1]
            return uncamel_case(at_path)
        
    def find_extended_name_for(self, at_path):
        try:
            at_page = Page.find(at_path)
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
            return uncamel_case(at_path)
        
    def load(self, file_name):
        if not os.path.exists(os.path.join(data_dir, file_name)):
            # No file backs up this at_path
            # So just take the atpath itself, and insert spaces where there's camel-casing
            self.info['name'] = [uncamel_case(file_name.split('.')[0])]
            # no file means no mtime
            self.mtime = ''
            return
        self.mtime = datetime.datetime.fromtimestamp(
            os.path.getmtime(os.path.join(data_dir, file_name))).strftime('%Y-%m-%d %H:%M:%S')
        current_key = ''
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
                current_key = key + "/" + unicode(value)  # kludge to get the format right; should be an object
            elif line.lstrip()[0] == '\\': # indented -- for now, we're not recursing, but we should
                if '=' in line:
                    (key, value) = line.lstrip()[1:].split('=', 2)
                else:
                    key=line.lstrip()[1:]
                    value=True
                self.info[current_key + "/" + key].append(value) # klude; see above
            else:
                self.text.append(line)
                current_key = ''

    def __getattr__(self, name):
        if self.info.has_key(name):
            return self.info[name]
        return []

    # TO DO -- if an @Name can be resolved, use the person's real name. Otherwise, expand out the camel case
    def resolve_info(self, key):
        s = ', '.join([cgi.escape(s) for s in self.info[key]])
        return self.expand_atpaths(s)

    def expand_atpaths(self, s):
        def do_lookup(at_path):
            at_path = at_path.group(1)
            return "<a href='" + at_path + "'>" + self.find_name_for(at_path) + "</a>"
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
        if self.relations.has_key('children'):
            outlines.append("<div class='children'>Children: " + ", ".join([
                self.expand_atpaths(cgi.escape(child_path)) for child_path in self.relations['children']
                ]) + "</div>")
        if len(self.xrefs):
            outlines.append("<div class='xrefs'>Referenced by: " + ', '.join(
                self.expand_atpaths(cgi.escape(v)) for v in self.xrefs
            ) + "</div>")
        outlines.append("</div>")

    def format_one_line(self, line):
        line = cgi.escape(line)

        line = re.sub(r'\\addr\{(.*?)\}', r'<span class="addr">\1</a>', line)
        line = re.sub(r'\\age\{(.*?)\}', r'\1', line) # TO DO --> implied birth year
        line = self.expand_atpaths(line)
        line = re.sub(r'(\d{4}-\d{2}-\d{2})', r'<span class="date">\1</span>', line)

        if self.info.has_key('isform'):
            if ': ' in line:
                line = "<tr><td>" + re.sub(r': (.*)', r':</td><td><b>\1</b>', line) + "</td></tr>"
            else:
                line = "<tr><td colspan=2>" + line + "</td></tr>"
        else:
            line += "<br>"

        return line

    def find_ancestor_by_path(self, path, x='self'):
        if x is None:
            return None
        if x=='self':
            x = self
        if isinstance(x, unicode):
            x = Page.find(x) # kludge
        if path == '':
            return x
        if path[0] == 'm':
            return self.find_ancestor_by_path(path[1:], (x.mother + [None])[0])
        if path[0] == 'f':
            return self.find_ancestor_by_path(path[1:], (x.father + [None])[0])
        return None

    def generate_ancestors_compact_html(self):
        ff = self.find_ancestor_by_path('ff')
        fm = self.find_ancestor_by_path('fm')
        mf = self.find_ancestor_by_path('mf')
        mm = self.find_ancestor_by_path('mm')
        f = self.find_ancestor_by_path('f')
        m = self.find_ancestor_by_path('m')
        s = []

        def do_grandparent(gp):
            if gp is None:
                return
            s.append("<div class='ftree_grandparent'>" + gp.expand_atpaths(cgi.escape(gp.page_name)))
            if len(gp.father):
                s.append("<div class='greatgrandparents'>" + gp.resolve_info('father') + "</div>")
            if len(gp.mother):
                s.append("<div class='greatgrandparents'>" + gp.resolve_info('mother') + "</div>")
            s.append("</div>")

        s.append("<div class='ftree'>")
        if not ((ff is None) and (fm is None)):
            s.append("<div class='ftree_paternal_grandparents'>")
            do_grandparent(ff)
            do_grandparent(fm)
            s.append("</div>")
        if not ((mf is None) and (mm is None)):
            s.append("<div class='ftree_maternal_grandparents'>")
            do_grandparent(mf)
            do_grandparent(mm)
            s.append("</div>")
        if not ((f is None) and (m is None)):
            s.append("<div class='ftree_parents'>")
            if not (f is None):
                s.append("<div>" + f.expand_atpaths(cgi.escape(f.page_name)) + "</div>")
            if not (m is None):
                s.append("<div>" + m.expand_atpaths(cgi.escape(m.page_name)) + "</div>")
            s.append("</div>")
        s.append("<div class='ftree_central'>" + cgi.escape(self.name[0]) + "</div>") # no need to self-link
        s.append("</div>")
        return "".join(s)

    def turn_page_into_html(self):
        outlines = []
        outlines.append("<title>" + self.page_name + "</title>")
        self.header_stuff(outlines)
        outlines.append(self.generate_ancestors_compact_html())
        outlines.append("<div class='text'>")
        if self.info.has_key('isform'):
            outlines.append("<table cellpadding=0 cellborders=0>")
        is_stub = True
        for line in self.text:
            formatted_line = self.format_one_line(line)
            if len(formatted_line.strip()):
                is_stub = False
            outlines.append(formatted_line)
        if self.info.has_key('isform'):
            outlines.append("</table>")
        if is_stub:
            outlines.append("This page is a stub. Nothing more is known at this time.")

        outlines.append("</div>")

        if self.mtime:
            outlines.append("<div class='mtime'>Last updated " + self.mtime + "</div>")

        for line in data_open('images-index.txt'):
            splits = line.split(' ')
            if re.sub('@', '', splits[0]) == self.page_name:
                outlines.append("<img class='img_on_page' src='/img/" + self.page_name + "'><br>")
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
    
    converted_refs = dict([(k, sorted(list(v))) for (k, v) in refs.items()])
    with codecs.open(os.path.join(data_dir, 'xrefs.json'), 'w', 'utf-8') as o:
        json.dump(converted_refs, o, ensure_ascii=False, indent=2, sort_keys=True)

def make_relationship_index():
    refs = {}
    def add_value(at_path, relationship, other_at_path):
        if not refs.has_key(at_path):
            refs[at_path] = {}
        if not refs[at_path].has_key(relationship):
            refs[at_path][relationship] = []
        refs[at_path][relationship].append(other_at_path)

    for f in os.listdir(data_dir):
        if not f.endswith('.html'):
            continue
        at_path = '@' + f[:-5]
        p = Page.find(at_path)

        for parent in p.father:
            add_value(at_path, 'father', parent)
            add_value(parent, 'children', at_path)
        for parent in p.mother:
            add_value(at_path, 'mother', parent)
            add_value(parent, 'children', at_path)
        for spouse in p.married:
            add_value(at_path, 'spouses', spouse)
            add_value(spouse, 'spouses', at_path)
    
    with codecs.open(os.path.join(data_dir, 'relationships.json'), 'w', 'utf-8') as o:
        json.dump(refs, o, ensure_ascii=False, indent=2, sort_keys=True)

img_dir = '/data/amg/dropbox/Genealogy/'

def html_index_images():
    outlines = []
    outlines.append("<html><body>")
    for line in data_open('images-index.txt'):
        (key, path) = line.strip().split(' ', 1)
        outlines.append('<a href="/' + key + '">'+key+'</a>')
    outlines.append("</body></html>")
    return '<br>'.join(outlines)

def locate_image(key):
    for line in data_open('images-index.txt'):
        if line.startswith(key + ' '):
            return os.path.join(img_dir, line.split(' ')[1]).strip()
    return None

if __name__ == '__main__':
    import sys
    # make_relationship_index()
    print Page.find('GersonGreene').generate_ancestors_compact_html()
