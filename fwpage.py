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
    def __init__(self, page_name):
        self.info = collections.defaultdict(list)
        self.text = []
        self.xrefs = []
        self.relations = {}
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
            at_page = Page(at_path2)
            return at_page.name[0]
        except Exception as e:
            # print e
            for line in data_open('etc.html'):
                if line.startswith(at_path + ' '):
                    return line.split(' ', 1)[1]
            return uncamel_case(at_path)
        
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

    def turn_page_into_html(self):
        outlines = []
        outlines.append("<title>" + self.page_name + "</title>")
        self.header_stuff(outlines)
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
        p = Page(at_path)

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

if __name__ == '__main__':
    import sys
    make_relationship_index()
